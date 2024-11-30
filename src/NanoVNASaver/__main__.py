#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
"""
NanoVNASaver

A multiplatform tool to save Touchstone files from the
NanoVNA, sweep frequency spans in segments to gain more
data points, and generally display and analyze the
resulting data.
"""
import argparse
import logging
import sys

from PyQt6 import QtWidgets

from NanoVNASaver.About import INFO, version
from NanoVNASaver.NanoVNASaver import NanoVNASaver
from NanoVNASaver.Touchstone import Touchstone


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Set loglevel to debug"
    )
    parser.add_argument(
        "-D", "--debug-file", help="File to write debug logging output to"
    )
    parser.add_argument(
        "-a",
        "--auto-connect",
        action="store_true",
        help="Auto connect if one device detected",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Touchstone file to load as sweep for off" " device usage",
    )
    parser.add_argument(
        "-r",
        "--ref-file",
        help="Touchstone file to load as reference for off" " device usage",
    )
    parser.add_argument(
        "--version", action="version", version=f"NanoVNASaver {version}"
    )
    args = parser.parse_args()

    console_log_level = logging.WARNING
    file_log_level = logging.DEBUG

    print(INFO)

    if args.debug:
        console_log_level = logging.DEBUG

    logger = logging.getLogger("NanoVNASaver")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(console_log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if args.debug_file:
        fh = logging.FileHandler(args.debug_file)
        fh.setLevel(file_log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.info("Startup...")

    app = QtWidgets.QApplication(sys.argv)
    window = NanoVNASaver()
    window.show()

    if args.auto_connect:
        window.auto_connect()
    if args.file:
        t = Touchstone(args.file)
        t.load()
        window.saveData(t.s11, t.s21, args.file)
        window.dataUpdated()
    if args.ref_file:
        t = Touchstone(args.ref_file)
        t.load()
        window.setReference(t.s11, t.s21, args.ref_file)
        window.dataUpdated()
    try:
        app.exec()
    except BaseException as exc:
        logger.exception("%s", exc)
        raise exc


if __name__ == "__main__":
    main()
