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
"""Calibration kit library stored as JSON files.

All values are in SI units (H, F, Ohm, s)."""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ..Calibration import CalElement

logger = logging.getLogger(__name__)


def user_data_dir() -> Path:
    """Per user data directory (no Qt dependency)"""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
        )
    return base / "NanoVNASaver"


def calkit_dir() -> Path:
    return user_data_dir() / "calkits"


@dataclass
class CalKit:
    name: str = "Ideal"
    description: str = ""
    ideal: bool = True
    short_l0: float = 0.0
    short_l1: float = 0.0
    short_l2: float = 0.0
    short_l3: float = 0.0
    short_delay: float = 0.0
    open_c0: float = 0.0
    open_c1: float = 0.0
    open_c2: float = 0.0
    open_c3: float = 0.0
    open_delay: float = 0.0
    load_r: float = 50.0
    load_l: float = 0.0
    load_c: float = 0.0
    load_delay: float = 0.0
    through_delay: float = 0.0

    def apply_to(self, element: CalElement) -> None:
        state = "IDEAL" if self.ideal else "COEFF"
        element.short_state = element.open_state = state
        element.load_state = state
        element.through_is_ideal = self.ideal
        element.short_l0 = self.short_l0
        element.short_l1 = self.short_l1
        element.short_l2 = self.short_l2
        element.short_l3 = self.short_l3
        element.short_length = self.short_delay
        element.open_c0 = self.open_c0
        element.open_c1 = self.open_c1
        element.open_c2 = self.open_c2
        element.open_c3 = self.open_c3
        element.open_length = self.open_delay
        element.load_r = self.load_r
        element.load_l = self.load_l
        element.load_c = self.load_c
        element.load_length = self.load_delay
        element.through_length = self.through_delay

    @classmethod
    def from_element(
        cls, element: CalElement, name: str, description: str = ""
    ) -> "CalKit":
        return cls(
            name=name,
            description=description,
            ideal=element.short_state == "IDEAL",
            short_l0=element.short_l0,
            short_l1=element.short_l1,
            short_l2=element.short_l2,
            short_l3=element.short_l3,
            short_delay=element.short_length,
            open_c0=element.open_c0,
            open_c1=element.open_c1,
            open_c2=element.open_c2,
            open_c3=element.open_c3,
            open_delay=element.open_length,
            load_r=element.load_r,
            load_l=element.load_l,
            load_c=element.load_c,
            load_delay=element.load_length,
            through_delay=element.through_length,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CalKit":
        raw = json.loads(text)
        known = {f.name for f in fields(cls)}
        unknown = set(raw) - known
        if unknown:
            logger.warning("Ignoring unknown cal kit keys: %s", unknown)
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CalKit":
        return cls.from_json(path.read_text(encoding="utf-8"))


_default = CalElement()
BUILTIN_KITS: tuple[CalKit, ...] = (
    CalKit(name="Ideal", description="Ideal short, open and 50 Ω load"),
    CalKit(
        name="NanoVNA-Saver default SMA",
        description="Coefficients NanoVNA-Saver has always offered as"
        " defaults for the SMA kits shipped with NanoVNAs.",
        ideal=False,
        short_l0=_default.short_l0,
        short_l1=_default.short_l1,
        short_l2=_default.short_l2,
        short_l3=_default.short_l3,
        short_delay=_default.short_length * 1e-12,
        open_c0=_default.open_c0,
        open_c1=_default.open_c1,
        open_c2=_default.open_c2,
        open_c3=_default.open_c3,
        open_delay=_default.open_length,
        load_r=_default.load_r,
    ),
)


def _file_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") + ".json"


class CalKitLibrary:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or calkit_dir()

    def user_kits(self) -> list[CalKit]:
        kits = []
        if not self.directory.is_dir():
            return kits
        for path in sorted(self.directory.glob("*.json")):
            try:
                kits.append(CalKit.load(path))
            except (ValueError, TypeError, OSError) as exc:
                logger.warning("Unable to read cal kit %s: %s", path, exc)
        return kits

    def kits(self) -> list[CalKit]:
        return list(BUILTIN_KITS) + self.user_kits()

    def names(self) -> list[str]:
        return [k.name for k in self.kits()]

    def get(self, name: str) -> CalKit:
        for kit in self.kits():
            if kit.name == name:
                return kit
        raise KeyError(name)

    def is_builtin(self, name: str) -> bool:
        return any(k.name == name for k in BUILTIN_KITS)

    def save(self, kit: CalKit) -> Path:
        if self.is_builtin(kit.name):
            raise ValueError(f"Can not overwrite builtin kit {kit.name}")
        path = self.directory / _file_name(kit.name)
        kit.save(path)
        return path

    def delete(self, name: str) -> None:
        if self.is_builtin(name):
            raise ValueError(f"Can not delete builtin kit {name}")
        path = self.directory / _file_name(name)
        if path.exists():
            path.unlink()
