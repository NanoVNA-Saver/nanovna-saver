import math
from datetime import datetime, timedelta

import numpy as np
import pytest

from NanoVNASaver.Calibration import Calibration
from NanoVNASaver.engine import SweepData
from NanoVNASaver.engine.calkit import BUILTIN_KITS, CalKit, CalKitLibrary
from NanoVNASaver.engine.deembed import (
    FixtureSettings,
    PortExtension,
    apply_fixture,
    auto_port_extension,
    cascade,
    deembed_one_port,
    deembed_two_port,
    renormalize_one_port,
    renormalize_two_port,
)
from NanoVNASaver.engine.dsp import (
    RunningAverage,
    SegmentRunningAverage,
    group_delay,
    smooth,
    smoothing_window,
)
from NanoVNASaver.engine.formats import TraceFormat, convert, gamma_to_z
from NanoVNASaver.engine.health import (
    Severity,
    check_calibration,
    verify_standard,
)
from NanoVNASaver.engine.limits import LimitSegment, LimitSpec, log_result
from NanoVNASaver.engine.matching import input_impedance, l_networks
from NanoVNASaver.engine.search import (
    next_peak,
    search_bandwidth,
    search_max,
    search_min,
    search_target,
)
from NanoVNASaver.engine.tdr import distance_to_time, time_gate, transform

RNG = np.random.default_rng(1)


# DSP


def test_smoothing_window():
    assert smoothing_window(1001, 0) == 1
    assert smoothing_window(1001, 1) == 9  # 10 -> odd
    assert smoothing_window(5, 100) == 5


def test_smooth_reduces_noise_and_keeps_constant():
    const = np.full(201, 0.5 + 0.5j)
    np.testing.assert_allclose(smooth(const, 5), const)
    noisy = const + 0.05 * (RNG.normal(size=201) + 1j * RNG.normal(size=201))
    assert np.std(smooth(noisy, 5) - const) < np.std(noisy - const) / 2


def test_running_average():
    avg = RunningAverage(4)
    for v in (1, 2, 3, 4):
        res = avg.add(np.array([v], dtype=complex))
    assert res[0] == pytest.approx(2.5)
    assert avg.n == 4
    res = avg.add(np.array([10], dtype=complex))
    assert res[0] == pytest.approx(2.5 + (10 - 2.5) / 4)
    assert avg.n == 4


def test_segment_running_average():
    avg = SegmentRunningAverage(2)
    avg.add(0, np.array([1.0]))
    avg.add(1, np.array([1.0]))
    assert avg.n == 1
    assert avg.add(0, np.array([3.0]))[0] == pytest.approx(2)
    assert avg.n == 1  # segment 1 only one sweep


def test_group_delay_of_delay_line():
    freq = np.linspace(1e6, 1e9, 101)
    tau = 3e-9
    s21 = np.exp(-2j * np.pi * freq * tau)
    np.testing.assert_allclose(group_delay(freq, s21, 2), tau, rtol=1e-6)


# formats


def test_formats():
    freq = np.array([1e6, 2e6])
    g = np.array([0.0, 1 / 3], dtype=complex)
    np.testing.assert_allclose(convert(TraceFormat.VSWR, freq, g), [1, 2])
    np.testing.assert_allclose(
        convert(TraceFormat.RESISTANCE, freq, g), [50, 100]
    )
    np.testing.assert_allclose(
        convert(TraceFormat.LOGMAG, freq, np.array([1, 0.1])), [0, -20]
    )
    z = 50 + 1j * 2 * math.pi * 1e6 * 1e-6  # 1 uH
    gamma = (z - 50) / (z + 50)
    assert convert(TraceFormat.SERIES_L, np.array([1e6]), np.array([gamma]))[
        0
    ] == pytest.approx(1e-6)


# de-embedding


def rand_s(n=11, scale=0.2):
    s = scale * (RNG.normal(size=(n, 2, 2)) + 1j * RNG.normal(size=(n, 2, 2)))
    s[:, 1, 0] += 0.7
    s[:, 0, 1] += 0.7
    return s


def test_cascade_deembed_roundtrip():
    a, dut, b = rand_s(), rand_s(), rand_s()
    meas = cascade(a, dut, b)
    np.testing.assert_allclose(deembed_two_port(meas, a, b), dut, atol=1e-10)


