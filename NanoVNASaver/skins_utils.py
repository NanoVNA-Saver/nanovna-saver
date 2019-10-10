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
from os.path import join, dirname, abspath
from .about import debug
from .skins import Skins


logger = logging.getLogger(__name__)

def DARK_SKIN_MONOCHROME():
    if debug == True:
        return join(dirname(abspath(__file__)), 'skins/dark-monochrome.css')
    else:
        return sys._MEIPASS + '/skins/dark-monochrome.css'

def DARK_SKIN_COLORED():
    if debug == True:
        return join(dirname(abspath(__file__)), 'skins/dark-colored.css')
    else:
        return sys._MEIPASS + '/skins/dark-colored.css'

def LIGHT_SKIN_MONOCHROME():
    if debug == True:
        return join(dirname(abspath(__file__)), 'skins/light-monochrome.css')
    else:
        return sys._MEIPASS + '/skins/light-monochrome.css'

def LIGHT_SKIN_COLORED():
    if debug == True:
        return join(dirname(abspath(__file__)), 'skins/light-colored.css')
    else:
        return sys._MEIPASS + '/skins/light-colored.css'

# DARK_SKIN_MONOCHROME =  DARK_SKIN_MONOCHROME()
# DARK_SKIN_COLORED = DARK_SKIN_COLORED()
# LIGHT_SKIN_MONOCHROME = LIGHT_SKIN_MONOCHROME()
# LIGHT_SKIN_COLORED = LIGHT_SKIN_COLORED()

DARK_SKIN_STRING_COLORED =  "Dark Colored"
DARK_SKIN_STRING_MONOCHROME = "Dark"
LIGHT_SKIN_STRING_COLORED = "Light Colored"
LIGHT_SKIN_STRING_MONOCHROME = "Light"


class NanoVNA_UI:
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
            logger.debug("Skin set to Default")

    # TODO
    # Skins.dark(app)
    # if self.color_mode_option.isChecked():
    #     app.setStyleSheet("file:///" + DARK_SKIN_COLORED)
    # else if !self.skin_mode_option.isChecked():
    #     app.setStyleSheet("file:///" + DARK_SKIN_MONOCHROME)

    # Skins.light(app)
    # if self.color_mode_option.isChecked():
    #     app.setStyleSheet("file:///" + LIGHT_SKIN_COLORED)
    # else:
    #     app.setStyleSheet("file:///" + LIGHT_SKIN_MONOCHROME)
    def validateSkin(saved_skin):
        if not saved_skin < DARK_SKIN_STRING_COLORED or not saved_skin < DARK_SKIN_STRING_MONOCHROME or not saved_skin < LIGHT_SKIN_STRING_COLORED or not saved_skin < LIGHT_SKIN_STRING_MONOCHROME:
            return True
        else:
            return False
