import logging
import platform
from struct import pack
from time import sleep

from serial import Serial

from NanoVNASaver.Hardware.Serial import Interface

from ..utils.version import Version
from .NanoVNA_V2 import (
    _ADDR_DEVICE_VARIANT,
    _ADDR_FW_MAJOR,
    _ADDR_FW_MINOR,
    _ADDR_HARDWARE_REVISION,
    _CMD_READ,
    WRITE_SLEEP,
    NanoVNA_V2,
)

if platform.system() != "Windows":
    pass

logger = logging.getLogger(__name__)

EXPECTED_HW_VERSION = Version.build(2, 2, 0)
EXPECTED_FW_VERSION = Version.build(2, 2, 0)


class LiteVNA64(NanoVNA_V2):
    name = "LiteVNA-64"
    valid_datapoints = (101, 11, 51, 201, 301, 501, 1023, 2047, 4095)
    screenwidth = 480
    screenheight = 320
    sweep_points_max = 65535

    def __init__(self, iface: Interface):
        super().__init__(iface)

    def read_fw_version(self) -> Version:
        with self.serial.lock:
            return LiteVNA64._get_fw_revision_serial(self.serial)

    @staticmethod
    def _get_major_minor_version_serial(
        cmd_major_version: int, cmd_minor_version: int, serial: Serial
    ) -> Version:
        cmd = pack(
            "<BBBB", _CMD_READ, cmd_major_version, _CMD_READ, cmd_minor_version
        )

        serial.write(cmd)
        # sleep(WRITE_SLEEP)
        sleep(2.0)  # could fix bug #585 but shoud be done
        # in a more predictive way
        resp = serial.read(2)

        if len(resp) != 2:  # noqa: PLR2004
            logger.error("Timeout reading version registers. Got: %s", resp)
            raise IOError("Timeout reading version registers")
        return Version.build(resp[0], resp[1])

    @staticmethod
    def _get_fw_revision_serial(serial: Serial) -> Version:
        result = LiteVNA64._get_major_minor_version_serial(
            _ADDR_FW_MAJOR, _ADDR_FW_MINOR, serial
        )
        logger.debug("Firmware version: %s", result)
        return result

    @staticmethod
    def _get_hw_revision_serial(serial: Serial) -> Version:
        result = LiteVNA64._get_major_minor_version_serial(
            _ADDR_DEVICE_VARIANT, _ADDR_HARDWARE_REVISION, serial
        )
        logger.debug(
            "Hardware version ({device_variant}.{hardware_revision}): %s",
            result,
        )
        return result

    @staticmethod
    def is_lite_vna_64(serial: Serial) -> bool:
        hw_version = LiteVNA64._get_hw_revision_serial(serial)
        fw_version = LiteVNA64._get_fw_revision_serial(serial)
        return (
            hw_version == EXPECTED_HW_VERSION
            and fw_version == EXPECTED_FW_VERSION
        )
