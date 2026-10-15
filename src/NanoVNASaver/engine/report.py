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
"""Self contained HTML test reports with inline SVG charts."""

import html
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from .formats import TraceFormat, logmag, vswr
from .limits import LimitResult, LimitSpec
from .sweepdata import SweepData

COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea")
LIMIT_COLOR = "#f59e0b"


@dataclass
class Series:
    label: str
    x: np.ndarray
    y: np.ndarray
    color: str = COLORS[0]


@dataclass
class LimitLine:
    x0: float
    x1: float
    y0: float
    y1: float


def _nice_ticks(lo: float, hi: float, count: int = 6) -> list[float]:
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        return [lo]
    raw = (hi - lo) / count
    mag = 10 ** math.floor(math.log10(raw))
    step = min(
        (m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw),
        default=10 * mag,
    )
    start = math.ceil(lo / step) * step
    ticks = []
    v = start
    while v <= hi + step * 1e-9:
        ticks.append(round(v, 12))
        v += step
    return ticks


def svg_xy(  # noqa: PLR0913
    series: list[Series],
    title: str,
    xlabel: str,
    ylabel: str,
    limits: Optional[list[LimitLine]] = None,
    width: int = 760,
    height: int = 300,
) -> str:
    left, right, top, bottom = 60, 20, 30, 40
    pw, ph = width - left - right, height - top - bottom
    xs = np.concatenate([s.x for s in series]) if series else np.zeros(1)
    ys = np.concatenate([s.y[np.isfinite(s.y)] for s in series] or [[0.0]])
    limits = limits or []
    ylims = [v for lim in limits for v in (lim.y0, lim.y1)]
    if len(ys) == 0:
        ys = np.zeros(1)
    y_lo = float(min(np.min(ys), *ylims)) if ylims else float(np.min(ys))
    y_hi = float(max(np.max(ys), *ylims)) if ylims else float(np.max(ys))
    if y_hi - y_lo < 1e-9:
        y_lo, y_hi = y_lo - 1, y_hi + 1
    pad = (y_hi - y_lo) * 0.05
    y_lo, y_hi = y_lo - pad, y_hi + pad
    x_lo, x_hi = float(np.min(xs)), float(np.max(xs))
    if x_hi <= x_lo:
        x_hi = x_lo + 1

    def px(x):
        return left + (np.asarray(x) - x_lo) / (x_hi - x_lo) * pw

    def py(y):
        return top + (y_hi - np.asarray(y)) / (y_hi - y_lo) * ph

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}"'
        f' height="{height}" font-family="sans-serif" font-size="11">',
        f'<rect x="{left}" y="{top}" width="{pw}" height="{ph}"'
        ' fill="#fff" stroke="#999"/>',
        f'<text x="{width / 2}" y="18" text-anchor="middle"'
        f' font-size="13" font-weight="bold">{html.escape(title)}</text>',
    ]
    for t in _nice_ticks(y_lo, y_hi):
        y = py(t)
        out.append(
            f'<line x1="{left}" x2="{left + pw}" y1="{y:.1f}" y2="{y:.1f}"'
            ' stroke="#e5e7eb"/>'
            f'<text x="{left - 5}" y="{y + 4:.1f}" text-anchor="end">'
            f"{t:g}</text>"
        )
    for t in _nice_ticks(x_lo, x_hi):
        x = px(t)
        out.append(
            f'<line y1="{top}" y2="{top + ph}" x1="{x:.1f}" x2="{x:.1f}"'
            ' stroke="#e5e7eb"/>'
            f'<text x="{x:.1f}" y="{top + ph + 15}" text-anchor="middle">'
            f"{t:g}</text>"
        )
    out.append(
        f'<text x="{left + pw / 2}" y="{height - 5}" text-anchor="middle">'
        f"{html.escape(xlabel)}</text>"
        f'<text x="14" y="{top + ph / 2}" text-anchor="middle"'
        f' transform="rotate(-90 14 {top + ph / 2})">'
        f"{html.escape(ylabel)}</text>"
    )
    for lim in limits:
        out.append(
            f'<line x1="{px(lim.x0):.1f}" x2="{px(lim.x1):.1f}"'
            f' y1="{py(lim.y0):.1f}" y2="{py(lim.y1):.1f}"'
            f' stroke="{LIMIT_COLOR}" stroke-width="2"'
            ' stroke-dasharray="6 3"/>'
        )
    for i, s in enumerate(series):
        mask = np.isfinite(s.y)
        pts = " ".join(
            f"{x:.1f},{y:.1f}"
            for x, y in zip(
                px(s.x[mask]), py(np.clip(s.y[mask], y_lo, y_hi)), strict=True
            )
        )
        out.append(
            f'<polyline fill="none" stroke="{s.color}" stroke-width="1.5"'
            f' points="{pts}"/>'
            f'<text x="{left + 8}" y="{top + 14 + 13 * i}"'
            f' fill="{s.color}">{html.escape(s.label)}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def svg_smith(
    series: list[tuple[str, np.ndarray, str]], size: int = 360
) -> str:
    c = size / 2
    r = size / 2 - 10

    def pt(z):
        return c + z.real * r, c - z.imag * r

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}"'
        f' height="{size}" font-family="sans-serif" font-size="11">',
        f'<circle cx="{c}" cy="{c}" r="{r}" fill="#fff" stroke="#999"/>',
        f'<line x1="{c - r}" x2="{c + r}" y1="{c}" y2="{c}" stroke="#ddd"/>',
    ]
    for rn in (0.2, 0.5, 1, 2, 5):
        cx = c + rn / (1 + rn) * r
        out.append(
            f'<circle cx="{cx:.1f}" cy="{c}" r="{r / (1 + rn):.1f}"'
            ' fill="none" stroke="#ddd"/>'
        )
    for xn in (0.2, 0.5, 1, 2, 5):
        for sign in (1, -1):
            x = sign * xn
            t = np.linspace(-50, 50, 400)
            z = (t + 1j * x - 1) / (t + 1j * x + 1)
            pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in map(pt, z))
            out.append(f'<polyline fill="none" stroke="#ddd" points="{pts}"/>')
    for i, (label, values, color) in enumerate(series):
        pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in map(pt, values))
        out.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="1.5"'
            f' points="{pts}"/><text x="8" y="{16 + 13 * i}"'
            f' fill="{color}">{html.escape(label)}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def _limit_lines(spec: Optional[LimitSpec], param: str) -> list[LimitLine]:
    if spec is None:
        return []
    return [
        LimitLine(
            seg.start / 1e6,
            seg.stop / 1e6,
            seg.value,
            seg.value if seg.value_stop is None else seg.value_stop,
        )
        for seg in spec.limits
        if seg.param == param and seg.trace_format is TraceFormat.LOGMAG
    ]


