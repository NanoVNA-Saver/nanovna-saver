"""End to end GUI test against the virtual VNA (headless)."""

import time

import numpy as np
import pytest
from PySide6 import QtWidgets

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.engine.limits import LimitSegment, LimitSpec
from NanoVNASaver.Hardware.VirtualVNA import (
    VirtualInterface,
    VirtualVNA,
    demo_filter,
)
from NanoVNASaver.RFTools import reference_impedance

QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def wait_until(cond, timeout=20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QAPP.processEvents()
        if cond():
            return True
        time.sleep(0.005)
    return cond()


@pytest.fixture(scope="module")
def window():
    from NanoVNASaver.NanoVNASaver import NanoVNASaver

    win = NanoVNASaver()
    win.errors = []
    win.showError = win.errors.append  # no modal dialogs in tests
    combo = win.serial_control.inp_port
    idx = next(
        i
        for i in range(combo.count())
        if isinstance(combo.itemData(i), VirtualInterface)
    )
    combo.setCurrentIndex(idx)
    win.serial_control.connect_device()
    assert wait_until(lambda: isinstance(win.vna, VirtualVNA))
    win.vna.sweep_delay_per_point = 0
    win.vna.noise = 0.0
    assert wait_until(lambda: not win.worker.isRunning())
    yield win
    win.worker.quit()
    win.worker.wait(5000)
    win.close()


def sweep(win) -> None:
    win.sweep_start()
    assert wait_until(lambda: win.worker.isRunning() or win.worker.isFinished())
    assert wait_until(lambda: not win.worker.isRunning())
    wait_until(lambda: False, 0.1)  # let throttled updates run
    assert not win.errors, win.errors


def s11(win) -> np.ndarray:
    return np.array([d.z for d in win.data.s11])


def test_connect_and_sweep(window):
    sweep(window)
    assert len(window.data.s11) == window.vna.datapoints
    assert window.worker.has_raw_data()


def test_calibration_with_assistant_standards(window):
    calwin = window.windows["calibration"]
    calwin.reset()
    for standard, names in (
        ("short", ["short"]),
        ("open", ["open"]),
        ("load", ["load"]),
        ("isolation", ["isolation"]),
        ("thru", ["thrurefl", "through"]),
    ):
        calwin._virtual_connect(standard)
        sweep(window)
        for name in names:
            calwin.cal_save(name)
    calwin._virtual_connect("dut")
    calwin.calculate()
    assert window.calibration.isCalculated
    assert window.calibration.isValid2Port()
    sweep(window)
    freq = np.array([d.freq for d in window.data.s11], dtype=float)
    truth = demo_filter(freq)
    # forward only: S11 still sees the port 2 load match (|e22| = 0.05 in
    # the simulator) - only the full 2-port correction removes that.
    np.testing.assert_allclose(s11(window), truth[:, 0, 0], atol=0.06)
    out_of_band = np.abs(truth[:, 1, 0]) < 1e-3
    np.testing.assert_allclose(
        s11(window)[out_of_band], truth[out_of_band, 0, 0], atol=1e-4
    )
    calwin.update_health()
    assert "INFO" in calwin.health_label.text() or calwin.health_label.text()


def test_smoothing_and_tag(window):
    window.windows["sweep_settings"].smoothing_input.setValue(2.0)
    wait_until(lambda: False, 0.1)
    assert "Smo 2%" in Chart.processing_tag
    window.windows["sweep_settings"].smoothing_input.setValue(0.0)
    wait_until(lambda: False, 0.1)
    assert "Smo" not in Chart.processing_tag


def test_fixture_reference_impedance(window):
    fixture = window.windows["fixture"]
    before = s11(window).copy()
    fixture.z0.setValue(75.0)
    assert reference_impedance() == 75.0
    assert wait_until(lambda: "Z0 75" in Chart.processing_tag, 2)
    assert not np.allclose(s11(window), before)
    fixture.z0.setValue(50.0)
    assert reference_impedance() == 50.0
    np.testing.assert_allclose(s11(window), before, atol=1e-9)


def test_full_two_port(window):
    two_port = window.windows["two_port"]
    sweep(window)
    two_port.capture_forward()
    assert window.vna.reversed
    sweep(window)
    two_port.capture_reverse()
    two_port.combine_and_show()
    assert two_port.result is not None
    freq = two_port.result.freq
    truth = demo_filter(freq)
    np.testing.assert_allclose(two_port.result.s22, truth[:, 1, 1], atol=1e-6)
    np.testing.assert_allclose(two_port.result.s12, truth[:, 0, 1], atol=1e-6)
    assert len(window.data.s22) == len(freq)


def test_pro_traces(window, tmp_path):
    pro = window.windows["pro_traces"]
    sweep(window)
    pro.show()
    pro.refresh()
    pro.spec = LimitSpec(
        "test",
        [LimitSegment("s21", "logmag", "lower", 420e6, 450e6, -6.0)],
    )
    pro.refresh(fetch=False)
    assert pro.verdict.text() == "PASS"
    pro.trace_select.setCurrentIndex(2)  # Tr3 = S21 log mag
    pro.search_max()
    assert pro.marker_freqs[0] == pytest.approx(435e6, rel=0.03)
    # tracking: marker 2 follows the S11 minimum on every refresh
    pro.marker_select.setCurrentIndex(1)
    pro.trace_select.setCurrentIndex(0)
    pro.track_check.setChecked(True)
    pro.search_min()
    pro.marker_freqs[1] = None
    pro.refresh(fetch=False)
    assert pro.marker_freqs[1] == pytest.approx(435e6, rel=0.03)
    pro.marker_select.setCurrentIndex(0)
    pro.trace_select.setCurrentIndex(2)
    pro.track_check.setChecked(False)
    pro.bw_value.setValue(3.0)
    pro.search_bandwidth()
    assert "BW" in pro.search_result.text()
    pro.data_to_memory()
    pro.trace_widgets[2][3].setCurrentIndex(2)  # data / mem
    pro.refresh(fetch=False)
    report = tmp_path / "r.html"
    from NanoVNASaver.engine.report import (
        ReportInfo,
        build_report,
        save_report,
    )

    save_report(report, build_report(pro.data, ReportInfo(), pro.spec))
    assert "PASS" in report.read_text(encoding="utf-8")
    pro.hide()


def test_matching_and_gate(window):
    matching = window.windows["matching"]
    matching.freq_input.setText("435M")
    matching.calculate()
    assert "Load at" in matching.load_label.text()
    tdr = window.windows["tdr"]
    tdr.gate_enabled.setChecked(True)
    assert tdr.gate_settings() is not None
    assert len(tdr.gated_s11()) == len(window.data.s11)
    tdr.gate_enabled.setChecked(False)


def test_s11_min_max_button(window):
    sweep(window)
    window.find_s11_min_max()
    db = 20 * np.log10(np.abs(s11(window)))
    freqs = [d.freq for d in window.data.s11]
    assert window.markers[0].freq == freqs[int(np.argmin(db))]
    assert window.markers[1].freq == freqs[int(np.argmax(db))]
    assert "@" in window.s11_min_label.text()
    assert "@" in window.s11_max_label.text()


def test_s21_min_max_button(window):
    sweep(window)
    window.find_s21_min_max()
    s21 = np.array([d.z for d in window.data.s21])
    db = 20 * np.log10(np.abs(s21))
    freqs = [d.freq for d in window.data.s21]
    assert window.markers[0].freq == freqs[int(np.argmin(db))]
    assert window.markers[1].freq == freqs[int(np.argmax(db))]
    assert "@" in window.s21_max_label.text()
    window.s11_minmax_auto.setChecked(True)
    window.s21_minmax_auto.setChecked(True)
    assert not window.s11_minmax_auto.isChecked()
    window.s21_minmax_auto.setChecked(False)
