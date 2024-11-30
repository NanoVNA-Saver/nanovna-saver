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
import logging
import os
import unittest

from NanoVNASaver.RFTools import Datapoint

# Import targets to be tested
from NanoVNASaver.Touchstone import Options, Touchstone


class TestTouchstoneOptions(unittest.TestCase):
    def setUp(self):
        self.opts = Options()

    def test_defaults(self):
        self.assertEqual(self.opts.unit, "ghz")
        self.assertEqual(self.opts.parameter, "s")
        self.assertEqual(self.opts.format, "ma")
        self.assertEqual(self.opts.resistance, 50)
        self.assertEqual(self.opts.factor, 1000000000)
        self.assertEqual(str(self.opts), "# GHZ S MA R 50")

    def test_parse(self):
        self.assertRaisesRegex(
            TypeError, "Not an option line:", self.opts.parse, ""
        )
        self.assertRaisesRegex(
            TypeError, "Not an option line: !", self.opts.parse, "!"
        )
        self.assertRaisesRegex(
            TypeError,
            "Illegal option line: # ILLEGAL",
            self.opts.parse,
            "# ILLEGAL",
        )
        self.assertRaisesRegex(
            TypeError,
            "Illegal option line: # GHz mhz",
            self.opts.parse,
            "# GHz mhz",
        )
        self.opts.parse("# khz")
        self.assertEqual(str(self.opts), "# KHZ S MA R 50")
        self.assertEqual(self.opts.factor, 1000)
        self.opts.parse("# r 123 ri hz y")
        self.assertEqual(str(self.opts), "# HZ Y RI R 123")
        self.assertEqual(self.opts.factor, 1)


