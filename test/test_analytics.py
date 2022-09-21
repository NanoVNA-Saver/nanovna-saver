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
import math
import unittest

import numpy as np
# Import targets to be tested
import NanoVNASaver.AnalyticTools as at

SINEWAVE = [math.sin(x/45 * math.pi) for x in range(360)]


class AnalyticsTools(unittest.TestCase):

    def test_zero_crossings(self):
        self.assertEqual(at.zero_crossings(SINEWAVE),
                         [45, 90, 135, 180, 225, 270, 315])
        self.assertEqual(at.zero_crossings([]), [])

    def test_maxima(self):
        self.assertEqual(at.maxima(SINEWAVE), [112, 202, 292])
        self.assertEqual(at.maxima(SINEWAVE, 0.9999), [])
        self.assertEqual(at.maxima(-np.array(SINEWAVE)), [67, 157, 247])

    def test_minima(self):
        self.assertEqual(at.minima(SINEWAVE), [67, 157, 247])
        self.assertEqual(at.minima(SINEWAVE, -0.9999), [])
        self.assertEqual(at.minima(-np.array(SINEWAVE)), [112, 202, 292])

    def test_take_from_idx(self):
        self.assertEqual(
            at.take_from_idx(SINEWAVE, 109, lambda i: i[1] > 0.9),
            [107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118])

    def test_center_from_idx(self):
        self.assertEqual(at.center_from_idx(SINEWAVE, 200), 22)
        self.assertEqual(at.center_from_idx(SINEWAVE, 200, .5), 202)

    def test_cut_off_left(self):
        self.assertEqual(at.cut_off_left(SINEWAVE, 210, 1, 0.4), 189)

    def test_cut_off_right(self):
        self.assertEqual(at.cut_off_right(SINEWAVE, 210, 1, 0.4), 216)

    def test_dip_cut_offs(self):
        self.assertEqual(at.dip_cut_offs(SINEWAVE, .8, .9), (47, 358))
        self.assertEqual(at.dip_cut_offs(SINEWAVE[:90], .8, .9), (47, 88))
