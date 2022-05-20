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
from cgitb import reset
import json
import dataclasses as DC
from operator import ge
from tkinter import N
from tkinter.messagebox import NO
from webbrowser import get

from PyQt5.QtCore import QSettings


@DC.dataclass
class ChartMarkerConfig:
    draw_label: bool = False
    fill: bool = False
    at_tip: bool = False
    size: int = 8


class AppSettings(QSettings):
    def store_dataclass(self, name: str, data: object) -> None:
        assert DC.is_dataclass(data)
        self.beginGroup(name)
        for field in DC.fields(data):
            value = getattr(data, field.name)
            if field.type not in (int, float, str, bool):
                value = json.dumps(value)
            self.setValue(field.name, value)
        self.endGroup()
    
    def restore_dataclass(self, name: str, data: object) -> object:
        assert DC.is_dataclass(data)

        result = DC.replace(data)
        self.beginGroup(name)
        for field in DC.fields(data):
            value = self.value(field.name)
            value = getattr(data, field.name) if value is None else value
            if field.type in (int, float, str, bool):
                value = field.type(value)
            else:
                value = json.loads(value)
            setattr(result, field.name, value)
        self.endGroup()
        
        return result