class TestTouchstoneTouchstone(unittest.TestCase):

    def test_load(self):
        ts = Touchstone("./tests/data/valid.s1p")
        ts.load()
        self.assertEqual(str(ts.opts), "# HZ S RI R 50")
        self.assertEqual(len(ts.s11), 1010)
        self.assertEqual(len(ts.s21), 0)
        self.assertEqual(ts.r, 50)

        ts = Touchstone("./tests/data/valid.s2p")
        ts.load()
        ts.gen_interpolation()
        self.assertEqual(str(ts.opts), "# HZ S RI R 50")
        self.assertEqual(len(ts.s11), 1020)
        self.assertEqual(len(ts.s21), 1020)
        self.assertEqual(len(ts.s12), 1020)
        self.assertEqual(len(ts.s22), 1020)
        self.assertIn("! Vector Network Analyzer VNA R2", ts.comments)
        self.assertEqual(ts.min_freq(), 500000)
        self.assertEqual(ts.max_freq(), 900000000)
        self.assertEqual(
            ts.s_freq("11", 1), Datapoint(1, -3.33238e-001, 1.80018e-004)
        )
        self.assertEqual(
            ts.s_freq("11", 750000),
            Datapoint(750000, -0.3331754099382822, 0.00032433255669243524),
        )

        ts = Touchstone("./tests/data/ma.s2p")
        ts.load()
        self.assertEqual(str(ts.opts), "# MHZ S MA R 50")

        ts = Touchstone("./tests/data/db.s2p")
        ts.load()
        self.assertEqual(str(ts.opts), "# HZ S DB R 50")

        ts = Touchstone("./tests/data/broken_pair.s2p")
        with self.assertLogs(level=logging.ERROR) as cm:
            ts.load()
        self.assertRegex(cm.output[0], "Data values aren't pairs")

        ts = Touchstone("./tests/data/missing_pair.s2p")
        with self.assertLogs(level=logging.ERROR) as cm:
            ts.load()
        self.assertRegex(cm.output[0], "Inconsistent number")

        ts = Touchstone("./tests/data/nonexistent.s2p")
        with self.assertLogs(level=logging.ERROR) as cm:
            ts.load()
        self.assertRegex(cm.output[0], "No such file or directory")

    def test_swap(self):
        ts = Touchstone("./tests/data/valid.s2p")
        ts.load()
        s11, s21, s12, s22 = ts.sdata
        ts.swap()
        s11_, s21_, s12_, s22_ = ts.sdata
        self.assertEqual([s11_, s21_, s12_, s22_], [s22, s12, s21, s11])

    def test_db_conversation(self):
        ts_db = Touchstone("./tests/data/attenuator-0643_DB.s2p")
        ts_db.load()
        ts_ri = Touchstone("./tests/data/attenuator-0643_RI.s2p")
        ts_ri.load()
        ts_ma = Touchstone("./tests/data/attenuator-0643_MA.s2p")
        ts_ma.load()
        self.assertEqual(len(ts_db.s11), len(ts_ri.s11))
        for dps_db, dps_ri in zip(ts_db.s11, ts_ri.s11, strict=False):
            self.assertAlmostEqual(dps_db.z, dps_ri.z, places=5)

        self.assertEqual(len(ts_db.s11), len(ts_ma.s11))
        for dps_db, dps_ma in zip(ts_db.s11, ts_ma.s11, strict=False):
            self.assertAlmostEqual(dps_db.z, dps_ma.z, places=5)

    def test_load_scikit(self):
        ts = Touchstone("./tests/data/scikit_unordered.s2p")
        with self.assertLogs(level=logging.WARNING) as cm:
            ts.load()
        self.assertEqual(
            cm.output,
            [
                "WARNING:NanoVNASaver.Touchstone:"
                "Non integer resistance value: 50.0",
                "WARNING:NanoVNASaver.Touchstone:Comment after header:"
                " !freq ReS11 ImS11 ReS21 ImS21 ReS12 ImS12 ReS22 ImS22",
                "WARNING:NanoVNASaver.Touchstone:Frequency not ascending:"
                " 15000000.0 0.849810063 -0.4147357 -0.000306106 0.0041482"
                " 0.0 0.0 0.0 0.0",
                "WARNING:NanoVNASaver.Touchstone:Reordering data",
            ],
        )
        self.assertEqual(str(ts.opts), "# HZ S RI R 50")
        self.assertEqual(len(ts.s11), 101)
        self.assertIn(
            "!freq ReS11 ImS11 ReS21 ImS21 ReS12 ImS12 ReS22 ImS22", ts.comments
        )

    def test_setter(self):
        ts = Touchstone("")
        dp_list = [Datapoint(1, 0.0, 0.0), Datapoint(3, 1.0, 1.0)]
        ts.s11 = dp_list[:]
        ts.s21 = dp_list[:]
        ts.s12 = dp_list[:]
        ts.s22 = dp_list[:]
        self.assertEqual(ts.s11, dp_list)
        self.assertEqual(ts.s21, dp_list)
        self.assertEqual(ts.s12, dp_list)
        self.assertEqual(ts.s22, dp_list)
        self.assertEqual(ts.min_freq(), 1)
        self.assertEqual(ts.max_freq(), 3)
        ts.gen_interpolation()
        self.assertEqual(ts.s_freq("11", 2), Datapoint(2, 0.5, 0.5))

    def test_save(self):
        ts = Touchstone("./tests/data/valid.s2p")
        self.assertEqual(ts.saves(), "# HZ S RI R 50\n")
        ts.load()
        lines = ts.saves().splitlines()
        self.assertEqual(len(lines), 1021)
        self.assertEqual(lines[0], "# HZ S RI R 50")
        self.assertEqual(lines[1], "500000 -0.333238 0.000180018")
        self.assertEqual(lines[-1], "900000000 -0.127646 0.31969")
        lines = ts.saves(4).splitlines()
        self.assertEqual(len(lines), 1021)
        self.assertEqual(lines[0], "# HZ S RI R 50")
        self.assertEqual(
            lines[1],
            "500000 -0.333238 0.000180018 0.67478 -8.1951e-07"
            " 0.67529 -8.20129e-07 -0.333238 0.000308078",
        )
        self.assertEqual(
            lines[-1],
            "900000000 -0.127646 0.31969 0.596287 -0.503453"
            " 0.599076 -0.50197 -0.122713 0.326965",
        )
        ts.filename = "./tests/data/output.s2p"
        ts.save(4)
        os.remove(ts.filename)
        ts.filename = ""
        self.assertRaises(FileNotFoundError, ts.save)

        ts.s11[0] = Datapoint(100, 0.1, 0.1)
        self.assertRaisesRegex(
            LookupError, "Frequencies of sdata not correlated", ts.saves, 4
        )
