import logging
from NanoVNASaver.Hardware.Serial import drain_serial, Interface
import serial
import struct
import numpy as np
from PyQt5 import QtGui

from NanoVNASaver.Hardware.NanoVNA import NanoVNA

logger = logging.getLogger(__name__)


class NanoVNA_F_V2(NanoVNA):
    name = "NanoVNA-F_V2"
    screenwidth = 800
    screenheight = 480

    def  _capture_data(self) -> bytes:
        timeout = self.serial.timeout
        with self.serial.lock:
            drain_serial(self.serial)
            timeout = self.serial.timeout
            self.serial.write("capture\r".encode('ascii'))
            self.serial.readline()
            self.serial.timeout = 4
            image_data = self.serial.read(
                self.screenwidth * self.screenheight * 2)
            self.serial.timeout = timeout
        self.serial.timeout = timeout
        return image_data

    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QtGui.QPixmap()
        try:
            rgba_array = self._capture_data()
            image = QtGui.QImage(
                rgba_array,
                self.screenwidth, self.screenheight,
                QtGui.QImage.Format_RGB16)
            logger.debug("Captured screenshot")
            return QtGui.QPixmap(image)
        except serial.SerialException as exc:
            logger.exception("Exception while capturing screenshot: %s", exc)
        return QtGui.QPixmap()
