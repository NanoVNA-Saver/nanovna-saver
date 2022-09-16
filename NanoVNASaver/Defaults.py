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

import dataclasses as DC
import logging
from ast import literal_eval

from PyQt5 import QtCore
from PyQt5.QtCore import QSettings, QByteArray
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
@DC.dataclass
class GUI:
    window_height: int = 950
    window_width: int = 1433
    font_size: int = 8
    custom_colors: bool = False
    dark_mode: bool = False
    splitter_sizes: QByteArray = DC.field(default_factory=QByteArray)
    markers_hidden: bool = False


@DC.dataclass
class ChartsSelected:
    chart_00: str = 'S11 Smith Chart'
    chart_01: str = 'S11 Return Loss'
    chart_02: str = 'None'
    chart_10: str = 'S21 Polar Plot'
    chart_11: str = 'S21 Gain'
    chart_12: str = 'None'


@DC.dataclass
class Chart:
    point_size: int = 2
    show_lines: bool = False
    line_thickness: int = 1
    marker_count: int = 3
    marker_label: bool = False
    marker_filled: bool = False
    marker_at_tip: bool = False
    marker_size: int = 8
    returnloss_is_positive: bool = False
    show_bands: bool = False
    vswr_lines: list = DC.field(default_factory=lambda: [])


@DC.dataclass
class ChartColors:  # pylint: disable=too-many-instance-attributes
    background: QColor = QColor(QtCore.Qt.white)
    foreground: QColor = QColor(QtCore.Qt.lightGray)
    reference: QColor = QColor(0, 0, 255, 64)
    reference_secondary: QColor = QColor(0, 0, 192, 48)
    sweep: QColor = QColor(QtCore.Qt.darkYellow)
    sweep_secondary: QColor = QColor(QtCore.Qt.darkMagenta)
    swr: QColor = QColor(255, 0, 0, 128)
    text: QColor = QColor(QtCore.Qt.black)
    bands: QColor = QColor(128, 128, 128, 48)


@DC.dataclass
class Markers:
    active_labels: list = DC.field(default_factory=lambda: [
        "actualfreq", "impedance", "serr", "serl", "serc", "parr", "parlc",
        "vswr", "returnloss", "s11q", "s11phase", "s21gain", "s21phase",
    ])
    colored_names: bool = True
    color_0: QColor = QColor(QtCore.Qt.darkGray)
    color_1: QColor = QColor(255, 0, 0)
    color_2: QColor = QColor(0, 255, 0)
    color_3: QColor = QColor(0, 0, 255)
    color_4: QColor = QColor(0, 255, 255)
    color_5: QColor = QColor(255, 0, 255)
    color_6: QColor = QColor(255, 255, 0)
    color_7: QColor = QColor(QtCore.Qt.lightGray)


@DC.dataclass
class CFG:
    gui: object = GUI()
    charts_selected: object = ChartsSelected()
    chart: object = Chart()
    chart_colors: object = ChartColors()
    markers: object = Markers()


cfg = CFG()


def restore(settings: 'AppSettings') -> CFG:
    result = CFG()
    for field in DC.fields(result):
        value = settings.restore_dataclass(field.name.upper(),
                                           getattr(result, field.name))
        setattr(result, field.name, value)
    logger.debug("restored\n(\n%s\n)", result)
    return result


def store(settings: 'AppSettings', data: CFG = None) -> None:
    data = data or cfg
    logger.debug("storing\n(\n%s\n)", data)
    assert isinstance(data, CFG)
    for field in DC.fields(data):
        data_class = getattr(data, field.name)
        assert DC.is_dataclass(data_class)
        settings.store_dataclass(field.name.upper(), data_class)


def from_type(data) -> str:
    type_map = {
        bytearray: lambda x: x.hex(),
        QColor: lambda x: x.getRgb(),
        QByteArray: lambda x: x.toHex()
    }
    return (f"{type_map[type(data)](data)}" if
            type(data) in type_map else
            f"{data}")


def to_type(data: object, data_type: type) -> object:
    type_map = {
        bool: lambda x: x.lower() == 'true',
        bytearray: bytearray.fromhex,
        list: literal_eval,
        tuple: literal_eval,
        QColor: lambda x: QColor.fromRgb(*literal_eval(x)),
        QByteArray: lambda x: QByteArray.fromHex(literal_eval(x))
    }
    return (type_map[data_type](data) if
            data_type in type_map else
            data_type(data))


# noinspection PyDataclass
class AppSettings(QSettings):
    def store_dataclass(self, name: str, data: object) -> None:
        assert DC.is_dataclass(data)
        self.beginGroup(name)
        for field in DC.fields(data):
            value = getattr(data, field.name)
            try:
                assert isinstance(value, field.type)
            except AssertionError as exc:
                logger.error("%s: %s of type %s is not a %s",
                             name, field.name, type(value), field.type)
                raise TypeError from exc
            self.setValue(field.name, from_type(value))
        self.endGroup()

    def restore_dataclass(self, name: str, data: object) -> object:
        assert DC.is_dataclass(data)

        result = DC.replace(data)
        self.beginGroup(name)
        for field in DC.fields(data):
            default = getattr(data, field.name)
            value = self.value(field.name, type=str, defaultValue="")
            if not value:
                setattr(result, field.name, default)
                continue
            try:
                setattr(result, field.name, to_type(value, field.type))
            except TypeError:
                setattr(result, field.name, default)
        self.endGroup()
        return result
