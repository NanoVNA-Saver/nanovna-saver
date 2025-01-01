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

# Import targets to be tested
from NanoVNASaver.utils import Version


class TestCases:

    @staticmethod
    def test_str() -> None:
        assert str(Version(1, 0, 0, "")) == "1.0.0"
        assert str(Version(1, 2, 0, "")) == "1.2.0"
        assert str(Version(1, 2, 3, "")) == "1.2.3"
        assert str(Version(1, 2, 3, "-test")) == "1.2.3-test"

    @staticmethod
    def test_repr() -> None:
        ver = Version(1, 2, 3, "-test")

        assert f"{ver}" == "1.2.3-test"

    @staticmethod
    def test_parse_normal_case() -> None:
        # At least major and minot components must be specified
        assert Version.parse("v1.2") == Version(1, 2, 0, "")
        assert Version.parse("v1.2.3") == Version(1, 2, 3, "")
        assert Version.parse("v1.2.3-test") == Version(1, 2, 3, "-test")

        # At least major and minot components must be specified
        assert Version.parse("1.2") == Version(1, 2, 0, "")
        assert Version.parse("1.2.3") == Version(1, 2, 3, "")
        assert Version.parse("1.2.3-test") == Version(1, 2, 3, "-test")

    @staticmethod
    def test_parse_invalid_values() -> None:
        assert Version.parse("asdasd") == Version(0, 0, 0, "")
        assert Version.parse("1.2.invalid") == Version(1, 2, 0, "invalid")

        # At least major and minot components must be specified
        assert Version.parse("v1") == Version(0, 0, 0, "")
        assert Version.parse("1") == Version(0, 0, 0, "")

    @staticmethod
    def test_build_normal_case() -> None:

        assert Version.build(1, 2) == Version(1, 2, 0, "")
        assert Version.build(1, 2, 3) == Version(1, 2, 3, "")
        assert Version.build(1, 2, 3, "test") == Version(1, 2, 3, "test")

    @staticmethod
    def test_comparation() -> None:
        assert Version(1, 2, 3, "test") > Version(1, 2, 3, "")
        assert Version(1, 2, 3, "test") < Version(1, 2, 4, "")

        assert Version(1, 2, 3, "test") <= Version(1, 2, 4, "u")

        assert Version(0, 0, 0, "0") != Version(0, 0, 0, "-rc")
