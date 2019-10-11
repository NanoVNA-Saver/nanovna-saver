# Author Carl Tremblay - Cinosh07 AKA VA2SAJ
#  Copyright (C) 2019.  Rune B. Broberg
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
import sys
from os.path import join, dirname, abspath, curdir
from .about import debug
from .skins import Skins

ROOT_DIRECTORY = dirname(dirname(__file__))

logger = logging.getLogger(__name__)

def DEFAULT_UI():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/default.css'
    else:
        url = join(ROOT_DIRECTORY, "skins/default.css")
        logger.debug("CSS Url for DEFAULT_UI", url)
        return url


def DARK_SKIN_MONOCHROME():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/dark-monochrome.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins/dark-monochrome.css')
        logger.debug("CSS Url for DARK_SKIN_MONOCHROME", url)
        return url


def DARK_SKIN_COLORED():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/dark-colored.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins/dark-colored.css')
        logger.debug("CSS Url for DARK_SKIN_COLORED", url)
        return url


def LIGHT_SKIN_MONOCHROME():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/light-monochrome.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins/light-monochrome.css')
        logger.debug("CSS Url for LIGHT_SKIN_MONOCHROME", url)
        return url


def LIGHT_SKIN_COLORED():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/light-colored.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins/light-colored.css')
        logger.debug("CSS Url for LIGHT_SKIN_COLORED", url)
        return url


DARK_SKIN_STRING_COLORED = "Dark Colored"
DARK_SKIN_STRING_MONOCHROME = "Dark"
LIGHT_SKIN_STRING_COLORED = "Light Colored"
LIGHT_SKIN_STRING_MONOCHROME = "Light"

def _defaultUI(app):
    with open(DEFAULT_UI()) as stylesheet:
        app.setStyleSheet(stylesheet.read())

class NanoVNA_UI:

    def getSkins():
        return [DARK_SKIN_STRING_COLORED, DARK_SKIN_STRING_MONOCHROME, LIGHT_SKIN_STRING_COLORED, LIGHT_SKIN_STRING_MONOCHROME]

    def defaultUI(app):
        _defaultUI(app)

    def updateUI(self, skin, app):
        current_skin = self.skin_dropdown.currentText()
        logger.debug("Current Skin is: " + current_skin)
        logger.debug("Optionnal Skin to update: " + skin)
        if skin < "NULL":
            if skin == DARK_SKIN_STRING_COLORED:
                current_skin = DARK_SKIN_COLORED()
                logger.debug("Skin set to DARK_SKIN_COLORED")
                Skins.dark(app, self, current_skin)
            if skin == DARK_SKIN_STRING_MONOCHROME:
                current_skin = DARK_SKIN_MONOCHROME()
                Skins.dark(app, self, current_skin)
                logger.debug("Skin set to DARK_SKIN_MONOCHROME")
            if skin == LIGHT_SKIN_STRING_MONOCHROME:
                current_skin = LIGHT_SKIN_MONOCHROME()
                Skins.light(app, self, current_skin)
                logger.debug("Skin set to LIGHT_SKIN_STRING_MONOCHROME")
            if skin == LIGHT_SKIN_STRING_COLORED:
                current_skin = LIGHT_SKIN_COLORED()
                Skins.light(app, self, current_skin)
                logger.debug("Skin set to LIGHT_SKIN_STRING_COLORED")
        else:
            Skins.default(app, self)
            _defaultUI(app)
            logger.debug("Skin set to Default")

    def validateSkin(saved_skin):
        if saved_skin is DARK_SKIN_STRING_COLORED or saved_skin is DARK_SKIN_STRING_MONOCHROME or  saved_skin is LIGHT_SKIN_STRING_COLORED or saved_skin is LIGHT_SKIN_STRING_MONOCHROME:
            return True
        else:
            return False
