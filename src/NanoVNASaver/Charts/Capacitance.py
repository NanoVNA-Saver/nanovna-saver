#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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

from NanoVNASaver.Charts.Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class CapacitanceChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.minDisplayValue = 0
        self.maxDisplayValue = 100
        self.name_unit = "F"
        self.value_function = lambda x: x.capacitiveEquivalent()