def test_deembed_one_port():
    a = rand_s()
    gamma = 0.3 * (RNG.normal(size=11) + 1j * RNG.normal(size=11))
    load = np.zeros((11, 2, 2), dtype=complex)
    load[:, 0, 0] = gamma
    # reflection through fixture a
    gm = a[:, 0, 0] + a[:, 0, 1] * a[:, 1, 0] * gamma / (1 - a[:, 1, 1] * gamma)
    np.testing.assert_allclose(deembed_one_port(gm, a), gamma, atol=1e-12)


def test_port_extension_auto_fit():
    freq = np.linspace(1e6, 3e9, 301)
    ext = PortExtension(delay=250e-12, loss_db=0.3)
    measured_open = 1 / (ext.factor(freq) ** 2)
    fit = auto_port_extension(freq, measured_open, "open")
    assert fit.delay == pytest.approx(250e-12, rel=1e-6)
    assert fit.loss_db == pytest.approx(0.3, rel=1e-6)
    data = SweepData(freq, measured_open, np.zeros_like(measured_open))
    out = apply_fixture(data, FixtureSettings(port1=fit))
    np.testing.assert_allclose(out.s11, 1, atol=1e-6)


def test_renormalize_consistent():
    z = np.array([25 + 10j, 100 - 30j])
    gamma50 = (z - 50) / (z + 50)
    gamma75 = renormalize_one_port(gamma50, 50, 75)
    np.testing.assert_allclose(gamma75, (z - 75) / (z + 75))
    s = np.zeros((2, 2, 2), dtype=complex)
    s[:, 0, 0] = gamma50
    s[:, 1, 1] = gamma50
    s75 = renormalize_two_port(s, 50, 75)
    np.testing.assert_allclose(s75[:, 0, 0], gamma75, atol=1e-12)


def test_fixture_z0_inactive_returns_same():
    data = SweepData(np.array([1.0]), np.array([0.1j]), np.array([0.5]))
    assert apply_fixture(data, FixtureSettings()) is data


def test_fixture_two_port_deembed():
    freq = np.linspace(1e6, 1e9, 11)
    a, dut, b = rand_s(), rand_s(), rand_s()
    meas = SweepData.from_s_matrix(freq, cascade(a, dut, b))
    settings = FixtureSettings(
        fixture1=SweepData.from_s_matrix(freq, a),
        fixture2=SweepData.from_s_matrix(freq, b),
    )
    out = apply_fixture(meas, settings)
    np.testing.assert_allclose(out.s_matrix(), dut, atol=1e-9)


# limits


def make_data():
    freq = np.linspace(2e9, 3e9, 101)
    s11 = np.full(101, 0.1 + 0j)  # -20 dB
    s11[50] = 0.5  # -6 dB spike at 2.5 GHz
    return SweepData(freq, s11, np.full(101, 0.9 + 0j))


def test_limits_pass_fail(tmp_path):
    spec = LimitSpec(
        "test",
        [
            LimitSegment("s11", "logmag", "upper", 2.0e9, 2.4e9, -10),
            LimitSegment("s11", "logmag", "upper", 2.4e9, 2.6e9, -10),
            LimitSegment("s21", "logmag", "lower", 2e9, 3e9, -3, -1),
            LimitSegment("s22", "logmag", "upper", 2e9, 3e9, -10),
        ],
    )
    res = spec.evaluate(make_data())
    assert not res.passed
    assert res.segments[0].passed
    assert not res.segments[1].passed
    assert res.segments[1].worst_freq == pytest.approx(2.5e9)
    assert res.segments[1].failed_points == 1
    assert res.segments[2].passed
    assert res.segments[3].skipped
    path = tmp_path / "spec.json"
    spec.save(path)
    again = LimitSpec.load(path)
    assert again.limits[2].value_stop == -1
    log = tmp_path / "log.csv"
    log_result(log, res, "SN1")
    log_result(log, res, "SN2")
    assert len(log.read_text().splitlines()) == 3
    assert "FAIL" in res.summary()


def test_limit_validation():
    with pytest.raises(ValueError):
        LimitSegment("s11", "logmag", "middle", 1, 2, 0)
    with pytest.raises(ValueError):
        LimitSegment("s11", "nonsense", "upper", 1, 2, 0)


# search


