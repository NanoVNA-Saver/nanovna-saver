#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
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
import logging
import struct

import numpy as np
from PySide6.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)


def get_argb32_pixmap(image_data: bytes, width, height) -> QPixmap:
    logger.debug(
        "dimenstion: %d x %d, buffer size: %d", width, height, len(image_data)
    )
    rgb_data = struct.unpack(f">{width * height}H", image_data)
    rgb_array = np.array(rgb_data, dtype=np.uint32)
    rgba = (
        0xFF000000
        + ((rgb_array & 0xF800) << 8)
        + ((rgb_array & 0x07E0) << 5)
        + ((rgb_array & 0x001F) << 3)
    )
    return QPixmap(
        QImage(
            rgba,
            width,
            height,
            QImage.Format.Format_ARGB32,
        )
    )


def get_rgb16_pixmap(image_data: bytes, width, height) -> QPixmap:
    return QPixmap(
        QImage(
            image_data,
            width,
            height,
            QImage.Format.Format_RGB16,
        )
    )
