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

from PySide6 import QtCore, QtWidgets

from NanoVNASaver import NanoVNASaver

from ..About import LATEST_URL, TAGS_KEY, TAGS_URL
from ..utils import Version, get_app_version, get_runtime_information
from .ui.about import Ui_DialogAbout

logger = logging.getLogger(__name__)


class AboutWindow(QtWidgets.QDialog):
    def __init__(self, app: NanoVNASaver):
        super(AboutWindow, self).__init__()
        self.ui = Ui_DialogAbout()
        self.ui.setupUi(self)

        self.app = app

        self.ui.l_app_version.setText(get_app_version())

        self.ui.txt_runtime_info.setText("\n".join(get_runtime_information()))
        self.ui.btn_copy_runtime_info.clicked.connect(self.copy_runtime_info)

        self.ui.btn_updates.clicked.connect(self.find_updates)

    def show(self):
        super().show()
        self.update_labels()

    def update_labels(self):
        with contextlib.suppress(IOError, AttributeError):
            device_version = (
                f"{self.app.vna.name} v{self.app.vna.version}"
                if self.app.vna.connected()
                else "not connected"
            )
            self.ui.l_dev_version.setText(device_version)

    # attempt to scan the TAGS_URL web page for something that looks like
    # a version tag. assume the first match with a line containing the TAGS_KEY
    # will contain the latest version substring since it appears at the top
    # of the web page.
    #
    # this routine can also allow the application to automatically perform a
    # check-for-updates and display a pop-up if any are found when this
    # function is called with automatic=True.

    @QtCore.Slot()
    def find_updates(self, automatic=False):
        version_label = self.ui.l_updates_status
        try:
            req = request.Request(TAGS_URL)
            req.add_header("User-Agent", f"NanoVNASaver/{self.app.version}")
            for ln in request.urlopen(req, timeout=3):
                line = ln.decode("utf-8")
                found_latest_version = TAGS_KEY in line
                if found_latest_version:
                    latest_version = Version.parse(
                        re.search(r"(\d+\.\d+\.\d+)", line).group()
                    )
                    break
        except error.HTTPError as e:
            logger.exception(
                "Checking for updates produced an HTTP exception: %s", e
            )
            version_label.setText(f"{e}\n{TAGS_URL}")
            return
        except TypeError as e:
            logger.exception(
                "Checking for updates provided an unparseable file: %s", e
            )
            version_label.setText("Data error reading versions.")
            return
        except error.URLError as e:
            logger.exception(
                "Checking for updates produced a URL exception: %s", e
            )
            version_label.setText("Connection error.")
            return

        if found_latest_version:
            logger.info("Latest version is %s", latest_version)
            this_version = Version.parse(self.app.version)
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
                version_label.setText(
                    f'<a href="{LATEST_URL}">View release page for version '
                    f"{latest_version} in browser</a>"
                )
                version_label.setOpenExternalLinks(True)
            else:
                # Probably don't show a message box, just update the screen?
                # Maybe consider showing it if not an automatic update.
                #
                version_label.setText(
                    f"NanoVNASaver is up to date as of: "
                    f"{strftime('%Y-%m-%d %H:%M:%S', localtime())}"
                )
        else:
            # not good. was gw able to find TAGS_KEY in file in TAGS_URL
            # content! if we get here, something may have changed in the way
            # github creates the .../latest web page.
            version_label.setText(
                "ERROR - Unable to determine what the latest version is!"
            )
            logger.error("Can't find %s in %s content.", TAGS_KEY, TAGS_URL)
        return

    @QtCore.Slot()
    def copy_runtime_info(self) -> None:
        self.ui.txt_runtime_info.selectAll()
        self.ui.txt_runtime_info.copy()
