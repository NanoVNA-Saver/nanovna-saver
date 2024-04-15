from .Hardware import Hardware as hw
from .Calibration import Calibration
from .CalibrationGuide import CalibrationGuide
from .Touchstone import Touchstone
from .SweepWorker import SweepWorker
from datetime import datetime
import threading


class NanoVNASaverHeadless:
    def __init__(self, vna_index=0, verbose=False, save_path="./Save.s2p"):
        """Initialize a NanoVNASaverHeadless object.

        Args:
            vna_index (int): Number of NanoVNAs to connect, at the moment multiple VNAs are not supported. Defaults to 0.
            verbose (bool): Print information. Defaults to False.
            save_path (str): The path to save data to. Defaults to "./Save.s2p".
        """
        self.verbose = verbose
        self.save_path = save_path
        self.iface = hw.get_interfaces()[vna_index]
        self.vna = hw.get_VNA(self.iface)
        self.calibration = Calibration()
        self.touchstone = Touchstone(self.save_path)  # s2p for two port nanovnas.
        self.worker = SweepWorker(self.vna, self.calibration, self.touchstone, verbose)
        self.CalibrationGuide = CalibrationGuide(self.calibration, self.worker, verbose)
        if self.verbose:
            print("VNA is connected: ", self.vna.connected())
            print("Firmware: ", self.vna.readFirmware())
            print("Features: ", self.vna.read_features())

    def calibrate(self, savefile=None, load_file=False):
        """Run the calibration guide and calibrate the NanoVNA.

        Args:
            savefile (path): Path to save the calibration. Defaults to None.
            load_file (bool, optional): Path to existing calibration. Defaults to False.
        """
        if load_file:
            self.CalibrationGuide.loadCalibration(load_file)
            return
        proceed = self.CalibrationGuide.automaticCalibration()
        while proceed:
            proceed = self.CalibrationGuide.automaticCalibrationStep()
        if savefile is None:
            savefile = f"./Calibration_file_{datetime.now()}.s2p"
        self.CalibrationGuide.saveCalibration(savefile)

    def set_sweep(self, start, stop, segments, points):
        """Set the sweep parameters.

        Args:
            start (int): The start frequnecy.
            stop (int): The stop frequency.
            segments (int): Number of segments.
            points (int): Number of points.
        """
        self.worker.sweep.update(start, stop, segments, points)
        if self.verbose:
            print(
                "Sweep set from "
                + str(self.worker.sweep.start / 1e9)
                + "e9"
                + " to "
                + str(self.worker.sweep.end / 1e9)
                + "e9"
            )

    def stream_data(self):
        """Creates a data stream from the continuous sweeping.

        Yields:
            list: Yields a list of data when new data is available.
        """
        self._stream_data()
        try:
            yield list(
                self._access_data()
            )  # Monitor and process data in the main thread
        except Exception as e:
            if self.verbose:
                print("Exception in data stream: ", e)
        finally:
            if self.verbose:
                print("Stopping worker.")
            self._stop_worker()

    def _stream_data(self):
        """Starts a thread for the sweep workers run function."""
        self.worker.sweep.set_mode("CONTINOUS")
        # Start the worker in a new thread
        self.worker_thread = threading.Thread(target=self.worker.run)
        self.worker_thread.start()

    def _access_data(self):
        """Fetches the data from the sweep worker as long as it is running a sweep.

        Yields:
            list: List of data from the latest sweep.
        """
        # Access data while the worker is running
        while self.worker.running:
            yield self.get_data()

    def _stop_worker(self):
        """Stop the sweep worker and kill the stream."""
        if self.verbose:
            print("NanoVNASaverHeadless is stopping sweepworker now.")
        self.worker.running = False
        self.worker_thread.join()

    def get_data(self):
        """Get data from the sweep worker.

        Returns:
            list: Real Reflection, Imaginary Reflection, Real Through, Imaginary Through, Frequency
        """
        data_s11 = self.worker.data11
        data_s21 = self.worker.data21
        reflRe = []
        reflIm = []
        thruRe = []
        thruIm = []
        freq = []
        for datapoint in data_s11:
            reflRe.append(datapoint.re)
            reflIm.append(datapoint.im)
            freq.append(datapoint.freq)
        for datapoint in data_s21:
            thruRe.append(datapoint.re)
            thruIm.append(datapoint.im)

        return reflRe, reflIm, thruRe, thruIm, freq

    def kill(self):
        """Disconnect the NanoVNA.

        Raises:
            Exception: If the NanoVNA was not successfully disconnected.
        """
        self.vna.disconnect()
        if self.vna.connected():
            raise Exception("The VNA was not successfully disconnected.")
        else:
            if self.verbose:
                print("Disconnected VNA.")
            return
