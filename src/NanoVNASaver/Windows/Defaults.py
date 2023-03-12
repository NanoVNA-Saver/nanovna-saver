#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020 Rune B. Broberg
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
import logging

from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)


def make_scrollable(
    window: QtWidgets.QWidget, layout: QtWidgets.QLayout
) -> None:
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    outer = QtWidgets.QVBoxLayout()
    outer.addWidget(area)
    widget = QtWidgets.QWidget()
    widget.setLayout(layout)
    area.setWidget(widget)
    window.setLayout(outer)
    window.resize(area.size())
