#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Production test sequences described as JSON.

Example::

    {
      "name": "433 MHz antenna",
      "device": "virtual:demo",
      "calibration": "cal/antenna.cal",
      "calkit": "Ideal",
      "sweep": {"start": 300e6, "stop": 600e6, "points": 101,
                "segments": 2, "averages": 1},
      "processing": {"smoothing": 1.0, "z0": 50,
                     "port1_delay_ps": 0, "port1_loss_db": 0},
      "limits": "limits/antenna.json",
      "steps": [
        {"action": "prompt", "message": "Connect DUT {serial}"},
        {"action": "sweep"},
        {"action": "check"},
        {"action": "save", "path": "out/{serial}_{timestamp}.s1p"},
        {"action": "report", "path": "out/{serial}_{timestamp}.html"},
        {"action": "log", "path": "out/results.csv"}
      ]
    }

Relative paths are relative to the sequence file. Placeholders:
{serial}, {timestamp}, {date}, {name}.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .deembed import FixtureSettings, PortExtension
from .limits import LimitResult, LimitSpec, log_result
from .report import ReportInfo, build_report, save_report
from .session import VNASession
from .sweepdata import SweepData

logger = logging.getLogger(__name__)

ACTIONS = ("prompt", "sweep", "sweep2port", "check", "save", "report", "log")


@dataclass
class SequenceResult:
    name: str
    serial: str
    passed: Optional[bool] = None
    limit_result: Optional[LimitResult] = None
    files: list[Path] = field(default_factory=list)
    data: Optional[SweepData] = None

    @property
    def verdict(self) -> str:
        if self.passed is None:
            return "NO LIMITS"
        return "PASS" if self.passed else "FAIL"


class Sequence:
    def __init__(self, spec: dict, base_dir: Path = Path(".")) -> None:
        self.spec = spec
        self.base_dir = base_dir
        self.name = spec.get("name", "Sequence")
        for step in spec.get("steps", []):
            if step.get("action") not in ACTIONS:
                raise ValueError(f"Unknown action in step {step}")

    @classmethod
    def load(cls, path: str | Path) -> "Sequence":
        path = Path(path)
        return cls(json.loads(path.read_text("utf-8")), path.parent)

    def path(self, value: str, variables: dict[str, str]) -> Path:
        p = Path(value.format(**variables))
        return p if p.is_absolute() else self.base_dir / p

    def configure(self, session: VNASession) -> None:
        if cal := self.spec.get("calibration"):
            session.load_calibration(
                self.base_dir / cal, self.spec.get("calkit", "Ideal")
            )
        proc = self.spec.get("processing", {})
        session.smoothing_pct = float(proc.get("smoothing", 0.0))
        session.fixture = FixtureSettings(
            port1=PortExtension(
                float(proc.get("port1_delay_ps", 0.0)) * 1e-12,
                float(proc.get("port1_loss_db", 0.0)),
            ),
            port2=PortExtension(
                float(proc.get("port2_delay_ps", 0.0)) * 1e-12,
                float(proc.get("port2_loss_db", 0.0)),
            ),
            z0=float(proc.get("z0", 50.0)),
        )

    def run(
        self,
        session: VNASession,
        serial: str = "",
        prompt: Callable[[str], None] = lambda msg: None,
    ) -> SequenceResult:
        now = datetime.now()
        variables = {
            "serial": serial or "noserial",
            "timestamp": now.strftime("%Y%m%d-%H%M%S"),
            "date": now.strftime("%Y-%m-%d"),
            "name": self.name,
        }
        self.configure(session)
        sweep_args = dict(self.spec.get("sweep", {}))
        start = float(sweep_args.pop("start"))
        stop = float(sweep_args.pop("stop"))
        spec = (
            LimitSpec.load(self.base_dir / self.spec["limits"])
            if self.spec.get("limits")
            else None
        )
        result = SequenceResult(self.name, serial)
        steps = self.spec.get("steps") or [
            {"action": "sweep"},
            {"action": "check"},
        ]
        for step in steps:
            action = step["action"]
            logger.info("Step: %s", action)
            if action == "prompt":
                prompt(step.get("message", "Continue").format(**variables))
            elif action == "sweep":
                result.data = session.sweep(start, stop, **sweep_args)
            elif action == "sweep2port":
                result.data = session.full_two_port(
                    start,
                    stop,
                    lambda step=step: prompt(
                        step.get(
                            "message", "Turn the DUT around (port 2 on port 1)"
                        ).format(**variables)
                    ),
                    **sweep_args,
                )
            elif result.data is None:
                raise RuntimeError(f"Step {action} needs a sweep first")
            elif action == "check":
                if spec is None:
                    raise RuntimeError("check step needs 'limits'")
                result.limit_result = spec.evaluate(result.data)
                result.passed = result.limit_result.passed
            elif action == "save":
                path = self.path(step["path"], variables)
                path.parent.mkdir(parents=True, exist_ok=True)
                result.data.save(str(path))
                result.files.append(path)
            elif action == "report":
                path = self.path(step["path"], variables)
                path.parent.mkdir(parents=True, exist_ok=True)
                info = ReportInfo(
                    title=f"{self.name} {serial}".strip(),
                    serial=serial,
                    device=session.info()["name"],
                    calibration=session.calibration.source
                    if session.calibration.isCalculated
                    else "device",
                )
                save_report(
                    path,
                    build_report(result.data, info, spec, result.limit_result),
                )
                result.files.append(path)
            elif action == "log":
                if result.limit_result is None:
                    raise RuntimeError("log step needs a check step first")
                path = self.path(step["path"], variables)
                path.parent.mkdir(parents=True, exist_ok=True)
                log_result(path, result.limit_result, serial, self.name)
                result.files.append(path)
        return result
