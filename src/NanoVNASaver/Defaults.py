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

import logging
from ast import literal_eval
from dataclasses import dataclass, field, fields, is_dataclass, replace

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtGui import QColor, QColorConstants

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
@dataclass
class GuiConfig:
    window_height: int = 950
    window_width: int = 1433
    font_size: int = 8
    custom_colors: bool = False
    dark_mode: bool = False
    splitter_sizes: QByteArray = field(default_factory=QByteArray)
    markers_hidden: bool = False


@dataclass
class ChartsSelectedConfig:
    chart_00: str = "S11 Smith Chart"
    chart_01: str = "S11 Return Loss"
    chart_02: str = "None"
    chart_10: str = "S21 Polar Plot"
    chart_11: str = "S21 Gain"
    chart_12: str = "None"


@dataclass
class ChartConfig:
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
    vswr_lines: list = field(default_factory=list)


@dataclass
class ChartColorsConfig:  # pylint: disable=too-many-instance-attributes
    background: QColor = field(
        default_factory=lambda: QColor(QColorConstants.White)
    )
    foreground: QColor = field(
        default_factory=lambda: QColor(QColorConstants.LightGray)
    )
    reference: QColor = field(default_factory=lambda: QColor(0, 0, 255, 64))
    reference_secondary: QColor = field(
        default_factory=lambda: QColor(0, 0, 192, 48)
    )
    sweep: QColor = field(
        default_factory=lambda: QColor(QColorConstants.DarkYellow)
    )
    sweep_secondary: QColor = field(
        default_factory=lambda: QColor(QColorConstants.DarkMagenta)
    )
    swr: QColor = field(default_factory=lambda: QColor(255, 0, 0, 128))
    text: QColor = field(
        default_factory=lambda: QColor(QColorConstants.Black)
    )
    bands: QColor = field(default_factory=lambda: QColor(128, 128, 128, 48))


@dataclass
class MarkersConfig:
    active_labels: list = field(
        default_factory=lambda: [
            "actualfreq",
            "impedance",
            "serr",
            "serl",
            "serc",
            "parr",
            "parlc",
            "vswr",
            "returnloss",
            "s11q",
            "s11phase",
            "s21gain",
            "s21phase",
        ]
    )
    colored_names: bool = True
    color_0: QColor = field(
        default_factory=lambda: QColor(QColorConstants.DarkGray)
    )
    color_1: QColor = field(default_factory=lambda: QColor(255, 0, 0))
    color_2: QColor = field(default_factory=lambda: QColor(0, 255, 0))
    color_3: QColor = field(default_factory=lambda: QColor(0, 0, 255))
    color_4: QColor = field(default_factory=lambda: QColor(0, 255, 255))
    color_5: QColor = field(default_factory=lambda: QColor(255, 0, 255))
    color_6: QColor = field(default_factory=lambda: QColor(255, 255, 0))
    color_7: QColor = field(
        default_factory=lambda: QColor(QColorConstants.LightGray)
    )


@dataclass
class AppConfig:
    gui: GuiConfig = field(default_factory=GuiConfig)
    charts_selected: ChartsSelectedConfig = field(default_factory=ChartsSelectedConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    chart_colors: ChartColorsConfig = field(default_factory=ChartColorsConfig)
    markers: MarkersConfig = field(default_factory=MarkersConfig)


app_config = AppConfig()


def restore_config(settings: "AppSettings") -> AppConfig:
    result = AppConfig()
    for field_it in fields(result):
        value = settings.restore_dataclass(
            field_it.name.upper(), getattr(result, field_it.name)
        )
        setattr(result, field_it.name, value)
    logger.debug("restored\n(\n%s\n)", result)
    return result


def store_config(settings: "AppSettings", data: AppConfig | None = None) -> None:
    data = data or app_config
    logger.debug("storing\n(\n%s\n)", data)
    assert isinstance(data, AppConfig)
    for field_it in fields(data):
        data_class = getattr(data, field_it.name)
        assert is_dataclass(data_class)
        settings.store_dataclass(field_it.name.upper(), data_class)


def _from_type(data) -> str:
    type_map = {
        bytearray: bytearray.hex,
        QColor: QColor.getRgb,
        QByteArray: QByteArray.toHex,
    }
    return (
        f"{type_map[type(data)](data)}" if type(data) in type_map else f"{data}"
    )


def _to_type(data: object, data_type: type) -> object:
    type_map = {
        bool: lambda x: x.lower() == "true",
        bytearray: bytearray.fromhex,
        list: literal_eval,
        tuple: literal_eval,
        QColor: lambda x: QColor.fromRgb(*literal_eval(x)),
        QByteArray: lambda x: QByteArray.fromHex(literal_eval(x)),
    }
    return (
        type_map[data_type](data) if data_type in type_map else data_type(data)
    )


# noinspection PyDataclass
class AppSettings(QSettings):
    def store_dataclass(self, name: str, data: object) -> None:
        assert is_dataclass(data)
        self.beginGroup(name)
        for field_it in fields(data):
            value = getattr(data, field_it.name)
            try:
                assert isinstance(value, field_it.type)
            except AssertionError as exc:
                logger.error(
                    "%s: %s of type %s is not a %s",
                    name,
                    field_it.name,
                    type(value),
                    field_it.type,
                )
                raise TypeError from exc
            self.setValue(field_it.name, _from_type(value))
        self.endGroup()

    def restore_dataclass(self, name: str, data: object) -> object:
        assert is_dataclass(data)

        result = replace(data)
        self.beginGroup(name)
        for field_it in fields(data):
            default = getattr(data, field_it.name)
            value = self.value(field_it.name, type=str, defaultValue="")
            if not value:
                setattr(result, field_it.name, default)
                continue
            try:
                setattr(result, field_it.name, _to_type(value, field_it.type))
            except TypeError:
                setattr(result, field_it.name, default)
        self.endGroup()
        return result
