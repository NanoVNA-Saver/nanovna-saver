import numpy as np
import pytest

from NanoVNASaver.Calibration import (
    Calibration,
    correct_full_two_port,
    solve_one_port,
)
from NanoVNASaver.RFTools import Datapoint

RNG = np.random.default_rng(42)
N = 51
FREQ = np.linspace(1e6, 1e9, N)


def rand_c(scale=0.1, offset=0.0):
    return offset + scale * (RNG.normal(size=N) + 1j * RNG.normal(size=N))


def error_terms():
    e00 = rand_c(0.05)
    e11 = rand_c(0.05)
    e10e01 = rand_c(0.05, 0.9)
    e22 = rand_c(0.05)
    e10e32 = rand_c(0.05, 0.8)
    e30 = rand_c(0.001)
    return {
        "e00": e00,
        "e11": e11,
        "e10e01": e10e01,
        "delta_e": e00 * e11 - e10e01,
        "e22": e22,
        "e10e32": e10e32,
        "e30": e30,
    }


def measure_1port(t, gamma):
    return t["e00"] + t["e10e01"] * gamma / (1 - t["e11"] * gamma)


def measure_fwd(t, s11, s21, s12, s22):
    """12 term forward model"""
    ds = s11 * s22 - s21 * s12
    den = 1 - t["e11"] * s11 - t["e22"] * s22 + t["e11"] * t["e22"] * ds
    s11m = t["e00"] + t["e10e01"] * (s11 - t["e22"] * ds) / den
    s21m = t["e30"] + t["e10e32"] * s21 / den
    return s11m, s21m


def make_cal(t, two_port=True):
    cal = Calibration()
    for name, gamma in (("short", -1), ("open", 1), ("load", 0)):
        m = measure_1port(t, np.full(N, gamma, dtype=complex))
        cal.insert(
            name,
            [
                Datapoint(int(f), v.real, v.imag)
                for f, v in zip(FREQ, m, strict=False)
            ],
        )
    if two_port:
        one = np.ones(N, dtype=complex)
        zero = np.zeros(N, dtype=complex)
        thrurefl, through = measure_fwd(t, zero, one, one, zero)
        for name, m in (
            ("through", through),
            ("thrurefl", thrurefl),
            ("isolation", t["e30"]),
        ):
            cal.insert(
                name,
                [
                    Datapoint(int(f), v.real, v.imag)
                    for f, v in zip(FREQ, m, strict=False)
                ],
            )
    cal.cal_element.short_state = "IDEAL"
    cal.cal_element.open_state = "IDEAL"
    cal.cal_element.load_state = "IDEAL"
    cal.calc_corrections()
    return cal


def test_one_port_recovers_dut():
    t = error_terms()
    cal = make_cal(t, two_port=False)
    dut = rand_c(0.3)
    corrected = cal.correct11_array(FREQ.astype(int), measure_1port(t, dut))
    np.testing.assert_allclose(corrected, dut, atol=1e-9)


def test_scalar_api_matches_array_api():
    t = error_terms()
    cal = make_cal(t, two_port=False)
    m = measure_1port(t, np.full(N, 0.2 + 0.1j))
    dp = Datapoint(int(FREQ[3]), m[3].real, m[3].imag)
    res = cal.correct11(dp)
    assert res.z == pytest.approx(0.2 + 0.1j, abs=1e-9)


def test_full_two_port_by_reversal():
    t = error_terms()
    cal = make_cal(t, two_port=True)
    s11, s22 = rand_c(0.3), rand_c(0.3)
    s21, s12 = rand_c(0.1, 0.5), rand_c(0.1, 0.4)
    s11m, s21m = measure_fwd(t, s11, s21, s12, s22)
    # DUT flipped: VNA sees S22 at port 1 and S12 as transmission
    s22m, s12m = measure_fwd(t, s22, s12, s21, s11)
    r11, r21, r12, r22 = cal.correct_two_port_array(
        FREQ.astype(int), s11m, s21m, s12m, s22m
    )
    for got, want in ((r11, s11), (r21, s21), (r12, s12), (r22, s22)):
        np.testing.assert_allclose(got, want, atol=1e-9)


def test_enhanced_response_exact_for_matched_load():
    t = error_terms()
    t["e22"] = np.zeros(N, dtype=complex)
    cal = make_cal(t, two_port=True)
    s11, s21 = rand_c(0.3), rand_c(0.1, 0.5)
    s11m, s21m = measure_fwd(t, s11, s21, s21, np.zeros(N, dtype=complex))
    r21 = cal.correct21_array(FREQ.astype(int), s21m, s11m)
    np.testing.assert_allclose(r21, s21, atol=1e-9)


def test_interpolation_holds_edges():
    t = error_terms()
    cal = make_cal(t, two_port=False)
    terms = cal.terms_at([0, 1e6, 5e9])
    assert terms["e00"][0] == terms["e00"][1]
    assert terms["e00"][2] == pytest.approx(t["e00"][-1])


def test_identical_standards_raise():
    cal = Calibration()
    for name in ("short", "open", "load"):
        cal.insert(name, [Datapoint(1000, 0.5, 0.5)])
    with pytest.raises(ValueError):
        cal.calc_corrections()


def test_solve_one_port_shapes():
    g = np.array([-1, 1, 0], dtype=complex)
    e00, e11, de = solve_one_port(
        np.array([-0.9]), np.array([0.95]), np.array([0.01]), *g[:, None]
    )
    assert e00.shape == (1,)


def test_correct_full_two_port_identity():
    one = np.ones(3, dtype=complex)
    zero = np.zeros(3, dtype=complex)
    terms = {
        "e00": zero,
        "e11": zero,
        "e10e01": one,
        "e30": zero,
        "e22": zero,
        "e10e32": one,
    }
    s = (0.1 * one, 0.9 * one, 0.8 * one, 0.2 * one)
    for got, want in zip(correct_full_two_port(terms, *s), s, strict=False):
        np.testing.assert_allclose(got, want)


def test_legacy_file_calibration(tmp_path):
    cal = Calibration()
    cal.load("tests/data/sol_27_30.cal")
    cal.calc_corrections()
    assert cal.isCalculated
    assert cal.created is not None
    out = tmp_path / "x.cal"
    cal.save(str(out))
    cal2 = Calibration()
    cal2.load(str(out))
    assert cal2.created == cal.created.replace(microsecond=0)
