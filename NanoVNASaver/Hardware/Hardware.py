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
import platform
from typing import List, Tuple
from collections import namedtuple

import serial
from serial.tools import list_ports

from NanoVNASaver.Hardware.VNA import VNA
from NanoVNASaver.Hardware.AVNA import AVNA
from NanoVNASaver.Hardware.NanoVNA_F import NanoVNA_F
from NanoVNASaver.Hardware.NanoVNA_H import NanoVNA_H, NanoVNA_H4
from NanoVNASaver.Hardware.NanoVNA import NanoVNA
from NanoVNASaver.Hardware.NanoVNA_V2 import NanoVNAV2

logger = logging.getLogger(__name__)

Device = namedtuple("Device", "vid pid name")

DEVICETYPES = (
    Device(0x0483, 0x5740, "NanoVNA"),
    Device(0x16c0, 0x0483, "AVNA"),
    Device(0x04b4, 0x0008, "NanaVNA-V2"),
)


# The USB Driver for NanoVNA V2 seems to deliver an
# incompatible hardware info like:
# 'PORTS\\VID_04B4&PID_0008\\DEMO'
# This function will fix it.
def _fix_v2_hwinfo(dev):
    if dev.hwid == r'PORTS\VID_04B4&PID_0008\DEMO':
        dev.vid, dev.pid = 0x04b4, 0x0008
    return dev


# Get list of interfaces with VNAs connected
def get_interfaces() -> List[Tuple[str, str]]:
    return_ports = []
    for d in list_ports.comports():
        if platform.system() == 'Windows' and d.vid is None:
            d = _fix_v2_hwinfo(d)
        for t in DEVICETYPES:
            if d.vid == t.vid and d.pid == t.pid:
                port = d.device
                logger.info("Found %s (%04x %04x) on port %s",
                            t.name, d.vid, d.pid, d.device)
                return_ports.append((port, f"{port}({t.name})"))
    return return_ports


def get_VNA(app, serial_port: serial.Serial) -> 'VNA':
    logger.info("Finding correct VNA type...")

    for _ in range(3):
        vnaType = detect_version(serial_port)
        if vnaType != "unknown":
            break

    serial_port.timeout = 0.2

    if vnaType == 'nanovnav2':
        logger.info("Type: NanoVNA-V2")
        return NanoVNAV2(app, serial_port)

    logger.info("Finding firmware variant...")
    tmp_vna = VNA(app, serial_port)
    tmp_vna.flushSerialBuffers()
    firmware = tmp_vna.readFirmware()
    if firmware.find("AVNA + Teensy") > 0:
        logger.info("Type: AVNA")
        return AVNA(app, serial_port)
    if firmware.find("NanoVNA-H 4") > 0:
        logger.info("Type: NanoVNA-H4")
        return NanoVNA_H4(app, serial_port)
    if firmware.find("NanoVNA-H") > 0:
        logger.info("Type: NanoVNA-H")
        vna = NanoVNA_H(app, serial_port)
        if firmware.find("sweep_points 201") > 0:
            logger.info("VNA has 201 datapoints capability")
            vna._datapoints = (201, 101)
        return vna
    if firmware.find("NanoVNA-F") > 0:
        logger.info("Type: NanoVNA-F")
        return NanoVNA_F(app, serial_port)
    if firmware.find("NanoVNA") > 0:
        logger.info("Type: Generic NanoVNA")
        return NanoVNA(app, serial_port)
    logger.warning("Did not recognize NanoVNA type from firmware.")
    return NanoVNA(app, serial_port)


def detect_version(serialPort: serial.Serial) -> str:
    serialPort.timeout = 0.1

    # drain any outstanding data in the serial incoming buffer
    data = "a"
    while len(data) != 0:
        data = serialPort.read(128)

    # send a \r and see what we get
    serialPort.write(b"\r")

    # will wait up to 0.1 seconds
    data = serialPort.readline().decode('ascii')

    if data == 'ch> ':
        # this is an original nanovna
        return 'nanovna'

    if data == '2':
        # this is a nanovna v2
        return 'nanovnav2'

    logger.error('Unknown VNA type: hardware responded to CR with: %s', data)
    return 'unknown'