@dataclass
class ReportInfo:
    title: str = "VNA test report"
    serial: str = ""
    operator: str = ""
    device: str = ""
    calibration: str = ""
    notes: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def build_report(
    data: SweepData,
    info: Optional[ReportInfo] = None,
    spec: Optional[LimitSpec] = None,
    result: Optional[LimitResult] = None,
) -> str:
    info = info or ReportInfo()
    if spec is not None and result is None:
        result = spec.evaluate(data)
    f_mhz = data.freq / 1e6
    charts = []
    params = ["s11", "s21"] + (["s12", "s22"] if data.is_full_two_port else [])
    for i, name in enumerate(params):
        values = data.param(name)
        if values is None or not np.any(values):
            continue
        charts.append(
            svg_xy(
                [Series(name.upper(), f_mhz, logmag(values), COLORS[i])],
                f"{name.upper()} log magnitude",
                "Frequency (MHz)",
                "dB",
                _limit_lines(spec, name),
            )
        )
    charts.append(
        svg_smith(
            [("S11", data.s11, COLORS[0])]
            + ([("S22", data.s22, COLORS[3])] if data.s22 is not None else [])
        )
    )

    rows = []
    sw = vswr(data.s11)
    i_min = int(np.argmin(sw)) if len(sw) else 0
    if len(sw):
        rows.append(
            ("Min VSWR (S11)", f"{sw[i_min]:.3f} @ {f_mhz[i_min]:.6g} MHz")
        )
        rows.append(("Best return loss", f"{-logmag(data.s11)[i_min]:.2f} dB"))
    if np.any(data.s21):
        gain = logmag(data.s21)
        rows.append(
            (
                "S21 max / min",
                f"{np.max(gain):.2f} dB / {np.min(gain):.2f} dB",
            )
        )
    rows.append(
        (
            "Sweep",
            f"{f_mhz[0]:.6g} - {f_mhz[-1]:.6g} MHz, {len(data)} points"
            if len(data)
            else "no data",
        )
    )

    verdict = ""
    if result is not None:
        state = "PASS" if result.passed else "FAIL"
        color = "#16a34a" if result.passed else "#dc2626"
        seg_rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(r.segment.describe()),
                "skipped" if r.skipped else ("pass" if r.passed else "FAIL"),
                "" if r.skipped else f"{r.worst_margin:+.3g}",
                "" if r.skipped else f"{r.worst_freq / 1e6:.6g} MHz",
            )
            for r in result.segments
        )
        verdict = (
            f'<div class="verdict" style="background:{color}">{state}</div>'
            f"<h2>Limits: {html.escape(result.name)}</h2>"
            "<table><tr><th>Limit</th><th>Result</th><th>Worst margin</th>"
            f"<th>at</th></tr>{seg_rows}</table>"
        )

    meta = [
        ("Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Serial / DUT", info.serial),
        ("Operator", info.operator),
        ("Instrument", info.device),
        ("Calibration", info.calibration),
        ("Reference impedance", f"{data.z0:g} Ω"),
        *info.extra.items(),
    ]
    meta_html = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in meta
        if v
    )
    summary_html = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"
        for k, v in rows
    )
    notes = (
        f"<h2>Notes</h2><p>{html.escape(info.notes)}</p>" if info.notes else ""
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>{html.escape(info.title)}</title>
<style>
body {{ font-family: sans-serif; margin: 24px; color: #111; }}
table {{ border-collapse: collapse; margin: 8px 0 16px; }}
th, td {{ border: 1px solid #ddd; padding: 4px 10px; text-align: left; }}
th {{ background: #f3f4f6; }}
.verdict {{ color: #fff; font-size: 28px; font-weight: bold;
  display: inline-block; padding: 6px 24px; border-radius: 6px; }}
svg {{ margin: 6px 0; }}
</style></head><body>
<h1>{html.escape(info.title)}</h1>
{verdict}
<h2>Measurement</h2><table>{meta_html}</table>
<table>{summary_html}</table>
{"".join(charts)}
{notes}
<p style="color:#888">Generated by NanoVNA-Saver</p>
</body></html>
"""


def save_report(path: str | Path, report: str) -> None:
    Path(path).write_text(report, encoding="utf-8")


__all__ = [
    "ReportInfo",
    "build_report",
    "save_report",
    "svg_smith",
    "svg_xy",
]
