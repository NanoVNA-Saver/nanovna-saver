#! /bin/env python

#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
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

from PyQt5 import QtWidgets, QtCore

from .NanoVNASaver import NanoVNASaver
from .about import debug


def main():
    print("NanoVNASaver " + NanoVNASaver.version)
    print("Copyright (C) 2019 Rune B. Broberg")
    print("This program comes with ABSOLUTELY NO WARRANTY")
    print("This program is licensed under the GNU General Public License version 3")
    print("")
    print("See https://github.com/mihtjel/nanovna-saver for further details")
    # Main code goes here
    console_log_level = logging.WARNING
    file_log_level = logging.DEBUG
    log_file = ""

    for i in range(len(sys.argv)):
        if sys.argv[i] == "-d":
            console_log_level = logging.DEBUG
        elif sys.argv[i] == "-D" and i < len(sys.argv) - 1:
            log_file = sys.argv[i+1]
        elif sys.argv[i] == "-D":
            print("You must enter a file name when using -D")
            return

    if debug:
        console_log_level = logging.DEBUG

    logger = logging.getLogger("NanoVNASaver")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(console_log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    if log_file != "":
        try:
            fh = logging.FileHandler(log_file)
        except Exception as e:
            logger.exception("Error opening log file: %s", e)
            return

        fh.setLevel(file_log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.info("Startup...")

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(sys.argv)
    window = NanoVNASaver()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
