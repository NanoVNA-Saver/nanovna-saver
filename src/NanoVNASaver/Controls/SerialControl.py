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
import logging
from time import sleep

from PyQt6 import QtWidgets

from NanoVNASaver.Controls.Control import Control
from NanoVNASaver.Hardware.Hardware import Interface, get_interfaces, get_VNA

logger = logging.getLogger(__name__)


class SerialControl(Control):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__(app, "Serial port control")

        self.interface = Interface("serial", "none")
        self.inp_port = QtWidgets.QComboBox()
        self.inp_port.setMinimumHeight(20)
        self.rescanSerialPort()
        self.inp_port.setEditable(True)
        self.btn_rescan = QtWidgets.QPushButton("Rescan")
        self.btn_rescan.setMinimumHeight(20)
        self.btn_rescan.setFixedWidth(60)
        self.btn_rescan.clicked.connect(self.rescanSerialPort)
        intput_layout = QtWidgets.QHBoxLayout()
        intput_layout.addWidget(QtWidgets.QLabel("Port"), stretch=0)
        intput_layout.addWidget(self.inp_port, stretch=1)
        intput_layout.addWidget(self.btn_rescan, stretch=0)
        self.layout.addRow(intput_layout)

        button_layout = QtWidgets.QHBoxLayout()

        self.btn_toggle = QtWidgets.QPushButton("Connect to device")
        self.btn_toggle.setMinimumHeight(20)
        self.btn_toggle.clicked.connect(self.serialButtonClick)
        button_layout.addWidget(self.btn_toggle, stretch=1)

        self.btn_settings = QtWidgets.QPushButton("Manage")
        self.btn_settings.setMinimumHeight(20)
        self.btn_settings.setFixedWidth(60)
        self.btn_settings.clicked.connect(
            lambda: self.app.display_window("device_settings")
        )

        button_layout.addWidget(self.btn_settings, stretch=0)
        self.layout.addRow(button_layout)

    def rescanSerialPort(self):
        self.inp_port.clear()
        for iface in get_interfaces():
            self.inp_port.insertItem(1, f"{iface}", iface)
        self.inp_port.repaint()

    def serialButtonClick(self):
        if not self.app.vna.connected():
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self):
        with self.interface.lock:
            self.interface = self.inp_port.currentData()
            logger.info("Connection %s", self.interface)
            try:
                self.interface.open()
            except (IOError, AttributeError) as exc:
                logger.error(
                    "Tried to open %s and failed: %s", self.interface, exc
                )
                return
            if not self.interface.isOpen():
                logger.error("Unable to open port %s", self.interface)
                return
            self.interface.timeout = 0.05
        sleep(0.1)
        try:
            self.app.vna = get_VNA(self.interface)
        except IOError as exc:
            logger.error("Unable to connect to VNA: %s", exc)

        self.app.vna.validateInput = self.app.settings.value(
            "SerialInputValidation", False, bool
        )

        # connected
        self.btn_toggle.setText("Disconnect")
        self.btn_toggle.repaint()

        try:
            frequencies = self.app.vna.read_frequencies()
        except ValueError:
            logger.warning("No frequencies read")
            return
        logger.info(
            "Read starting frequency %s and end frequency %s",
            frequencies[0],
            frequencies[-1],
        )
        self.app.sweep_control.set_start(frequencies[0])
        if frequencies[0] < frequencies[-1]:
            self.app.sweep_control.set_end(frequencies[-1])
        else:
            self.app.sweep_control.set_end(
                frequencies[0]
                + self.app.vna.datapoints
                * self.app.sweep_control.get_segments()
            )

        self.app.sweep_control.set_segments(1)  # speed up things
        self.app.sweep_control.update_center_span()
        self.app.sweep_control.update_step_size()

        self.app.windows["sweep_settings"].vna_connected()

        logger.debug("Starting initial sweep")
        self.app.sweep_start()

    def disconnect_device(self):
        with self.interface.lock:
            logger.info("Closing connection to %s", self.interface)
            self.interface.close()
            self.btn_toggle.setText("Connect to device")
            self.btn_toggle.repaint()
