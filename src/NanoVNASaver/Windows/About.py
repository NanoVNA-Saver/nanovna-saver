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

import contextlib
import logging
import re
from time import localtime, strftime
from urllib import error, request

from PyQt6 import QtCore, QtGui, QtWidgets

from NanoVNASaver.About import INFO_URL, LATEST_URL, TAGS_KEY, TAGS_URL
from NanoVNASaver.Version import Version
from NanoVNASaver.Windows.Defaults import make_scrollable

logger = logging.getLogger(__name__)


class AboutWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setWindowTitle("About NanoVNASaver")
        self.setWindowIcon(self.app.icon)

        top_layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, top_layout)

        upper_layout = QtWidgets.QHBoxLayout()
        top_layout.addLayout(upper_layout)
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        icon_layout = QtWidgets.QVBoxLayout()
        upper_layout.addLayout(icon_layout)
        icon = QtWidgets.QLabel()
        icon.setPixmap(self.app.icon.pixmap(128, 128))
        icon_layout.addWidget(icon)
        icon_layout.addStretch()

        info_layout = QtWidgets.QVBoxLayout()
        upper_layout.addLayout(info_layout)
        upper_layout.addStretch()

        info_layout.addWidget(
            QtWidgets.QLabel(f"NanoVNASaver version {self.app.version}")
        )
        info_layout.addWidget(QtWidgets.QLabel(""))
        info_layout.addWidget(
            QtWidgets.QLabel(
                "\N{COPYRIGHT SIGN} Copyright 2019, 2020 Rune B. Broberg\n"
                "\N{COPYRIGHT SIGN} Copyright 2020ff NanoVNA-Saver Authors"
            )
        )
        info_layout.addWidget(
            QtWidgets.QLabel("This program comes with ABSOLUTELY NO WARRANTY")
        )
        info_layout.addWidget(
            QtWidgets.QLabel(
                "This program is licensed under the"
                " GNU General Public License version 3"
            )
        )
        info_layout.addWidget(QtWidgets.QLabel(""))
        link_label = QtWidgets.QLabel(
            f'For further details, see: <a href="{INFO_URL}">' f"{INFO_URL}"
        )
        link_label.setOpenExternalLinks(True)
        info_layout.addWidget(link_label)
        info_layout.addWidget(QtWidgets.QLabel(""))

        lower_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(lower_layout)

        btn_check_version = QtWidgets.QPushButton(
            "Check for NanoVNASaver updates"
        )
        btn_check_version.clicked.connect(self.findUpdates)

        self.updateLabel = QtWidgets.QLabel()

        update_hbox = QtWidgets.QHBoxLayout()
        update_hbox.addWidget(btn_check_version)
        update_hbox.addStretch()
        lower_layout.addLayout(update_hbox)
        lower_layout.addWidget(self.updateLabel)

        lower_layout.addStretch()

        self.versionLabel = QtWidgets.QLabel(
            "NanoVNA Firmware Version: Not connected."
        )
        lower_layout.addWidget(self.versionLabel)

        lower_layout.addStretch()

        btn_ok = QtWidgets.QPushButton("Ok")
        btn_ok.clicked.connect(lambda: self.close())
        lower_layout.addWidget(btn_ok)

    def show(self):
        super().show()
        self.updateLabels()

    def updateLabels(self):
        with contextlib.suppress(IOError, AttributeError):
            if self.app.vna.connected():
                self.versionLabel.setText(
                    f"NanoVNA Firmware Version: {self.app.vna.name} "
                    f"v{self.app.vna.version}"
                )
            else:
                self.versionLabel.setText(
                    "NanoVNA Firmware Version: Not connected."
                )

    # attempt to scan the TAGS_URL web page for something that looks like
    # a version tag. assume the first match with a line containing the TAGS_KEY
    # will contain the latest version substring since it appears at the top
    # of the web page.
    #
    # this routine can also allow the application to automatically perform a
    # check-for-updates and display a pop-up if any are found when this
    # function is called with automatic=True.

    def findUpdates(self, automatic=False):
        try:
            req = request.Request(TAGS_URL)
            req.add_header("User-Agent", f"NanoVNASaver/{self.app.version}")
            for ln in request.urlopen(req, timeout=3):
                line = ln.decode("utf-8")
                found_latest_version = TAGS_KEY in line
                if found_latest_version:
                    latest_version = Version(
                        re.search(r"(\d+\.\d+\.\d+)", line).group()
                    )
                    break
        except error.HTTPError as e:
            logger.exception(
                "Checking for updates produced an HTTP exception: %s", e
            )
            self.updateLabel.setText(f"{e}\n{TAGS_URL}")
            return
        except TypeError as e:
            logger.exception(
                "Checking for updates provided an unparseable file: %s", e
            )
            self.updateLabel.setText("Data error reading versions.")
            return
        except error.URLError as e:
            logger.exception(
                "Checking for updates produced a URL exception: %s", e
            )
            self.updateLabel.setText("Connection error.")
            return

        if found_latest_version:
            logger.info("Latest version is %s", latest_version)
            this_version = Version(self.app.version)
            logger.info("This is %s", this_version)
            if latest_version > this_version:
                logger.info("New update available: %s!", latest_version)
                if automatic:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Update available",
                        f"There is a new update for NanoVNASaver available!\n"
                        f"Version {latest_version}\n\n"
                        f'Press "About ..." to find the update.',
                    )
                else:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Update available",
                        "There is a new update for NanoVNASaver available!\n"
                        f"Version {latest_version}\n\n",
                    )
                self.updateLabel.setText(
                    f'<a href="{LATEST_URL}">View release page for version '
                    f"{latest_version} in browser</a>"
                )
                self.updateLabel.setOpenExternalLinks(True)
            else:
                # Probably don't show a message box, just update the screen?
                # Maybe consider showing it if not an automatic update.
                #
                self.updateLabel.setText(
                    f"NanoVNASaver is up to date as of: "
                    f"{strftime('%Y-%m-%d %H:%M:%S', localtime())}"
                )
        else:
            # not good. was gw able to find TAGS_KEY in file in TAGS_URL
            # content! if we get here, something may have changed in the way
            # github creates the .../latest web page.
            self.updateLabel.setText(
                "ERROR - Unable to determine what the latest version is!"
            )
            logger.error(f"Can't find {TAGS_KEY} in {TAGS_URL} content.")
        return
