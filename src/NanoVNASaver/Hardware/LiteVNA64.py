import logging
import platform
from struct import iter_unpack, pack, unpack
from time import sleep

from PySide6.QtGui import QImage, QPixmap
from serial import Serial, SerialException

from ..utils.version import Version
from .NanoVNA_V2 import (
    _ADDR_DEVICE_VARIANT,
    _ADDR_FW_MAJOR,
    _ADDR_FW_MINOR,
    _ADDR_HARDWARE_REVISION,
    _ADDR_RAW_SAMPLES_MODE,
    _ADF4350_TXPOWER_DESC_MAP,
    _CMD_READ,
    _CMD_READ2,
    _CMD_WRITE,
    WRITE_SLEEP,
    NanoVNA_V2,
)
from .Serial import Interface

if platform.system() != "Windows":
    pass

logger = logging.getLogger(__name__)

EXPECTED_HW_VERSION = Version.build(2, 2, 0)
EXPECTED_FW_VERSION = Version.build(2, 2, 0)


_ADDR_VBAT_MILIVOLTS = 0x5C
_ADDR_SCREENSHOT = 0xEE


SUPPORTED_PIXEL_FORMAT = 16


# TODO: move screenshot conversation to Convert module
class ScreenshotData:
    header_size = 2 + 2 + 1

    def __init__(self, width: int, height: int, pixel_size: int):
        self.width = width
        self.height = height
        self.pixel_size = pixel_size
        self.data = bytes()

    def data_size(self) -> int:
        return self.width * self.height * int(self.pixel_size / 8)

    def __repr__(self) -> str:
        return (
            f"{self.width}x{self.height} {self.pixel_size}bits "
            f"({self.data_size()} Bytes)"
        )

    @staticmethod
    def from_header(header_data: bytes) -> "ScreenshotData":
        logger.debug("Screenshot header: %s", header_data)

        width, height, depth = unpack("<HHB", header_data)
        return ScreenshotData(width, height, depth)

    @staticmethod
    def rgb565_to_888(rgb565: int) -> tuple[int, int, int]:
        # Extract red, green, and blue components
        r = (rgb565 & 0xF800) >> 11
        g = (rgb565 & 0x07E0) >> 5
        b = rgb565 & 0x001F

        # Scale to 8-bit values
        r = (r * 527 + 23) >> 6
        g = (g * 259 + 33) >> 6
        b = (b * 527 + 23) >> 6

        return r, g, b

    def get_rgb888_data(self) -> bytes:
        result = bytearray()
        for rgb565 in iter_unpack(">H", self.data):
            result.extend(self.rgb565_to_888(rgb565[0]))

        return bytes(result)


class LiteVNA64(NanoVNA_V2):
    name = "LiteVNA-64"
    valid_datapoints: tuple[int, ...] = (
        51,
        101,
        201,
        401,
        801,
        1024,
        1601,
        3201,
        4501,
        6401,
        12801,
        25601,
    )
    screenwidth = 480
    screenheight = 320
    sweep_points_max = 65535
    sweep_max_freq_hz = 6300e6

    def __init__(self, iface: Interface):
        super().__init__(iface)

        self.datapoints = 201

    def read_fw_version(self) -> Version:
        with self.serial.lock:
            return LiteVNA64._get_fw_revision_serial(self.serial)

    def init_features(self) -> None:
        # VBat state will be added dynamicly in get_features()

        self.features.add("Customizable data points")
        self.features.add("Screenshots")

        # TODO: more than one dp per freq
        self.features.add("Multi data points")

        # TODO review this part, which was copy-pasted from NanoVNA_V2
        self.features.add("Set Average")
        self.features.add("Set TX power partial")
        # Can only set ADF4350 power, i.e. for >= 140MHz
        # See https://groups.io/g/liteVNA/message/318 for more details
        self.txPowerRanges = [
            (
                (140e6, self.sweep_max_freq_hz),
                [_ADF4350_TXPOWER_DESC_MAP[value] for value in (3, 2, 1, 0)],
            ),
        ]

    def get_features(self) -> set[str]:
        result = set(self.features)
        result.add(f"Vbat: {self.read_vbat()}V")
        return result

    def read_vbat(self) -> str:
        with self.serial.lock:
            cmd = pack("<BB", _CMD_READ2, _ADDR_VBAT_MILIVOLTS)

            self.serial.write(cmd)
            sleep(WRITE_SLEEP)
            # in a more predictive way
            resp = self.serial.read(2)
            vbat = int.from_bytes(resp, "little") / 1000.0

            logger.debug("Vbat: %sV", vbat)

            return f"{vbat}"

    @staticmethod
    def _get_major_minor_version_serial(
        cmd_major_version: int, cmd_minor_version: int, serial: Serial
    ) -> Version:
        cmd = pack(
            "<BBBB", _CMD_READ, cmd_major_version, _CMD_READ, cmd_minor_version
        )

        serial.write(cmd)
        sleep(WRITE_SLEEP)
        # in a more predictive way
        resp = serial.read(2)

        if len(resp) != 2:
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

    def disconnect(self):
        self._exit_usb_mode()
        super().disconnect()

    def _exit_usb_mode(self) -> None:
        with self.serial.lock:
            self.serial.write(
                pack("<BBB", _CMD_WRITE, _ADDR_RAW_SAMPLES_MODE, 2)
            )
            sleep(WRITE_SLEEP)

    def readValues(self, value) -> list[complex]:
        result = super().readValues(value)
        self._exit_usb_mode()
        return result

    def setSweep(self, start, stop):
        # Device loose these value after going to idle mode
        # Do not try to cache them locally
        step = (stop - start) / (self.datapoints - 1)
        self.sweepStartHz = start
        self.sweepStepHz = step
        logger.info(
            "NanoVNAV2: set sweep start %d step %d",
            self.sweepStartHz,
            self.sweepStepHz,
        )
        self._updateSweep()

    def getScreenshot(self) -> QPixmap:
        logger.debug("Capturing screenshot...")
        self.serial.timeout = 8
        if self.connected():
            try:
                screenshot = self._get_screenshot()

                if screenshot.pixel_size != SUPPORTED_PIXEL_FORMAT:
                    logger.warning(
                        "Unsupported %d screenshot pixel format!",
                        screenshot.pixel_size,
                    )
                    return QPixmap()

                image = QImage(
                    screenshot.get_rgb888_data(),
                    screenshot.width,
                    screenshot.height,
                    QImage.Format.Format_RGB888,
                )

                logger.debug("Screenshot was captured")
                return QPixmap(image)
            except SerialException as exc:
                logger.exception(
                    "Exception while capturing screenshot: %s", exc
                )

        logger.debug("Unable to get screenshot")
        return QPixmap()

    def _get_screenshot(self) -> ScreenshotData:
        with self.serial.lock:
            self.serial.write(pack("<BBB", _CMD_WRITE, _ADDR_SCREENSHOT, 0))
            sleep(WRITE_SLEEP)

            result = ScreenshotData.from_header(
                self.serial.read(ScreenshotData.header_size)
            )

            logger.debug("Screenshot format: %s. Loading data...", result)

            result.data = self.serial.read(result.data_size())

            return result