def test_search_functions():
    freq = np.linspace(0, 100, 101)
    y = -((freq - 50) ** 2) / 100  # peak 0 at 50
    assert search_max(y) == 50
    assert search_min(y) in (0, 100)
    f = search_target(freq, y, -1.0, 50, 1)
    assert f == pytest.approx(60, abs=0.1)
    bw = search_bandwidth(freq, y, -3)
    assert bw.low == pytest.approx(50 - math.sqrt(300), abs=0.1)
    assert bw.high == pytest.approx(50 + math.sqrt(300), abs=0.1)
    notch = search_bandwidth(freq, -y, -3, notch=True)
    assert notch.bandwidth == pytest.approx(bw.bandwidth)
    yy = np.sin(freq / 5)
    assert next_peak(yy, 0, 1) is not None
    assert next_peak(yy, 0, -1) is None


# matching


@pytest.mark.parametrize(
    "zl", [100 + 50j, 20 - 30j, 10 + 0j, 200 - 100j, 50 + 40j]
)
def test_l_networks_match(zl):
    sols = l_networks(zl, 100e6)
    assert sols
    for net in sols:
        assert input_impedance(net, zl) == pytest.approx(50, abs=1e-6)


# TDR


def test_tdr_locates_open_at_end_of_line():
    freq = np.linspace(0, 3e9, 1001)
    length = 1.5  # m, air line
    tau = 2 * length / 299_792_458
    s11 = np.exp(-2j * np.pi * freq * tau)
    td = transform(freq, s11, "kaiser6", 8192)
    assert td.peak_distance() == pytest.approx(length, abs=0.02)
    assert td.step[-1] == pytest.approx(1, abs=0.05)


def test_time_gate_removes_second_reflection():
    freq = np.linspace(10e6, 3e9, 801)
    t1, t2 = 2e-9, 12e-9
    first = 0.3 * np.exp(-2j * np.pi * freq * t1)
    second = 0.5 * np.exp(-2j * np.pi * freq * t2)
    gated = time_gate(freq, first + second, 0, 7e-9)
    mid = slice(100, 700)
    np.testing.assert_allclose(gated[mid], first[mid], atol=0.02)
    notched = time_gate(freq, first + second, 0, 7e-9, mode="notch")
    np.testing.assert_allclose(notched[mid], second[mid], atol=0.02)
    assert distance_to_time(1.0) == pytest.approx(6.671e-9, rel=1e-3)


# health


def test_health_checks():
    cal = Calibration()
    assert check_calibration(cal).severity == Severity.WARNING
    cal.load("tests/data/sol_27_30.cal")
    cal.calc_corrections()
    cal.created = datetime.now() - timedelta(hours=20)
    lo, hi = cal.freq_range()
    rep = check_calibration(cal, np.array([lo - 1e6, hi]))
    assert rep.severity == Severity.ERROR
    assert "old" in rep.summary()
    cal.created = datetime.now()
    rep = check_calibration(cal, np.linspace(lo, hi, 11))
    assert rep.severity == Severity.INFO
    assert verify_standard(np.full(5, 0.01 + 0j), "load").passed
    assert not verify_standard(np.full(5, 0.2 + 0j), "load").passed
    assert verify_standard(np.full(5, 0.99 + 0j), "open").passed


# cal kit library


def test_calkit_library(tmp_path):
    lib = CalKitLibrary(tmp_path)
    assert "Ideal" in lib.names()
    kit = CalKit(name="My kit", ideal=False, open_c0=50e-15, load_r=49.8)
    lib.save(kit)
    assert lib.get("My kit").load_r == 49.8
    with pytest.raises(ValueError):
        lib.save(BUILTIN_KITS[0])
    cal = Calibration()
    kit.apply_to(cal.cal_element)
    assert cal.cal_element.open_state == "COEFF"
    assert cal.cal_element.open_c0 == 50e-15
    back = CalKit.from_element(cal.cal_element, "x")
    assert back.load_r == 49.8
    lib.delete("My kit")
    assert "My kit" not in lib.names()


# sweep data


def test_sweepdata_roundtrip(tmp_path):
    freq = np.linspace(1e6, 1e8, 5)
    s = rand_s(5)
    data = SweepData.from_s_matrix(freq, s)
    path = tmp_path / "x.s2p"
    data.save(str(path))
    back = SweepData.load(str(path))
    np.testing.assert_allclose(back.s_matrix(), s, atol=1e-12)
    data.save(str(tmp_path / "x.s1p"))
    one = SweepData.load(str(tmp_path / "x.s1p"))
    assert not one.is_full_two_port
    np.testing.assert_allclose(gamma_to_z(np.array([0j])), [50])
