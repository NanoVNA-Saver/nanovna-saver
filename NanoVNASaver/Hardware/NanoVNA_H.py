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

from NanoVNASaver.Hardware.NanoVNA import NanoVNA

logger = logging.getLogger(__name__)


class NanoVNA_H(NanoVNA):
    name = "NanoVNA-H"

    def read_features(self):
        logger.debug("read_features")
        if self.readFirmware().find("sweep_points 201") > 0:
            logger.info("VNA has 201 datapoints capability")
            self.valid_datapoints = (201, 101)
            self.datapoints = 201
        self.features.add("Screenshot")