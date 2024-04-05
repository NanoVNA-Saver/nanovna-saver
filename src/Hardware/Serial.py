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
from threading import Lock

import serial

logger = logging.getLogger(__name__)


def drain_serial(serial_port: serial.Serial):
    """drain up to 64k outstanding data in the serial incoming buffer"""
    # logger.debug("Draining: %s", serial_port)
    timeout = serial_port.timeout
    serial_port.timeout = 0.05
    for _ in range(512):
        cnt = len(serial_port.read(128))
        if not cnt:
            serial_port.timeout = timeout
            return
    serial_port.timeout = timeout
    logger.warning("unable to drain all data")


class Interface(serial.Serial):
    def __init__(self, interface_type: str, comment, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert interface_type in {"serial", "usb", "bt", "network"}
        self.type = interface_type
        self.comment = comment
        self.port = None
        self.baudrate = 115200
        self.timeout = 0.05
        self.lock = Lock()

    def __str__(self):
        return f"{self.port} ({self.comment})"
