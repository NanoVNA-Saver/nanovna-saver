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

    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QtGui.QPixmap()
        try:
            rgba_array = self._capture_data()
            image = QtGui.QImage(
                rgba_array,
                self.screenwidth,
                self.screenheight,
                QtGui.QImage.Format_RGB16)
            logger.debug("Captured screenshot")
            return QtGui.QPixmap(image)
        except serial.SerialException as exc:
            logger.exception(
                "Exception while capturing screenshot: %s", exc)
        return QtGui.QPixmap()
