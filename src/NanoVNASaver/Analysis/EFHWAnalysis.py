#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020 Rune B. Broberg
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
import csv
import logging

from PyQt6 import QtWidgets

import NanoVNASaver.AnalyticTools as At
from NanoVNASaver.Analysis.ResonanceAnalysis import (
    ResonanceAnalysis,
    format_resistence_neg,
)
from NanoVNASaver.Formatting import (
    format_complex_imp,
    format_frequency,
    format_frequency_short,
)

logger = logging.getLogger(__name__)


class EFHWAnalysis(ResonanceAnalysis):
    """
    find only resonance when HI impedance
    """

    def __init__(self, app):
        super().__init__(app)
        self.old_data = []

    def do_resonance_analysis(self):
        s11 = self.app.data.s11
        maximums = sorted(
            At.maxima([d.impedance().real for d in s11], threshold=500)
        )
        extended_data = {}
        logger.info("TO DO: find near data")
        for lowest in self.crossings:
            my_data = self._get_data(lowest)
            if lowest in extended_data:
                extended_data[lowest].update(my_data)
            else:
                extended_data[lowest] = my_data
        logger.debug("maximumx %s of type %s", maximums, type(maximums))
        for m in maximums:
            logger.debug("m %s of type %s", m, type(m))
            my_data = self._get_data(m)
            if m in extended_data:
                extended_data[m].update(my_data)
            else:
                extended_data[m] = my_data
        fields = [
            ("freq", format_frequency_short),
            ("r", format_resistence_neg),
            ("lambda", lambda x: round(x, 2)),
        ]

        if self.old_data:
            diff = self.compare(self.old_data[-1], extended_data, fields=fields)
        else:
            diff = self.compare({}, extended_data, fields=fields)
        self.old_data.append(extended_data)
        for i, idx in enumerate(sorted(extended_data.keys())):
            self.layout.addRow(
                f"{format_frequency_short(s11[idx].freq)}",
                QtWidgets.QLabel(
                    f" ({diff[i]['freq']})"
                    f" {format_complex_imp(s11[idx].impedance())}"
                    f" ({diff[i]['r']}) {diff[i]['lambda']} m"
                ),
            )

        if self.filename and extended_data:
            with open(
                self.filename, "w", newline="", encoding="utf-8"
            ) as csvfile:
                fieldnames = extended_data[
                    sorted(extended_data.keys())[0]
                ].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for idx in sorted(extended_data.keys()):
                    writer.writerow(extended_data[idx])

    def compare(self, old, new, fields=None):
        """
        Compare data to help changes

        NB
        must be same sweep
        ( same index must be same frequence )
        :param old:
        :param new:
        """
        fields = fields or [
            ("freq", str),
        ]

        def no_compare():
            return {k: "-" for k, _ in fields}

        old_idx = sorted(old.keys())
        # 'odict_keys' object is not subscriptable
        new_idx = sorted(new.keys())
        diff = {}
        i_max = min(len(old_idx), len(new_idx))
        i_tot = max(len(old_idx), len(new_idx))

        if i_max != i_tot:
            logger.warning(
                "resonances changed from %s to %s", len(old_idx), len(new_idx)
            )

        split = 0
        max_delta_f = 1_000_000
        for i, k in enumerate(new_idx):
            if len(old_idx) <= i + split:
                diff[i] = no_compare()
                continue

            logger.info("Resonance %s at %s", i, new[k]["freq"])

            delta_f = new[k]["freq"] - old[old_idx[i + split]]["freq"]
            if abs(delta_f) < max_delta_f:
                logger.debug("can compare")
                diff[i] = {
                    desc: fnc(new[k][desc] - old[old_idx[i + split]][desc])
                    for desc, fnc in fields
                }
                logger.debug("Deltas %s", diff[i])
                continue

            logger.debug(
                "can't compare, %s is too much ", format_frequency(delta_f)
            )

            if delta_f > 0:
                logger.debug("possible missing band, ")
                if len(old_idx) > (i + split + 1):
                    if (
                        abs(
                            new[k]["freq"] - old[old_idx[i + split + 1]]["freq"]
                        )
                        < max_delta_f
                    ):
                        logger.debug("new is missing band, compare next ")
                        split += 1
                        # FIXME: manage 2 or more band missing ?!?
                        continue
                    logger.debug("new band, non compare ")
                    diff[i] = no_compare()
                continue

            logger.debug("new band, non compare ")
            diff[i] = no_compare()
            split -= 1

        for i in range(i_max, i_tot):
            # add missing in old ... if any
            diff[i] = no_compare()
        return diff
