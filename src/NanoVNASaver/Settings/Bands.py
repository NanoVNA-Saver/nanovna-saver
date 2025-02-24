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
import contextlib
import logging
from typing import Optional

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QModelIndex, Qt

_DEFAULT_BANDS = (
    (
        "2200 m;135700;137800",
        "630 m;472000;479000",
        "160 m;1800000;2000000",
        "80 m;3500000;3800000",
        "60 m;5250000;5450000",
        "40 m;7000000;7200000",
        "30 m;10100000;10150000",
        "20 m;14000000;14350000",
        "17 m;18068000;18168000",
        "15 m;21000000;21450000",
        "12 m;24890000;24990000",
        "10 m;28000000;29700000",
        "6 m;50000000;52000000",
        "4 m;69887500;70512500",
        "2 m;144000000;146000000",
        "70 cm;430000000;440000000",
        "23 cm;1240000000;1300000000",
        "13 cm;2300000000;2450000000",
        "5 cm;5650000000;5850000000",
    ),
    (
        "2200 m;135700;137800",
        "630 m;472000;479000",
        "160 m;1800000;2000000",
        "80 m;3500000;4000000",
        "60 m;5250000;5450000",
        "40 m;7000000;7300000",
        "30 m;10100000;10150000",
        "20 m;14000000;14350000",
        "17 m;18068000;18168000",
        "15 m;21000000;21450000",
        "12 m;24890000;24990000",
        "10 m;28000000;29700000",
        "6 m;50000000;54000000",
        "4 m;69887500;70512500",
        "2 m;144000000;148000000",
        "1.25 m;222000000;225000000",
        "70 cm;420000000;450000000",
        "33 cm;902000000;928000000",
        "23 cm;1240000000;1300000000",
        "13 cm;2300000000;2450000000",
        "9 cm;3300000000;3500000000",
        "5 cm;5650000000;5925000000",
    ),
    (
        "2200 m;135700;137800",
        "630 m;472000;479000",
        "160 m;1800000;2000000",
        "80 m;3500000;3900000",
        "60 m;5250000;5450000",
        "40 m;7000000;7200000",
        "30 m;10100000;10150000",
        "20 m;14000000;14350000",
        "17 m;18068000;18168000",
        "15 m;21000000;21450000",
        "12 m;24890000;24990000",
        "10 m;28000000;29700000",
        "6 m;50000000;54000000",
        "4 m;69887500;70512500",
        "2 m;144000000;148000000",
        "70 cm;430000000;440000000",
        "23 cm;1240000000;1300000000",
        "13 cm;2300000000;2450000000",
        "9 cm;3300000000;3500000000",
        "5 cm;5650000000;5850000000",
    ),
)


_HEADER_DATA = ("Band", "Start (Hz)", "End (Hz)")

logger = logging.getLogger(__name__)


class BandsModel(QtCore.QAbstractTableModel):
    color = QtGui.QColor(128, 128, 128, 48)

    # These bands correspond broadly to the Danish Amateur Radio allocation
    def __init__(self):
        super().__init__()
        self.settings = QtCore.QSettings(
            QtCore.QSettings.Format.IniFormat,
            QtCore.QSettings.Scope.UserScope,
            "NanoVNASaver",
            "Bands",
        )
        # self.settings.setIniCodec("UTF-8")

        self.enabled = self.settings.value("ShowBands", False, bool)
        self.bands = [
            band.split(";")
            for band in self.settings.value("bands", _DEFAULT_BANDS[0])
        ]

    def saveSettings(self):
        self.settings.setValue(
            "bands",
            [f"{name};{start};{end}" for name, start, end in self.bands],
        )
        self.settings.sync()

    def resetBands(self, region_index=1):
        self.bands = [
            band.split(";") for band in _DEFAULT_BANDS[region_index - 1]
        ]
        self.layoutChanged.emit()
        self.saveSettings()

    def columnCount(self, _) -> int:
        return 3

    def rowCount(self, _) -> int:
        return len(self.bands)

    def data(
        self, index: QModelIndex, role: int = -1
    ) -> str | Qt.AlignmentFlag | None:
        row: int = index.row()
        col: int = index.column()
        match role:
            case Qt.ItemDataRole.DisplayRole | Qt.ItemDataRole.EditRole:
                return self.bands[row][col]
            case Qt.ItemDataRole.TextAlignmentRole:
                if col == 0:
                    return Qt.AlignmentFlag.AlignCenter
                return (
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            case _:
                logger.debug("No data for role(%s)", role)
                return None

    def setData(self, index: QModelIndex, value: str, role: int = -1) -> bool:
        row = index.row()
        col = index.column()
        if role != QtCore.Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        name, start, end = self.bands[row]
        match col:
            case 1:
                name = value
            case 2:
                start = value
            case 3:
                end = value
        self.bands[index.row()] = (name, start, end)
        self.dataChanged.emit(index, index)
        self.saveSettings()
        return True

    def index(
        self, row: int, column: int, _: Optional[QModelIndex] = None
    ) -> QModelIndex:
        return self.createIndex(row, column)

    def addRow(self):
        self.bands.append(("New", 0, 0))
        self.dataChanged.emit(
            self.index(len(self.bands), 0), self.index(len(self.bands), 2)
        )
        self.layoutChanged.emit()

    def removeRow(self, row: int, _: Optional[QModelIndex] = None) -> bool:
        self.bands.remove(self.bands[row])
        self.layoutChanged.emit()
        self.saveSettings()
        return True

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = -1
    ):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            with contextlib.suppress(IndexError):
                return _HEADER_DATA[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid():
            return Qt.ItemFlag(
                Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
        return super().flags(index)

    def setColor(self, color):
        self.color = color
