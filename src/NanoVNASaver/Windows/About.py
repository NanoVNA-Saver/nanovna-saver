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
from time import strftime, localtime
from urllib import request, error

from PyQt6 import QtWidgets, QtCore, QtGui

from NanoVNASaver.About import VERSION_URL, INFO_URL
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

        btn_check_version = QtWidgets.QPushButton("Check for NanoVNASaver updates")
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
        btn_ok.clicked.connect(lambda: self.close())  # noqa
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

    def findUpdates(self, automatic=False):
        latest_version = Version()
        latest_url = ""
        try:
            req = request.Request(VERSION_URL)
            req.add_header("User-Agent", f"NanoVNASaver/{self.app.version}")
            for line in request.urlopen(req, timeout=3):
                line = line.decode("utf-8")
                if line.startswith("VERSION ="):
                    latest_version = Version(line[8:].strip(" \"'"))
                if line.startswith("RELEASE_URL ="):
                    latest_url = line[13:].strip(" \"'")
        except error.HTTPError as e:
            logger.exception(
                "Checking for updates produced an HTTP exception: %s", e
            )
            self.updateLabel.setText(f"{e}\n{VERSION_URL}")
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

        logger.info("Latest version is %s", latest_version)
        this_version = Version(self.app.version)
        logger.info("This is %s", this_version)
        if latest_version > this_version:
            logger.info("New update available: %s!", latest_version)
            if automatic:
                QtWidgets.QMessageBox.information(
                    self,
                    "Updates available",
                    f"There is a new update for NanoVNASaver available!\n"
                    f"Version {latest_version}\n\n"
                    f'Press "About" to find the update.',
                )
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Updates available",
                    "There is a new update for NanoVNASaver available!",
                )
            self.updateLabel.setText(
                f'<a href="{latest_url}">New version available</a>.'
            )
            self.updateLabel.setOpenExternalLinks(True)
        else:
            # Probably don't show a message box, just update the screen?
            # Maybe consider showing it if not an automatic update.
            #
            self.updateLabel.setText(
                f"Last checked: "
                f"{strftime('%Y-%m-%d %H:%M:%S', localtime())}"
            )
        return
