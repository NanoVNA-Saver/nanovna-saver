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
from NanoVNASaver.SweepWorker import truncate

DATA = [
    [
        (-0.81474496 + 0.639054208j),
        (-0.809070272 + 0.645022336j),
        (-0.80785184 + 0.646469184j),
    ],
    [
        (-0.81436032 + 0.638994432j),
        (-0.809495232 + 0.645203008j),
        (-0.808114176 + 0.646456512j),
    ],
    [
        (-0.814578048 + 0.638436288j),
        (-0.809082496 + 0.644978368j),
        (-0.807828096 + 0.646324352j),
    ],
    [
        (-0.814171712 + 0.639012992j),
        (-0.80954272 + 0.645197312j),
        (-0.807910976 + 0.646379968j),
    ],
]

DATA_TRUNCATED = [
    [
        (-0.81436032 + 0.638994432j),
        (-0.809495232 + 0.645203008j),
        (-0.807910976 + 0.646379968j),
    ],
    [
        (-0.814171712 + 0.639012992j),
        (-0.809070272 + 0.645022336j),
        (-0.80785184 + 0.646469184j),
    ],
    [
        (-0.81474496 + 0.639054208j),
        (-0.809082496 + 0.644978368j),
        (-0.807828096 + 0.646324352j),
    ],
]


class TestSweepWorkerTruncate(unittest.TestCase):

    def test_truncate(self):
        x = truncate(DATA, 1)
        self.assertEqual(x, DATA_TRUNCATED)
