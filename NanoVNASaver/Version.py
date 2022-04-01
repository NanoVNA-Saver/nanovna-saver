#  NanoVNASaver
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
import logging
import re

logger = logging.getLogger(__name__)


class Version:
    RXP = re.compile(r"""^
        \D*
        (?P<major>\d+)\.
        (?P<minor>\d+)\.?
        (?P<revision>\d+)?
        (?P<note>.*)
        $""", re.VERBOSE)

    def __init__(self, vstring: str = "0.0.0"):
        self.data = {
            "major": 0,
            "minor": 0,
            "revision": 0,
            "note": "",
        }
        try:
            self.data = Version.RXP.search(vstring).groupdict()
            for name in ("major", "minor", "revision"):
                self.data[name] = int(self.data[name])
        except TypeError:
            self.data["revision"] = 0
        except AttributeError:
            logger.error("Unable to parse version: %s", vstring)

    def __gt__(self, other: "Version") -> bool:
        l, r = self.data, other.data
        for name in ("major", "minor", "revision"):
            if l[name] > r[name]:
                return True
            if l[name] < r[name]:
                return False
        return False

    def __lt__(self, other: "Version") -> bool:
        return other.__gt__(self)

    def __ge__(self, other: "Version") -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __le__(self, other: "Version") -> bool:
        return other.__gt__(self) or self.__eq__(other)

    def __eq__(self, other: "Version") -> bool:
        return self.data == other.data

    def __str__(self) -> str:
        return (f'{self.data["major"]}.{self.data["minor"]}'
                f'.{self.data["revision"]}{self.data["note"]}')

    @property
    def major(self) -> int:
        return self.data["major"]

    @property
    def minor(self) -> int:
        return self.data["minor"]

    @property
    def revision(self) -> int:
        return self.data["revision"]

    @property
    def note(self) -> str:
        return self.data["note"]
