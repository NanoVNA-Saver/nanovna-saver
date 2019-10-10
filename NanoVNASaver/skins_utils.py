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
from os.path import join, dirname, abspath
import sys
from .about import debug

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

DARK_SKIN_MONOCHROME =  DARK_SKIN_MONOCHROME()
DARK_SKIN_COLORED = DARK_SKIN_COLORED()
LIGHT_SKIN_MONOCHROME = LIGHT_SKIN_MONOCHROME()
LIGHT_SKIN_COLORED = LIGHT_SKIN_COLORED()
