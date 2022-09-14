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
import unittest
from dataclasses import dataclass, field

import NanoVNASaver.Defaults as CFG


@dataclass
class TConfig:
    my_int: int = 3
    my_float: float = 3.14
    my_str: str = "Hello World"
    my_bool: bool = True
    my_list: list = field(default_factory=lambda: [1, 2, 3])
    my_bytearray: bytearray = field(default_factory=lambda: bytearray((1, 2, 3)))


class TestCases(unittest.TestCase):

    def setUp(self) -> None:
        self.settings_1 = CFG.AppSettings(
            CFG.QSettings.IniFormat,
            CFG.QSettings.UserScope,
            "NanoVNASaver", "Test_1")
        self.settings_2 = CFG.AppSettings(
            CFG.QSettings.IniFormat,
            CFG.QSettings.UserScope,
            "NanoVNASaver", "Test_2")
        self.config_1 = TConfig()
        self.config_2 = TConfig(
            my_int=4,
            my_float=3.0,
            my_str="Goodbye World",
            my_bool=False,
            my_list=[4, 5, 6])

    def test_store_dataclass(self):
        self.settings_1.store_dataclass("Section1", self.config_1)
        self.settings_1.store_dataclass("Section2", self.config_2)
        illegal_config = TConfig(
            my_int=4, my_float=3.0, my_str="Goodbye World",
            my_bool="False", my_list=(4, 5, 6))
        with self.assertRaises(TypeError):
            self.settings_1.store_dataclass("SectionX", illegal_config)

    def test_restore_dataclass(self):
        tc_1 = self.settings_1.restore_dataclass("Section1", self.config_1)
        tc_2 = self.settings_1.restore_dataclass("Section2", self.config_2)
        self.assertNotEqual(tc_1, tc_2)
        self.assertEqual(tc_1, self.config_1)
        self.assertEqual(tc_2, self.config_2)
        self.assertEqual(tc_2.my_int, 4)
        self.assertEqual(tc_2.my_float, 3.0)
        self.assertEqual(tc_2.my_str, "Goodbye World")
        self.assertEqual(tc_2.my_bool, False)
        self.assertEqual(tc_2.my_list, [4, 5, 6])
        self.assertIsInstance(tc_2.my_int, int)
        self.assertIsInstance(tc_2.my_float, float)

    def test_restore_empty(self):
        tc_3 = self.settings_1.restore_dataclass("Section3", TConfig())
        self.assertEqual(tc_3, TConfig())

    def test_store(self):
        tc_1 = CFG.CFG()
        tc_1.gui.dark_mode = not tc_1.gui.dark_mode
        CFG.store(self.settings_2, tc_1)
        tc_2 = CFG.restore(self.settings_2)
        print(f"\n{tc_1}\n{tc_2}\n")
        self.assertEqual(tc_1, tc_2)
        self.assertNotEqual(tc_2.gui, CFG.GUI())
