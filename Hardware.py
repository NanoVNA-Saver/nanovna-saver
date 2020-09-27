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
from collections import namedtuple
from time import sleep
from typing import List

import serial
from serial.tools import list_ports

from NanoVNASaver.Hardware.AVNA import AVNA
from NanoVNASaver.Hardware.NanoVNA import NanoVNA
from NanoVNASaver.Hardware.NanoVNA_F import NanoVNA_F
from NanoVNASaver.Hardware.NanoVNA_F_V2 import NanoVNA_F_V2
from NanoVNASaver.Hardware.NanoVNA_H import NanoVNA_H
from NanoVNASaver.Hardware.NanoVNA_H4 import NanoVNA_H4
from NanoVNASaver.Hardware.NanoVNA_V2 import NanoVNA_V2
from NanoVNASaver.Hardware.Serial import drain_serial, Interface


logger = logging.getLogger(__name__)

USBDevice = namedtuple("Device", "vid pid name")

USBDEVICETYPES = (
    USBDevice(0x0483, 0x5740, "NanoVNA"),
    USBDevice(0x16c0, 0x0483, "AVNA"),
    USBDevice(0x04b4, 0x0008, "S-A-A-2"),
)
RETRIES = 3
TIMEOUT = 0.2
WAIT = 0.05

# The USB Driver for NanoVNA V2 seems to deliver an
# incompatible hardware info like:
# 'PORTS\\VID_04B4&PID_0008\\DEMO'
# This function will fix it.
def _fix_v2_hwinfo(dev):
    if dev.hwid == r'PORTS\VID_04B4&PID_0008\DEMO':
        dev.vid, dev.pid = 0x04b4, 0x0008
    return dev


# Get list of interfaces with VNAs connected
def get_interfaces() -> List[Interface]:
    interfaces = []
    # serial like usb interfaces
    for d in list_ports.comports():
        if platform.system() == 'Windows' and d.vid is None:
            d = _fix_v2_hwinfo(d)
        for t in USBDEVICETYPES:
            if d.vid != t.vid or d.pid != t.pid:
                continue
            logger.debug("Found %s USB:(%04x:%04x) on port %s",
                         t.name, d.vid, d.pid, d.device)
            iface = Interface('serial', t.name)
            iface.port = d.device
            interfaces.append(iface)
    return interfaces


def get_VNA(iface: Interface) -> 'VNA':
    # serial_port.timeout = TIMEOUT

    logger.info("Finding correct VNA type...")
    with iface.lock:
        vna_version = detect_version(iface)

    if vna_version == 'v2':
        logger.info("Type: NanoVNA-V2")
        return NanoVNA_V2(iface)

    logger.info("Finding firmware variant...")
    info = get_info(iface)
    if info.find("AVNA + Teensy") >= 0:
        logger.info("Type: AVNA")
        return AVNA(iface)
    if info.find("NanoVNA-H 4") >= 0:
        logger.info("Type: NanoVNA-H4")
        vna = NanoVNA_H4(iface)
        return vna
    if info.find("NanoVNA-H") >= 0:
        logger.info("Type: NanoVNA-H")
        vna = NanoVNA_H(iface)
        return vna
    if info.find("NanoVNA-F_V2") >= 0:
        logger.info("Type: NanoVNA-F_V2")
        return NanoVNA_F_V2(iface)
    if info.find("NanoVNA-F") >= 0:
        logger.info("Type: NanoVNA-F")
        return NanoVNA_F(iface)
    if info.find("NanoVNA") >= 0:
        logger.info("Type: Generic NanoVNA")
        return NanoVNA(iface)
    logger.warning("Did not recognize NanoVNA type from firmware.")
    return NanoVNA(iface)

def detect_version(serial_port: serial.Serial) -> str:
    data = ""
    for i in range(RETRIES):
        drain_serial(serial_port)
        serial_port.write("\r".encode("ascii"))
        sleep(0.05)
        data = serial_port.read(128).decode("ascii")
        if data.startswith("ch> "):
            return "v1"
        # -H versions
        if data.startswith("\r\nch> "):
            return "vh"
        if data.startswith("2"):
            return "v2"
        logger.debug("Retry detection: %s", i + 1)
    logger.error('No VNA detected. Hardware responded to CR with: %s', data)
    return ""

def get_info(serial_port: serial.Serial) -> str:
    for _ in range(RETRIES):
        drain_serial(serial_port)
        serial_port.write("info\r".encode("ascii"))
        lines = []
        retries = 0
        while True:
            line = serial_port.readline()
            line = line.decode("ascii").strip()
            if not line:
                retries += 1
                if retries > RETRIES:
                    return ""
                sleep(WAIT)
                continue
            if line == "info":  # suppress echo
                continue
            if line.startswith("ch>"):
                logger.debug("Needed retries: %s", retries)
                break
            lines.append(line)
        return "\n".join(lines)
