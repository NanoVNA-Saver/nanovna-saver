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

# Import targets to be tested
from NanoVNASaver.Version import Version


class TestCases(unittest.TestCase):

    def test_version(self):
        ver = Version("v1.2.3-test")
        self.assertEqual(str(ver), "1.2.3-test")
        self.assertLessEqual(ver, Version("1.2.4"))
        self.assertFalse(ver > Version("1.2.4"))
        self.assertFalse(ver > Version("1.2.3-u"))
        self.assertTrue(Version("1.2.4") >= ver)
        self.assertTrue(ver < Version("1.2.4"))
        self.assertFalse(Version("0.0.0") == Version("0.0.0-rc"))
        self.assertEqual(ver.major, 1)
        self.assertEqual(ver.minor, 2)
        self.assertEqual(ver.revision, 3)
        self.assertEqual(ver.note, "-test")
        Version("asdasd")
        Version("1.2.invalid")
