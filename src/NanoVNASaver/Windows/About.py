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

from PyQt5 import QtWidgets, QtCore

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

        top_layout = QtWidgets.QHBoxLayout()
        make_scrollable(self, top_layout)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        icon_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(icon_layout)
        icon = QtWidgets.QLabel()
        icon.setPixmap(self.app.icon.pixmap(128, 128))
        icon_layout.addWidget(icon)
        icon_layout.addStretch()

        layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(layout)

        layout.addWidget(
            QtWidgets.QLabel(f"NanoVNASaver version {self.app.version}")
        )
        layout.addWidget(QtWidgets.QLabel(""))
        layout.addWidget(
            QtWidgets.QLabel(
                "\N{COPYRIGHT SIGN} Copyright 2019, 2020 Rune B. Broberg\n"
                "\N{COPYRIGHT SIGN} Copyright 2020ff NanoVNA-Saver Authors"
            )
        )
        layout.addWidget(
            QtWidgets.QLabel("This program comes with ABSOLUTELY NO WARRANTY")
        )
        layout.addWidget(
            QtWidgets.QLabel(
                "This program is licensed under the"
                " GNU General Public License version 3"
            )
        )
        layout.addWidget(QtWidgets.QLabel(""))
        link_label = QtWidgets.QLabel(
            f'For further details, see: <a href="{INFO_URL}">' f"{INFO_URL}"
        )
        link_label.setOpenExternalLinks(True)
        layout.addWidget(link_label)
        layout.addWidget(QtWidgets.QLabel(""))

        self.versionLabel = QtWidgets.QLabel(
            "NanoVNA Firmware Version: Not connected."
        )
        layout.addWidget(self.versionLabel)

        layout.addStretch()

        btn_check_version = QtWidgets.QPushButton("Check for updates")
        btn_check_version.clicked.connect(self.findUpdates)

        self.updateLabel = QtWidgets.QLabel("Last checked: ")

        update_hbox = QtWidgets.QHBoxLayout()
        update_hbox.addWidget(btn_check_version)
        update_form = QtWidgets.QFormLayout()
        update_hbox.addLayout(update_form)
        update_hbox.addStretch()
        update_form.addRow(self.updateLabel)
        layout.addLayout(update_hbox)

        layout.addStretch()

        btn_ok = QtWidgets.QPushButton("Ok")
        btn_ok.clicked.connect(lambda: self.close())  # noqa
        layout.addWidget(btn_ok)

    def show(self):
        super().show()
        self.updateLabels()

    def updateLabels(self):
        with contextlib.suppress(IOError, AttributeError):
            self.versionLabel.setText(
                f"NanoVNA Firmware Version: {self.app.vna.name} "
                f"v{self.app.vna.version}"
            )

    def findUpdates(self, automatic=False):
        latest_version = Version()
        latest_url = ""
        try:
            req = request.Request(VERSION_URL)
            req.add_header("User-Agent", f"NanoVNA-Saver/{self.app.version}")
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
            self.updateLabel.setText("Connection error.")
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
                    f"There is a new update for NanoVNA-Saver available!\n"
                    f"Version {latest_version}\n\n"
                    f'Press "About" to find the update.',
                )
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Updates available",
                    "There is a new update for NanoVNA-Saver available!",
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
