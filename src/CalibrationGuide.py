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

from .Calibration import Calibration
from .Sweep import SweepMode

class CalibrationGuide():# renamed from CalibrationWindow since it is no longer a window.
    nextStep = -1

    def __init__(self, calibration, touchstone, worker):
        self.calibration = calibration
        self.data = touchstone
        self.worker = worker

    def cal_save(self, name: str):
        if name in {"through", "isolation"}:
            self.calibration.insert(name, self.data.s21) ######## FIX THIS
        else:
            self.calibration.insert(name, self.data.s11)

    def manual_save(self, name: str):
        self.cal_save(name)

    def reset(self):
        self.calibration = Calibration()

        if len(self.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            if self.verbose:
                print("Saving and displaying raw data.")
            self.saveData(
                self.worker.rawData11,
                self.worker.rawData21,
                self.sweepSource,
            )

    def setOffsetDelay(self, value: float):
        if self.verbose:
            print("New offset delay value: %f ps", value)
        self.worker.offsetDelay = value / 1e12
        if len(self.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            if self.verbose:
                print("Applying new offset to existing sweep data.")
            (
                self.worker.data11,
                self.worker.data21,
            ) = self.worker.applyCalibration(
                self.worker.rawData11, self.worker.rawData21
            )
            if self.verbose:
                print("Saving and displaying corrected data.")
            self.saveData(
                self.worker.data11,
                self.worker.data21,
                self.sweepSource,
            )

    def calculate(self):
        cal_element = self.calibration.cal_element
        if False: #TODO ensure sweep is not currently running.
            print("Unable to apply calibration while a sweep is running. Please stop the sweep and try again.")
            return

        cal_element.short_is_ideal = True
        cal_element.open_is_ideal = True
        cal_element.load_is_ideal = True
        cal_element.through_is_ideal = True

        try:
            self.calibration.calc_corrections()
            
            if self.use_ideal_values:
                self.calibration_source_label.setText(
                    self.calibration.source
                )

            if self.worker.rawData11:
                # There's raw data, so we can get corrected data
                if self.verbose:
                    print("Applying calibration to existing sweep data.")
                (
                    self.worker.data11,
                    self.worker.data21,
                ) = self.worker.applyCalibration(
                    self.worker.rawData11, self.worker.rawData21
                )
                if self.verbose:
                    print("Saving and displaying corrected data.")
                self.saveData(
                    self.worker.data11,
                    self.worker.data21,
                    self.sweepSource,
                )
        except ValueError as e:
            raise Exception(f"Error applying calibration: {str(e)}\nApplying calibration failed.")


    def loadCalibration(self, filename):
        if filename:
            self.calibration.load(filename)
        if not self.calibration.isValid1Port():
            raise Exception("Not a valid port.")

        for i, name in enumerate(
            ("short", "open", "load", "through", "isolation", "thrurefl")
        ):
            if i == 2 and not self.calibration.isValid2Port():
                break
        self.calculate()

    def saveCalibration(self, filename):
        if not self.calibration.isCalculated:
            raise Exception("Cannot save an unapplied calibration state.")

        try:
            self.calibration.save(filename)
            return True
        except Exception as e:
            print("Save failed: ", e)
            return False

    def automaticCalibration(self):
        response = input(
            """Calibration assistant,
            
                This calibration assistant will help you create a calibration\n
                in the NanoVNASaver application. It will sweep the\n
                standards for you and guide you through the process.<br><br>\n
                Before starting, ensure you have Open, Short and Load\n
                standards available and the cables you wish to have\n
                calibrated connected to the device.<br><br>\n
                Make sure sweep is NOT in continuous mode.\n
                If you want a 2-port calibration, also have a through\n
                connector on hand.<br><br>\n
                <b>The best results are achieved by having the NanoVNA\n
                calibrated on-device for the full span of interest and stored\n
                in save slot 0 before starting.</b><br><br>\n\n
                Once you are ready to proceed, press enter. (q to quit).""")
        
        if response.lower() == 'q':
            return
        print("Starting automatic calibration assistant.")
        if not self.vna.connected():
            print("NanoVNA not connected.\n\nPlease ensure the NanoVNA is connected before attempting calibration.")
            return
        
        if self.worker.sweep.properties.mode == SweepMode.CONTINOUS:
            print("Please disable continuous sweeping before attempting calibration.")
            return

        response = input("Calibrate short.\n\nPlease connect the short standard to port 0 of the NanoVNA.\n\n Press enter when you are ready to continue. (q to quit).")

        if response.lower() == 'q':
            return
        
        self.reset()
        self.calibration.source = "Calibration assistant"
        self.nextStep = 0
        self.sweep_start()
        return

    def automaticCalibrationStep(self):
        if self.nextStep == -1:
            return

        if self.nextStep == 0:
            # Short
            self.cal_save("short")
            self.nextStep = 1

            response = input("""Calibrate open.\n\nPlease connect the open
                    standard to port 0 of the NanoVNA.\n\n
                    Either use a supplied open, or leave the end of the
                    cable unconnected if desired.\n\n
                    Press enter when you are ready to continue. (q to quit).""")

            if response.lower() == 'q':
                self.nextStep = -1
                return
            self.sweep_start()
            return

        if self.nextStep == 1:
            # Open
            self.cal_save("open")
            self.nextStep = 2
            response = input("""Calibrate load
                    Please connect the "load" standard to port 0 of the NanoVNA.\n\n
                    Press Ok when you are ready to continue. (q to quit).""")

            if response.lower() == 'q':
                self.nextStep = -1
                return
            self.sweep_start()
            return

        if self.nextStep == 2:
            # Load
            self.cal_save("load")
            self.nextStep = 3
            response = input("""1-port calibration complete,\n
                    The required steps for a 1-port calibration are now complete.\n\n
                    Do you wish to continue and perform a 2-port calibration,
                    enter Y.\nTo apply the 1-port calibration and stop, press q""")

            if response.lower() == 'q':
                self.calculate()
                self.nextStep = -1
                return
            if response.lower() == 'y' or response.lower() == "yes":
                self.nextStep = -1
                return

            response = input("""Calibrate isolation\n
                             Please connect the load standard to port 1 of the 
                             NanoVNA.\n\n If available, also connect a load standard to 
                             port 0.\n\n Press enter when you are ready to continue. (q to quit).""")

            if response.lower() == 'q':
                self.nextStep = -1
                return
            self.sweep_start()
            return

        if self.nextStep == 3:
            # Isolation
            self.cal_save("isolation")
            self.nextStep = 4
            response = input("""Calibrate through.\n
                             Please connect the "through" standard between
                             port 0 and port 1 of the NanoVNA.\n\n
                             Press Ok when you are ready to continue. (q to quit).""")

            if response.lower() == 'q':
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                return
            self.sweep_start()
            return

        if self.nextStep == 4:
            # Done
            self.cal_save("thrurefl")
            self.cal_save("through")
            response = input("""Calibrate complete.\n
                             The calibration process is now complete. Press
                             enter to apply the calibration parameters. (q to quit).""")

            if response.lower() == 'q':
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                return

            self.calculate()
            self.btn_automatic.setDisabled(False)
            self.nextStep = -1
            return
