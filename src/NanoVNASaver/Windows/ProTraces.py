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
"""Bench top VNA style trace display (pyqtgraph based).

4 traces, each with its own parameter and format, memory traces and
trace math, 4 markers with search functions, limit lines with pass/fail
and HTML reports."""

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ..engine.dsp import group_delay_aperture_points
from ..engine.formats import TraceFormat, convert
from ..engine.limits import LimitResult, LimitSpec, log_result
from ..engine.report import ReportInfo, build_report, save_report
from ..engine.search import (
    next_peak,
    search_bandwidth,
    search_max,
    search_min,
    search_target,
)
from ..engine.sweepdata import SweepData
from ..engine.tdr import time_gate
from ..RFTools import reference_impedance
from .ui import get_window_icon

if TYPE_CHECKING:
    from ..NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app

logger = logging.getLogger(__name__)

TRACE_COLORS = ("#facc15", "#22d3ee", "#f472b6", "#4ade80")
MARKER_COLORS = ("#ffffff", "#fb923c", "#a78bfa", "#38bdf8")
LIMIT_PEN = pg.mkPen("#f59e0b", width=2, style=QtCore.Qt.PenStyle.DashLine)
GRID_PEN = pg.mkPen("#3f3f46", width=1)
N_TRACES = 4
N_MARKERS = 4

PARAMS = (
    ("S11", "s11"),
    ("S21", "s21"),
    ("S12", "s12"),
    ("S22", "s22"),
    ("S11 gated (TDR gate)", "s11g"),
)
MEMORY_MODES = (
    ("Data", "off"),
    ("Data + Mem", "show"),
    ("Data / Mem", "divide"),
    ("Data - Mem", "subtract"),
)
DEFAULT_TRACES = (
    ("s11", TraceFormat.LOGMAG, True),
    ("s11", TraceFormat.SMITH, True),
    ("s21", TraceFormat.LOGMAG, True),
    ("s21", TraceFormat.PHASE, False),
)
NO_SI_PREFIX = {"dB", "°", "", "U"}


def eng(value: float, unit: str) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    if unit in NO_SI_PREFIX:
        return f"{value:.4g} {unit}".strip()
    if value == 0:
        return f"0 {unit}"
    exp = int(math.floor(math.log10(abs(value)) / 3) * 3)
    exp = max(min(exp, 9), -15)
    prefix = {
        -15: "f",
        -12: "p",
        -9: "n",
        -6: "µ",
        -3: "m",
        0: "",
        3: "k",
        6: "M",
        9: "G",
    }[exp]
    return f"{value / 10**exp:.4g} {prefix}{unit}"


@dataclass
class TraceConfig:
    enabled: bool = True
    param: str = "s11"
    fmt: TraceFormat = TraceFormat.LOGMAG
    memory: str = "off"


