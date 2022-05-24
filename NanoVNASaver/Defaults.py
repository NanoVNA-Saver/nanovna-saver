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
import json

from PyQt5.QtCore import QSettings


logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
@DC.dataclass
class GUI:
    window_height: int = 950
    window_width: int = 1433
    font_size: int = 8
    dark_mode: bool = False
    # TODO: implement QByteArray
    splitter_sizes: bytearray = DC.field(default_factory=bytearray)
    markers_hidden: bool = False


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


@DC.dataclass
class CFG:
    gui: object = GUI()
    chart: object = Chart()


cfg = CFG()

def restore(settings: 'AppSettings') -> CFG:
    result = CFG()
    for field in DC.fields(result):
        value = settings.restore_dataclass(field.name.upper(),
                                           getattr(result, field.name))
        setattr(result, field.name, value)
    logger.debug("restored\n(\n%s\n)", result)
    return result


def store(settings: 'AppSettings', data: CFG) -> None:
    logger.debug("storing\n(\n%s\n)", data)
    assert isinstance(data, CFG)
    for field in DC.fields(data):
        data_class  = getattr(data, field.name)
        assert DC.is_dataclass(data_class)
        settings.store_dataclass(field.name.upper(), data_class)


class AppSettings(QSettings):
    def store_dataclass(self, name: str, data: object) -> None:
        assert DC.is_dataclass(data)
        self.beginGroup(name)
        for field in DC.fields(data):
            value = getattr(data, field.name)
            try:
                assert isinstance(value, field.type)
            except AssertionError:
                logger.error("%s: %s is not a %s", name, field.name,
                               field.type)
                continue
            if field.type not in (int, float, str, bool):
                try:
                    value = json.dumps(value)
                except TypeError:
                    value = field.type(value).hex()
            self.setValue(field.name, value)
        self.endGroup()

    def restore_dataclass(self, name: str, data: object) -> object:
        assert DC.is_dataclass(data)

        result = DC.replace(data)
        self.beginGroup(name)
        for field in DC.fields(data):
            value = None
            if field.type in (int, float, str, bool):
                value = self.value(field.name,
                                   type=field.type,
                                   defaultValue=field.default)
            else:
                default = getattr(data, field.name)
                try:
                    value = json.loads(
                        self.value(field.name, type=str,
                                   defaultValue=json.dumps(default)))
                except TypeError:
                    value = self.value(field.name)
                    value = bytes.fromhex(value) if value is str else default
            setattr(result, field.name, field.type(value))
        self.endGroup()

        return result
