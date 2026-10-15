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
"""nanovna-pro: headless measurements, limit tests, sequences and the
REST/WebSocket server.

Exit codes: 0 pass (or no limits), 1 fail, 2 error.

Examples:
  nanovna-pro ports
  nanovna-pro sweep -d COM3 --start 1G --stop 3G -n 101 -s 4 \\
      --cal kit.cal --limits ant.json --out dut_042.s1p --report dut.html
  nanovna-pro check measured.s2p --limits filter.json
  nanovna-pro run production.json --serial SN042
  nanovna-pro serve -d virtual:demo --port 8765
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np

from ..Formatting import parse_frequency
from .deembed import FixtureSettings, PortExtension
from .formats import logmag, vswr
from .limits import LimitResult, LimitSpec, log_result
from .report import ReportInfo, build_report, save_report
from .sequence import Sequence
from .session import VNASession, list_ports
from .sweepdata import SweepData

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2

logger = logging.getLogger("NanoVNASaver")


def frequency(text: str) -> float:
    value = parse_frequency(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"invalid frequency: {text}")
    return float(value)


def summary(data: SweepData) -> str:
    f = data.freq / 1e6
    sw = vswr(data.s11)
    i = int(np.argmin(sw))
    lines = [
        f"{len(data)} points {f[0]:.6g} - {f[-1]:.6g} MHz",
        f"S11 best: VSWR {sw[i]:.3f}, RL {-logmag(data.s11)[i]:.2f} dB"
        f" @ {f[i]:.6g} MHz",
    ]
    if np.any(data.s21):
        g = logmag(data.s21)
        j = int(np.argmax(g))
        lines.append(f"S21 max: {g[j]:.2f} dB @ {f[j]:.6g} MHz")
    return "\n".join(lines)


def finish(
    data: SweepData,
    args: argparse.Namespace,
    info: Optional[ReportInfo] = None,
) -> int:
    print(summary(data))
    spec = LimitSpec.load(args.limits) if args.limits else None
    result: Optional[LimitResult] = spec.evaluate(data) if spec else None
    if result is not None:
        print(result.summary())
        if args.log:
            log_result(args.log, result, args.serial)
    if args.out:
        data.save(args.out)
        print(f"saved {args.out}")
    if args.report:
        save_report(args.report, build_report(data, info, spec, result))
        print(f"report {args.report}")
    if result is None:
        return EXIT_PASS
    return EXIT_PASS if result.passed else EXIT_FAIL


def add_output_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--limits", help="limit spec JSON")
    p.add_argument("--out", help="save data (.s1p / .s2p)")
    p.add_argument("--report", help="save HTML report")
    p.add_argument("--log", help="append pass/fail result to CSV")
    p.add_argument("--serial", default="", help="DUT serial number")


def cmd_ports(_: argparse.Namespace) -> int:
    for port in list_ports():
        print(port)
    return EXIT_PASS


def cmd_sweep(args: argparse.Namespace) -> int:
    with VNASession(args.device) as session:
        if args.cal:
            session.load_calibration(args.cal, args.kit)
        session.smoothing_pct = args.smooth
        session.fixture = FixtureSettings(
            port1=PortExtension(args.port1_delay * 1e-12, args.port1_loss),
            port2=PortExtension(args.port2_delay * 1e-12, args.port2_loss),
            z0=args.z0,
        )
        data = session.sweep(
            args.start,
            args.stop,
            points=args.points,
            segments=args.segments,
            averages=args.averages,
            logarithmic=args.log_sweep,
        )
        info = ReportInfo(
            title=f"VNA report {args.serial}".strip(),
            serial=args.serial,
            device=f"{session.info()['name']} ({args.device})",
            calibration=args.cal or "device",
        )
    return finish(data, args, info)


def cmd_check(args: argparse.Namespace) -> int:
    data = SweepData.load(args.file)
    info = ReportInfo(
        title=f"Report {Path(args.file).name}", serial=args.serial
    )
    return finish(data, args, info)


def cmd_run(args: argparse.Namespace) -> int:
    seq = Sequence.load(args.sequence)
    device = args.device or seq.spec.get("device", "virtual:demo")

    def prompt(message: str) -> None:
        if args.yes:
            print(f"[prompt] {message}")
            return
        input(f"{message} - press Enter to continue ")

    with VNASession(device) as session:
        result = seq.run(session, args.serial, prompt)
    if result.limit_result is not None:
        print(result.limit_result.summary())
    for f in result.files:
        print(f"wrote {f}")
    print(result.verdict)
    return EXIT_FAIL if result.passed is False else EXIT_PASS


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import ApiServer

    session = VNASession(args.device).connect()
    if args.cal:
        session.load_calibration(args.cal, args.kit)
    server = ApiServer(session, args.host, args.port)
    host, port = server.address
    print(f"Serving {session.info()['name']} on http://{host}:{port}")
    print("Endpoints: /api/info /api/sweep /api/last /api/check /ws")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        session.close()
    return EXIT_PASS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nanovna-pro",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ports", help="list detected devices").set_defaults(
        func=cmd_ports
    )

    p = sub.add_parser("sweep", help="measure, check limits, save")
    p.add_argument("-d", "--device", default="virtual:demo")
    p.add_argument("--start", type=frequency, required=True)
    p.add_argument("--stop", type=frequency, required=True)
    p.add_argument("-n", "--points", type=int)
    p.add_argument("-s", "--segments", type=int, default=1)
    p.add_argument("-a", "--averages", type=int, default=1)
    p.add_argument("--log-sweep", action="store_true")
    p.add_argument("--cal", help="NanoVNA-Saver .cal file")
    p.add_argument("--kit", default="Ideal", help="cal kit name or JSON")
    p.add_argument("--smooth", type=float, default=0.0, help="percent")
    p.add_argument("--z0", type=float, default=50.0)
    p.add_argument("--port1-delay", type=float, default=0.0, help="ps")
    p.add_argument("--port1-loss", type=float, default=0.0, help="dB@1GHz")
    p.add_argument("--port2-delay", type=float, default=0.0, help="ps")
    p.add_argument("--port2-loss", type=float, default=0.0, help="dB@1GHz")
    add_output_args(p)
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("check", help="check / report a Touchstone file")
    p.add_argument("file")
    add_output_args(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("run", help="run a test sequence (JSON)")
    p.add_argument("sequence")
    p.add_argument("--serial", default="")
    p.add_argument("-d", "--device", help="override the sequence device")
    p.add_argument(
        "-y", "--yes", action="store_true", help="do not wait at prompts"
    )
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("serve", help="REST / WebSocket API server")
    p.add_argument("-d", "--device", default="virtual:demo")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--cal")
    p.add_argument("--kit", default="Ideal")
    p.set_defaults(func=cmd_serve)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    # Windows consoles may not be able to print symbols like ≤ / Ω
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