class TracePane(pg.PlotWidget):
    """One trace in its own plot (like one window of a bench top VNA)"""

    marker_moved = QtCore.Signal(int, float)

    def __init__(self, index: int) -> None:
        super().__init__(background="#18181b")
        self.index = index
        self.color = TRACE_COLORS[index]
        self.fmt: Optional[TraceFormat] = None
        self.plot_item = self.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.25)
        self.curve = self.plot_item.plot(pen=pg.mkPen(self.color, width=1.5))
        self.curve.setClipToView(True)
        self.curve.setDownsampling(auto=True, method="peak")
        self.mem_curve = self.plot_item.plot(
            pen=pg.mkPen(self.color, width=1, style=QtCore.Qt.PenStyle.DotLine)
        )
        self.static_items: list = []
        self.limit_items: list = []
        self.marker_lines: list[Optional[pg.InfiniteLine]] = [None] * N_MARKERS
        self.marker_points = pg.ScatterPlotItem(size=9)
        self.plot_item.addItem(self.marker_points)
        self.title_text = ""

    # setup

    def set_format(self, fmt: TraceFormat, title: str) -> None:
        self.title_text = title
        self.plot_item.setTitle(title, color=self.color)
        if fmt == self.fmt:
            return
        self.fmt = fmt
        # clip to view / downsampling need ascending x values, which a
        # Smith or polar trace (x = Re) does not have
        for curve in (self.curve, self.mem_curve):
            curve.setClipToView(not fmt.is_complex_plane)
            if fmt.is_complex_plane:
                curve.setDownsampling(ds=1, auto=False)
            else:
                curve.setDownsampling(auto=True, method="peak")
        for item in self.static_items:
            self.plot_item.removeItem(item)
        self.static_items = []
        for i, line in enumerate(self.marker_lines):
            if line is not None:
                self.plot_item.removeItem(line)
                self.marker_lines[i] = None
        if fmt.is_complex_plane:
            self.plot_item.setAspectLocked(True)
            self.plot_item.showGrid(x=False, y=False)
            self.plot_item.hideAxis("left")
            self.plot_item.hideAxis("bottom")
            self._draw_complex_grid(fmt is TraceFormat.SMITH)
            self.plot_item.setRange(xRange=(-1.05, 1.05), yRange=(-1.05, 1.05))
        else:
            self.plot_item.setAspectLocked(False)
            self.plot_item.showGrid(x=True, y=True, alpha=0.25)
            self.plot_item.showAxis("left")
            self.plot_item.showAxis("bottom")
            self.plot_item.setLabel("bottom", "Frequency", units="Hz")
            self.plot_item.setLabel("left", fmt.label, units=fmt.unit)
            self.plot_item.getAxis("left").enableAutoSIPrefix(
                fmt.unit not in NO_SI_PREFIX
            )
            self.plot_item.enableAutoRange()

    def _add_static(self, x, y) -> None:
        item = self.plot_item.plot(x, y, pen=GRID_PEN)
        self.static_items.append(item)

    def _draw_complex_grid(self, smith: bool) -> None:
        t = np.linspace(0, 2 * np.pi, 361)
        self._add_static(np.cos(t), np.sin(t))
        self._add_static(np.array([-1, 1]), np.array([0, 0]))
        if not smith:
            for r in (0.25, 0.5, 0.75):
                self._add_static(r * np.cos(t), r * np.sin(t))
            return
        for rn in (0.2, 0.5, 1.0, 2.0, 5.0):
            c, rad = rn / (1 + rn), 1 / (1 + rn)
            self._add_static(c + rad * np.cos(t), rad * np.sin(t))
        r_param = np.concatenate([np.linspace(0, 10, 300), [50, 200, 1e4]])
        for xn in (0.2, 0.5, 1.0, 2.0, 5.0):
            for sign in (1, -1):
                z = r_param + 1j * sign * xn
                g = (z - 1) / (z + 1)
                self._add_static(g.real, g.imag)

    # data

    def set_data(self, x, y, mem_x=None, mem_y=None) -> None:
        if self.fmt is not None and self.fmt.is_complex_plane:
            self.curve.setData(np.real(y), np.imag(y))
            if mem_y is not None:
                self.mem_curve.setData(np.real(mem_y), np.imag(mem_y))
            else:
                self.mem_curve.clear()
            return
        y = np.asarray(y, dtype=float)
        finite = np.isfinite(y)
        self.curve.setData(x[finite], y[finite])
        if mem_y is not None and mem_x is not None:
            mem_y = np.asarray(mem_y, dtype=float)
            mf = np.isfinite(mem_y)
            self.mem_curve.setData(mem_x[mf], mem_y[mf])
        else:
            self.mem_curve.clear()

    def clear_data(self) -> None:
        self.curve.clear()
        self.mem_curve.clear()
        self.marker_points.clear()

    def set_limits(self, segments: list) -> None:
        for item in self.limit_items:
            self.plot_item.removeItem(item)
        self.limit_items = []
        if self.fmt is None or self.fmt.is_complex_plane:
            return
        for seg in segments:
            y1 = seg.value if seg.value_stop is None else seg.value_stop
            item = self.plot_item.plot(
                [seg.start, seg.stop], [seg.value, y1], pen=LIMIT_PEN
            )
            self.limit_items.append(item)

    def set_markers(self, positions: list[Optional[tuple[float, complex]]]):
        """positions: per marker (freq, value) or None"""
        if self.fmt is None:
            return
        spots = []
        for i, pos in enumerate(positions):
            line = self.marker_lines[i]
            if pos is None:
                if line is not None:
                    line.hide()
                continue
            freq, value = pos
            if self.fmt.is_complex_plane:
                spots.append(
                    {
                        "pos": (value.real, value.imag),
                        "brush": MARKER_COLORS[i],
                        "pen": None,
                    }
                )
                continue
            if line is None:
                line = pg.InfiniteLine(
                    angle=90,
                    movable=True,
                    pen=pg.mkPen(MARKER_COLORS[i], width=1),
                    label=f"M{i + 1}",
                    labelOpts={"position": 0.95, "color": MARKER_COLORS[i]},
                )
                line.sigPositionChangeFinished.connect(
                    lambda ln, idx=i: self.marker_moved.emit(idx, ln.value())
                )
                self.plot_item.addItem(line)
                self.marker_lines[i] = line
            line.blockSignals(True)
            line.setValue(freq)
            line.blockSignals(False)
            line.show()
            if np.isfinite(value.real):
                spots.append(
                    {
                        "pos": (freq, value.real),
                        "brush": MARKER_COLORS[i],
                        "pen": None,
                    }
                )
        self.marker_points.setData(spots)


