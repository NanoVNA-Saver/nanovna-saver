#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
import logging
from typing import TYPE_CHECKING

from PyQt6 import QtWidgets

import NanoVNASaver.AnalyticTools as At
from NanoVNASaver.Analysis.Base import Analysis, QHLine
from NanoVNASaver.Formatting import format_frequency, format_vswr

if TYPE_CHECKING:
    from NanoVNASaver.NanoVNASaver import NanoVNASaver as NanoVNA

logger = logging.getLogger(__name__)


class VSWRAnalysis(Analysis):
    MAX_DIPS_SHOWN: int = 3
    vswr_limit_value: float = 1.5

    def __init__(self, app: "NanoVNA") -> None:
        super().__init__(app)

        self._widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QFormLayout()
        self._widget.setLayout(self.layout)

        self.input_vswr_limit = QtWidgets.QDoubleSpinBox()
        self.input_vswr_limit.setValue(VSWRAnalysis.vswr_limit_value)
        self.input_vswr_limit.setSingleStep(0.1)
        self.input_vswr_limit.setMinimum(1)
        self.input_vswr_limit.setMaximum(25)
        self.input_vswr_limit.setDecimals(2)

        self.checkbox_move_marker = QtWidgets.QCheckBox()
        self.layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        self.layout.addRow("VSWR limit", self.input_vswr_limit)
        self.layout.addRow(QHLine())

        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        self.layout.addRow(self.results_label)

        self.minimums: list[int] = []

    def runAnalysis(self) -> None:
        if not self.app.data.s11:
            return
        s11 = self.app.data.s11

        data = [d.vswr for d in s11]
        threshold = self.input_vswr_limit.value()

        minima = sorted(At.minima(data, threshold), key=lambda i: data[i])[
            : VSWRAnalysis.MAX_DIPS_SHOWN
        ]
        self.minimums = minima

        results_header = self.layout.indexOf(self.results_label)
        logger.debug(
            "Results start at %d, out of %d",
            results_header,
            self.layout.rowCount(),
        )
        for _ in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)

        if not minima:
            self.layout.addRow(
                QtWidgets.QLabel(
                    f"No areas found with VSWR below {format_vswr(threshold)}."
                )
            )
            return

        for idx in minima:
            rng = At.take_from_idx(data, idx, lambda i: i[1] < threshold)
            begin, end = rng[0], rng[-1]
            self.layout.addRow(
                "Start", QtWidgets.QLabel(format_frequency(s11[begin].freq))
            )
            self.layout.addRow(
                "Minimum",
                QtWidgets.QLabel(
                    f"{format_frequency(s11[idx].freq)}"
                    f" ({round(s11[idx].vswr, 2)})"
                ),
            )
            self.layout.addRow(
                "End", QtWidgets.QLabel(format_frequency(s11[end].freq))
            )
            self.layout.addRow(
                "Span",
                QtWidgets.QLabel(
                    format_frequency((s11[end].freq - s11[begin].freq))
                ),
            )
            self.layout.addWidget(QHLine())

        self.layout.removeRow(self.layout.rowCount() - 1)
