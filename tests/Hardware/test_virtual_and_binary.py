import struct
import threading

import numpy as np
import pytest

from NanoVNASaver.Calibration import Calibration
from NanoVNASaver.engine.acquire import read_segment
from NanoVNASaver.Hardware.Hardware import get_interface_for_port, get_VNA
from NanoVNASaver.Hardware.NanoVNA import BINARY_RECORD, NanoVNA
from NanoVNASaver.Hardware.VirtualVNA import VirtualInterface, VirtualVNA
from NanoVNASaver.RFTools import Datapoint


def connect(source="demo") -> VirtualVNA:
    iface = get_interface_for_port(f"virtual:{source}")
    iface.open()
    vna = get_VNA(iface)
    assert isinstance(vna, VirtualVNA)
    vna.sweep_delay_per_point = 0
    return vna


def test_virtual_device_reads_segment():
    vna = connect()
    vna.datapoints = 201
    freq, s11, s21 = read_segment(vna, 300_000_000, 600_000_000)
    assert len(freq) == len(s11) == len(s21) == 201
    assert freq[0] == 300_000_000
    assert vna.connected()
    assert "Virtual" in vna.features


def _sweep(vna, standard):
    vna.set_standard(standard)
    freq, s11, s21 = read_segment(vna, 100_000_000, 800_000_000)
    return freq, s11, s21


def _dps(freq, values):
    return [
        Datapoint(f, v.real, v.imag) for f, v in zip(freq, values, strict=False)
    ]


def test_virtual_calibration_recovers_ideal_dut():
    vna = connect("demo")
    vna.noise = 0.0
    cal = Calibration()
    for std, name, idx in (
        ("short", "short", 1),
        ("open", "open", 1),
        ("load", "load", 1),
        ("thru", "through", 2),
        ("thru", "thrurefl", 1),
        ("isolation", "isolation", 2),
    ):
        res = _sweep(vna, std)
        cal.insert(name, _dps(res[0], res[idx]))
    cal.cal_element.short_state = "IDEAL"
    cal.cal_element.open_state = "IDEAL"
    cal.cal_element.load_state = "IDEAL"
    cal.calc_corrections()

    freq, s11m, s21m = _sweep(vna, "dut")
    vna.reversed = True
    _, s22m, s12m = _sweep(vna, "dut")
    f = np.array(freq, dtype=float)
    s11, s21, s12, s22 = cal.correct_two_port_array(f, s11m, s21m, s12m, s22m)
    ideal = connect("ideal")
    ideal.datapoints = vna.datapoints
    truth = ideal._dut(f)
    np.testing.assert_allclose(s11, truth[:, 0, 0], atol=1e-9)
    np.testing.assert_allclose(s21, truth[:, 1, 0], atol=1e-9)
    np.testing.assert_allclose(s12, truth[:, 0, 1], atol=1e-9)
    np.testing.assert_allclose(s22, truth[:, 1, 1], atol=1e-9)


def test_virtual_replays_file():
    vna = connect("tests/data/valid.s2p")
    freq, s11, _ = read_segment(vna, 1_000_000, 2_000_000)
    assert len(s11) == vna.datapoints


def test_virtual_interface_str():
    assert "demo" in str(VirtualInterface("demo"))


class FakeSerial:
    """Minimal serial port emulating a DiSlord scan_bin response"""

    def __init__(self, response_for):
        self.lock = threading.RLock()
        self.timeout = 0.05
        self.buffer = bytearray()
        self.written = []
        self.response_for = response_for
        self.is_open = True

    def write(self, data: bytes):
        self.written.append(data)
        self.buffer += self.response_for(data.decode().strip())

    def read(self, n=1):
        chunk = bytes(self.buffer[:n])
        del self.buffer[:n]
        return chunk

    def readline(self):
        idx = self.buffer.find(b"\n")
        return self.read(len(self.buffer) if idx < 0 else idx + 1)


def binary_response(cmd: str, points: int, corrupt=False) -> bytes:
    rec = np.zeros(points, dtype=BINARY_RECORD)
    rec["freq"] = np.linspace(1e6, 2e6, points).astype(np.uint32)
    rec["s11"][:, 0] = 0.5
    rec["s11"][:, 1] = -0.25
    rec["s21"][:, 0] = 0.125
    header = struct.pack("<HH", 0x87 if not corrupt else 0x81, points)
    return cmd.encode() + b"\r\n" + header + rec.tobytes() + b"ch> "


def make_nanovna(serial, method="scan_bin", points=11):
    vna = NanoVNA.__new__(NanoVNA)
    vna.serial = serial
    vna.start, vna.stop = 1_000_000, 2_000_000
    vna.datapoints = points
    vna.bandwidth = 1000
    vna.sweep_method = method
    vna.features = {"Binary scan"}
    vna._sweepdata = []
    return vna


def test_binary_scan_parses():
    serial = FakeSerial(lambda cmd: binary_response(cmd, 11))
    vna = make_nanovna(serial)
    freqs = vna.read_frequencies()
    assert len(freqs) == 11
    assert freqs[0] == 1_000_000
    s11 = vna.readValues("data 0")
    s21 = vna.readValues("data 1")
    assert s11[0] == pytest.approx(0.5 - 0.25j)
    assert s21[0] == pytest.approx(0.125)
    assert len(serial.written) == 1  # one scan for freq + both channels
    assert serial.written[0].startswith(b"scan_bin 1000000 2000000 11 7")


def test_binary_scan_falls_back_to_text():
    def respond(cmd):
        if cmd.startswith("scan_bin"):
            return binary_response(cmd, 11, corrupt=True)
        lines = "".join(
            f"{1_000_000 + i * 100_000} 0.1 0.2 0.3 0.4\r\n" for i in range(11)
        )
        return (cmd + "\r\n" + lines + "ch> ").encode()

    serial = FakeSerial(respond)
    vna = make_nanovna(serial)
    freqs = vna.read_frequencies()
    assert vna.sweep_method == "scan_mask"
    assert "Binary scan" not in vna.features
    assert len(freqs) == 11
    assert vna.readValues("data 1")[0] == pytest.approx(0.3 + 0.4j)