class ProTracesWindow(QtWidgets.QWidget):
    # pylint: disable=too-many-instance-attributes
    def __init__(self, app: "vna_app"):
        super().__init__()
        self.app = app
        self.setWindowTitle("Traces, markers & limits")
        self.setWindowIcon(get_window_icon())
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)
        self.resize(1300, 850)

        self.configs = [
            TraceConfig(enabled, param, fmt)
            for param, fmt, enabled in DEFAULT_TRACES
        ]
        self.data = SweepData()
        self.memory: Optional[SweepData] = None
        self.marker_freqs: list[Optional[float]] = [None] * N_MARKERS
        # marker -> (search, trace) re-run on every new sweep
        self.tracking: dict[int, tuple[str, int]] = {}
        self.spec: Optional[LimitSpec] = None
        self.last_result: Optional[LimitResult] = None
        self.log_path: Optional[Path] = None
        self._dirty = True

        splitter = QtWidgets.QSplitter()
        outer = QtWidgets.QHBoxLayout(self)
        outer.addWidget(splitter)

        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QVBoxLayout(controls)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(380)
        splitter.addWidget(scroll)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.verdict = QtWidgets.QLabel("")
        self.verdict.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.verdict.setVisible(False)
        right_layout.addWidget(self.verdict)
        grid_widget = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(grid_widget, 1)
        self.marker_table = QtWidgets.QTableWidget(N_MARKERS, 1 + N_TRACES)
        self.marker_table.setHorizontalHeaderLabels(
            ["Frequency"] + [f"Tr{i + 1}" for i in range(N_TRACES)]
        )
        self.marker_table.setVerticalHeaderLabels(
            [f"M{i + 1}" for i in range(N_MARKERS)]
        )
        self.marker_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.marker_table.setMaximumHeight(150)
        self.marker_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        right_layout.addWidget(self.marker_table)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        self.panes = [TracePane(i) for i in range(N_TRACES)]
        for pane in self.panes:
            pane.marker_moved.connect(self.marker_dragged)

        controls_layout.addWidget(self.trace_box())
        controls_layout.addWidget(self.memory_box())
        controls_layout.addWidget(self.marker_box())
        controls_layout.addWidget(self.limit_box())
        controls_layout.addWidget(self.report_box())
        controls_layout.addStretch(1)

        self.layout_panes()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.app.communicate.data_available.connect(self.mark_dirty)
        self.app.worker.signals.finished.connect(self.sweep_finished)

    # ---------------------------------------------------------------- UI

    def trace_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Traces")
        grid = QtWidgets.QGridLayout(box)
        self.trace_widgets = []
        for i, cfg in enumerate(self.configs):
            show = QtWidgets.QCheckBox(f"Tr{i + 1}")
            show.setStyleSheet(f"color: {TRACE_COLORS[i]}; font-weight: bold")
            show.setChecked(cfg.enabled)
            param = QtWidgets.QComboBox()
            for label, key in PARAMS:
                param.addItem(label, key)
            param.setCurrentIndex([k for _, k in PARAMS].index(cfg.param))
            fmt = QtWidgets.QComboBox()
            for f in TraceFormat:
                fmt.addItem(f.label, f)
            fmt.setCurrentIndex(list(TraceFormat).index(cfg.fmt))
            mem = QtWidgets.QComboBox()
            for label, key in MEMORY_MODES:
                mem.addItem(label, key)
            for w in (show, param, fmt, mem):
                signal = (
                    w.toggled
                    if isinstance(w, QtWidgets.QCheckBox)
                    else w.currentIndexChanged
                )
                signal.connect(self.config_changed)
            grid.addWidget(show, i, 0)
            grid.addWidget(param, i, 1)
            grid.addWidget(fmt, i, 2)
            grid.addWidget(mem, i, 3)
            self.trace_widgets.append((show, param, fmt, mem))
        self.gd_aperture = QtWidgets.QDoubleSpinBox()
        self.gd_aperture.setRange(0.0, 20.0)
        self.gd_aperture.setSingleStep(0.5)
        self.gd_aperture.setValue(1.0)
        self.gd_aperture.setSuffix(" %")
        self.gd_aperture.valueChanged.connect(self.config_changed)
        grid.addWidget(
            QtWidgets.QLabel("Group delay aperture"), N_TRACES, 0, 1, 2
        )
        grid.addWidget(self.gd_aperture, N_TRACES, 2, 1, 2)
        return box

    def memory_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Memory")
        row = QtWidgets.QHBoxLayout(box)
        btn = QtWidgets.QPushButton("Data → Memory")
        btn.clicked.connect(self.data_to_memory)
        clear = QtWidgets.QPushButton("Clear")
        clear.clicked.connect(self.clear_memory)
        self.memory_label = QtWidgets.QLabel("empty")
        row.addWidget(btn)
        row.addWidget(clear)
        row.addWidget(self.memory_label, 1)
        return box

    def marker_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Markers & search")
        grid = QtWidgets.QGridLayout(box)
        self.marker_select = QtWidgets.QComboBox()
        self.marker_select.addItems([f"M{i + 1}" for i in range(N_MARKERS)])
        self.trace_select = QtWidgets.QComboBox()
        self.trace_select.addItems([f"Tr{i + 1}" for i in range(N_TRACES)])
        grid.addWidget(QtWidgets.QLabel("Marker"), 0, 0)
        grid.addWidget(self.marker_select, 0, 1)
        grid.addWidget(QtWidgets.QLabel("on trace"), 0, 2)
        grid.addWidget(self.trace_select, 0, 3)
        buttons = (
            ("Min", self.search_min),
            ("Max", self.search_max),
            ("◀ Peak", lambda: self.search_peak(-1)),
            ("Peak ▶", lambda: self.search_peak(1)),
            ("Center", self.marker_center),
            ("Off", self.marker_off),
        )
        for i, (label, slot) in enumerate(buttons):
            btn = QtWidgets.QPushButton(label)
            btn.clicked.connect(slot)
            grid.addWidget(btn, 1 + i // 3, i % 3)
        self.target_value = QtWidgets.QDoubleSpinBox()
        self.target_value.setRange(-1e9, 1e9)
        self.target_value.setDecimals(3)
        self.target_value.setValue(-10.0)
        btn_target = QtWidgets.QPushButton("Target ▶")
        btn_target.clicked.connect(self.search_target)
        grid.addWidget(QtWidgets.QLabel("Target"), 3, 0)
        grid.addWidget(self.target_value, 3, 1)
        grid.addWidget(btn_target, 3, 2)
        self.bw_value = QtWidgets.QDoubleSpinBox()
        self.bw_value.setRange(0.1, 60.0)
        self.bw_value.setValue(3.0)
        self.bw_value.setSuffix(" dB")
        self.bw_notch = QtWidgets.QCheckBox("Notch")
        btn_bw = QtWidgets.QPushButton("Bandwidth")
        btn_bw.clicked.connect(self.search_bandwidth)
        grid.addWidget(QtWidgets.QLabel("BW level"), 4, 0)
        grid.addWidget(self.bw_value, 4, 1)
        grid.addWidget(self.bw_notch, 4, 2)
        grid.addWidget(btn_bw, 4, 3)
        self.track_check = QtWidgets.QCheckBox(
            "Track: repeat Min/Max on every sweep"
        )
        grid.addWidget(self.track_check, 6, 0, 1, 4)
        self.search_result = QtWidgets.QLabel("")
        self.search_result.setWordWrap(True)
        self.search_result.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        grid.addWidget(self.search_result, 5, 0, 1, 4)
        return box

    def limit_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Limit lines / pass-fail")
        grid = QtWidgets.QGridLayout(box)
        load = QtWidgets.QPushButton("Load limits ...")
        load.clicked.connect(self.load_limits)
        clear = QtWidgets.QPushButton("Clear")
        clear.clicked.connect(self.clear_limits)
        example = QtWidgets.QPushButton("Save example ...")
        example.clicked.connect(self.save_example_limits)
        grid.addWidget(load, 0, 0)
        grid.addWidget(clear, 0, 1)
        grid.addWidget(example, 0, 2)
        self.limit_label = QtWidgets.QLabel("No limits loaded")
        self.limit_label.setWordWrap(True)
        grid.addWidget(self.limit_label, 1, 0, 1, 3)
        self.log_check = QtWidgets.QCheckBox("Log every finished sweep to CSV")
        self.log_check.toggled.connect(self.toggle_log)
        grid.addWidget(self.log_check, 2, 0, 1, 3)
        return box

    def report_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Report")
        form = QtWidgets.QFormLayout(box)
        self.serial_input = QtWidgets.QLineEdit()
        self.serial_input.setPlaceholderText("DUT serial number")
        self.operator_input = QtWidgets.QLineEdit()
        btn = QtWidgets.QPushButton("Save HTML report ...")
        btn.clicked.connect(self.save_report)
        form.addRow("Serial", self.serial_input)
        form.addRow("Operator", self.operator_input)
        form.addRow(btn)
        return box

    def layout_panes(self) -> None:
        for pane in self.panes:
            self.grid.removeWidget(pane)
            pane.setParent(None)
        active = [
            p
            for p, c in zip(self.panes, self.configs, strict=True)
            if c.enabled
        ]
        cols = 1 if len(active) <= 1 else 2
        for n, pane in enumerate(active):
            self.grid.addWidget(pane, n // cols, n % cols)
            pane.show()

    # ------------------------------------------------------------- config

    def config_changed(self) -> None:
        relayout = False
        for cfg, (show, param, fmt, mem) in zip(
            self.configs, self.trace_widgets, strict=True
        ):
            if cfg.enabled != show.isChecked():
                relayout = True
            cfg.enabled = show.isChecked()
            cfg.param = param.currentData()
            cfg.fmt = fmt.currentData()
            cfg.memory = mem.currentData()
        if relayout:
            self.layout_panes()
        self.refresh(fetch=False)

    def mark_dirty(self) -> None:
        self._dirty = True

    def _tick(self) -> None:
        if self._dirty and self.isVisible():
            self._dirty = False
            self.refresh()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    # --------------------------------------------------------------- data

    def fetch(self) -> None:
        with self.app.dataLock:
            data = SweepData.from_datapoints(
                self.app.data.s11,
                self.app.data.s21,
                self.app.data.s12,
                self.app.data.s22,
            )
        data.z0 = reference_impedance()
        self.data = data

    def source(self, data: SweepData, param: str) -> Optional[np.ndarray]:
        if len(data) == 0:
            return None
        if param == "s11g":
            gate = self.app.windows["tdr"].gate_settings()
            if gate is None:
                return None
            start, stop, mode = gate
            return time_gate(data.freq, data.s11, start, stop, mode)
        return data.param(param)

    def trace_values(self, cfg: TraceConfig, data: SweepData):
        """(complex values after memory math, displayed y)"""
        values = self.source(data, cfg.param)
        if values is None:
            return None, None
        mem = self.memory_values(cfg)
        if mem is not None and cfg.memory == "divide":
            with np.errstate(divide="ignore", invalid="ignore"):
                values = values / mem
        elif mem is not None and cfg.memory == "subtract":
            values = values - mem
        ap = group_delay_aperture_points(len(values), self.gd_aperture.value())
        y = convert(cfg.fmt, data.freq, values, data.z0, ap)
        return values, y

    def memory_values(self, cfg: TraceConfig) -> Optional[np.ndarray]:
        if self.memory is None or len(self.memory) != len(self.data):
            return None
        if not np.allclose(self.memory.freq, self.data.freq):
            return None
        return self.source(self.memory, cfg.param)

    def refresh(self, fetch: bool = True) -> None:
        if fetch:
            self.fetch()
        data = self.data
        for i, (pane, cfg) in enumerate(
            zip(self.panes, self.configs, strict=True)
        ):
            if not cfg.enabled:
                continue
            label = {k: lab for lab, k in PARAMS}[cfg.param]
            mode = {k: lab for lab, k in MEMORY_MODES}[cfg.memory]
            title = f"Tr{i + 1}: {label} {cfg.fmt.label}"
            if cfg.memory != "off":
                title += f" ({mode})"
            pane.set_format(cfg.fmt, title)
            _, y = self.trace_values(cfg, data)
            if y is None:
                pane.clear_data()
                continue
            mem_y = None
            if (
                cfg.memory == "show"
                and (m := self.memory_values(cfg)) is not None
            ):
                ap = group_delay_aperture_points(
                    len(m), self.gd_aperture.value()
                )
                mem_y = convert(cfg.fmt, data.freq, m, data.z0, ap)
            pane.set_data(data.freq, y, data.freq, mem_y)
            pane.set_limits(
                [
                    s
                    for s in (self.spec.limits if self.spec else [])
                    if s.param == cfg.param and s.trace_format is cfg.fmt
                ]
            )
        self.apply_tracking()
        self.update_markers()
        self.update_verdict()

    # ------------------------------------------------------------ markers

    def _index(self, freq: float) -> int:
        return int(np.argmin(np.abs(self.data.freq - freq)))

    def update_markers(self) -> None:
        data = self.data
        positions_per_trace = []
        for col, cfg in enumerate(self.configs):
            values, y = (
                self.trace_values(cfg, data) if cfg.enabled else (None, None)
            )
            positions = []
            for m, freq in enumerate(self.marker_freqs):
                item_text = "—"
                if freq is None or values is None or len(data) == 0:
                    positions.append(None)
                else:
                    idx = self._index(freq)
                    if cfg.fmt.is_complex_plane:
                        positions.append((data.freq[idx], complex(values[idx])))
                        item_text = self._complex_text(
                            cfg, values[idx], data.freq[idx]
                        )
                    else:
                        positions.append(
                            (data.freq[idx], complex(float(y[idx]), 0))
                        )
                        item_text = eng(float(y[idx]), cfg.fmt.unit)
                self.marker_table.setItem(
                    m, col + 1, QtWidgets.QTableWidgetItem(item_text)
                )
            positions_per_trace.append(positions)
        for m, freq in enumerate(self.marker_freqs):
            text = "off"
            if freq is not None and len(data):
                text = eng(float(data.freq[self._index(freq)]), "Hz")
            self.marker_table.setItem(m, 0, QtWidgets.QTableWidgetItem(text))
        for pane, cfg, positions in zip(
            self.panes, self.configs, positions_per_trace, strict=True
        ):
            if cfg.enabled:
                pane.set_markers(positions)

    def _complex_text(self, cfg: TraceConfig, value: complex, freq: float):
        if cfg.fmt is TraceFormat.POLAR:
            return f"{abs(value):.4f} ∠ {math.degrees(np.angle(value)):.2f}°"
        z0 = self.data.z0
        z = z0 * (1 + value) / (1 - value) if value != 1 else complex(np.inf)
        reactive = (
            eng(z.imag / (2 * math.pi * freq), "H")
            if z.imag >= 0
            else eng(-1 / (2 * math.pi * freq * z.imag), "F")
        )
        return f"{z.real:.2f} {z.imag:+.2f}j Ω ({reactive})"

    def marker_dragged(self, marker: int, freq: float) -> None:
        if len(self.data):
            self.marker_freqs[marker] = float(self.data.freq[self._index(freq)])
        self.update_markers()

    def _search_context(self):
        trace = self.trace_select.currentIndex()
        cfg = self.configs[trace]
        marker = self.marker_select.currentIndex()
        if cfg.fmt.is_complex_plane:
            self.search_result.setText(
                "Select a trace with a rectangular format for searching."
            )
            return None
        _, y = self.trace_values(cfg, self.data)
        if y is None:
            self.search_result.setText("No data for this trace.")
            return None
        return marker, np.real(np.asarray(y, dtype=float)), cfg

    def _set_marker(self, marker: int, index: int) -> None:
        self.marker_freqs[marker] = float(self.data.freq[index])
        self.update_markers()

    def _remember(self, marker: int, search: str) -> None:
        if self.track_check.isChecked():
            self.tracking[marker] = (search, self.trace_select.currentIndex())
        else:
            self.tracking.pop(marker, None)

    def search_min(self) -> None:
        if ctx := self._search_context():
            marker, y, _ = ctx
            self._remember(marker, "min")
            self._set_marker(marker, search_min(y))

    def search_max(self) -> None:
        if ctx := self._search_context():
            marker, y, _ = ctx
            self._remember(marker, "max")
            self._set_marker(marker, search_max(y))

    def apply_tracking(self) -> None:
        for marker, (search, trace) in self.tracking.items():
            cfg = self.configs[trace]
            if not cfg.enabled or cfg.fmt.is_complex_plane:
                continue
            _, y = self.trace_values(cfg, self.data)
            if y is None or len(y) == 0:
                continue
            y = np.real(np.asarray(y, dtype=float))
            idx = search_min(y) if search == "min" else search_max(y)
            self.marker_freqs[marker] = float(self.data.freq[idx])

    def search_peak(self, direction: int) -> None:
        if ctx := self._search_context():
            marker, y, _ = ctx
            current = self.marker_freqs[marker]
            start = (
                self._index(current)
                if current is not None
                else (0 if direction > 0 else len(y) - 1)
            )
            idx = next_peak(y, start, direction)
            if idx is None:
                self.search_result.setText("No further peak.")
                return
            self._set_marker(marker, idx)

    def search_target(self) -> None:
        if ctx := self._search_context():
            marker, y, cfg = ctx
            current = self.marker_freqs[marker]
            start = self._index(current) + 1 if current is not None else 0
            freq = search_target(
                self.data.freq, y, self.target_value.value(), start, 1
            )
            if freq is None:
                self.search_result.setText("Target not found.")
                return
            self.marker_freqs[marker] = float(self.data.freq[self._index(freq)])
            self.search_result.setText(
                f"{self.target_value.value():g} {cfg.fmt.unit} at"
                f" {eng(freq, 'Hz')}"
            )
            self.update_markers()

    def search_bandwidth(self) -> None:
        if ctx := self._search_context():
            marker, y, _ = ctx
            res = search_bandwidth(
                self.data.freq,
                y,
                -self.bw_value.value(),
                notch=self.bw_notch.isChecked(),
            )
            if res is None:
                self.search_result.setText(
                    "Bandwidth edges not found inside the sweep."
                )
                return
            self._set_marker(marker, res.peak_index)
            self.search_result.setText(
                f"Center {eng(res.center, 'Hz')}"
                f"   BW {eng(res.bandwidth, 'Hz')}"
                f"   Q {res.q:.1f}\nLow {eng(res.low, 'Hz')}"
                f"   High {eng(res.high, 'Hz')}   Peak {res.peak_value:.3f}"
            )

    def marker_center(self) -> None:
        if len(self.data):
            self._set_marker(
                self.marker_select.currentIndex(), len(self.data) // 2
            )

    def marker_off(self) -> None:
        self.marker_freqs[self.marker_select.currentIndex()] = None
        self.tracking.pop(self.marker_select.currentIndex(), None)
        self.update_markers()

    # ------------------------------------------------------------- memory

    def data_to_memory(self) -> None:
        self.memory = self.data.copy()
        self.memory_label.setText(f"{len(self.memory)} points stored")
        self.refresh(fetch=False)

    def clear_memory(self) -> None:
        self.memory = None
        self.memory_label.setText("empty")
        self.refresh(fetch=False)

    # ------------------------------------------------------------- limits

    def load_limits(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load limits", "", "Limit files (*.json)"
        )
        if not filename:
            return
        try:
            self.spec = LimitSpec.load(filename)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            self.app.showError(f"Invalid limit file: {exc}")
            return
        self.limit_label.setText(
            f"{self.spec.name}:\n"
            + "\n".join(s.describe() for s in self.spec.limits)
        )
        self.refresh(fetch=False)

    def clear_limits(self) -> None:
        self.spec = None
        self.last_result = None
        self.limit_label.setText("No limits loaded")
        self.refresh(fetch=False)

    def save_example_limits(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save example limit file", "limits.json", "JSON (*.json)"
        )
        if not filename:
            return
        from ..engine.limits import LimitSegment

        f0 = float(self.data.freq[0]) if len(self.data) else 1e6
        f1 = float(self.data.freq[-1]) if len(self.data) else 1e9
        LimitSpec(
            "Example",
            [
                LimitSegment("s11", "logmag", "upper", f0, f1, -10.0),
                LimitSegment("s21", "logmag", "lower", f0, f1, -3.0),
            ],
        ).save(filename)

    def toggle_log(self, on: bool) -> None:
        if not on:
            self.log_path = None
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Result log", "results.csv", "CSV (*.csv)"
        )
        if not filename:
            self.log_check.setChecked(False)
            return
        self.log_path = Path(filename)

    def update_verdict(self) -> None:
        if self.spec is None or len(self.data) == 0:
            self.verdict.setVisible(False)
            return
        self.last_result = self.spec.evaluate(self.data)
        passed = self.last_result.passed
        self.verdict.setText("PASS" if passed else "FAIL")
        self.verdict.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: white;"
            f" background: {'#16a34a' if passed else '#dc2626'};"
            " padding: 4px;"
        )
        self.verdict.setToolTip(self.last_result.summary())
        self.verdict.setVisible(True)

    def sweep_finished(self) -> None:
        if self.spec is None or self.log_path is None:
            return
        self.fetch()
        result = self.spec.evaluate(self.data)
        log_result(self.log_path, result, self.serial_input.text())
        logger.info("Logged result: %s", "PASS" if result.passed else "FAIL")

    # ------------------------------------------------------------- report

    def save_report(self) -> None:
        if len(self.data) == 0:
            self.app.showError("No data for a report.")
            return
        serial = self.serial_input.text().strip()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save report",
            f"{serial or 'report'}.html",
            "HTML (*.html)",
        )
        if not filename:
            return
        info = ReportInfo(
            title=f"VNA report {serial}".strip(),
            serial=serial,
            operator=self.operator_input.text(),
            device=f"{self.app.vna.name} {self.app.vna.SN}"
            if self.app.vna.connected()
            else "",
            calibration=self.app.calibration.source
            if self.app.calibration.isCalculated
            else "device",
            extra={"Processing": self.app.worker.processing_tag()},
        )
        save_report(filename, build_report(self.data, info, self.spec))
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(filename))
