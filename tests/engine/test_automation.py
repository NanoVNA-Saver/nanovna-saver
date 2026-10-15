import base64
import json
import os
import socket
import urllib.request

import numpy as np
import pytest

from NanoVNASaver.engine.cli import EXIT_ERROR, EXIT_FAIL, EXIT_PASS, main
from NanoVNASaver.engine.limits import LimitSegment, LimitSpec
from NanoVNASaver.engine.sequence import Sequence
from NanoVNASaver.engine.server import ApiServer, ws_read_frame
from NanoVNASaver.engine.session import VNASession
from NanoVNASaver.engine.sweepdata import SweepData
from NanoVNASaver.Hardware.VirtualVNA import demo_filter

START, STOP = 300e6, 600e6


@pytest.fixture
def session():
    with VNASession("virtual:demo") as s:
        s.device.sweep_delay_per_point = 0
        s.device.noise = 0.0
        yield s


def calibrate(session: VNASession) -> None:
    for std in ("short", "open", "load", "isolation", "thru"):
        session.device.set_standard(std)
        session.capture_standard(std, START, STOP, segments=2)
    session.device.set_standard("dut")
    session.apply_calibration("Ideal")


def test_session_scripted_calibration_and_full_two_port(session, tmp_path):
    calibrate(session)
    assert session.calibration.isValid2Port()

    def flip():
        session.device.reversed = True

    data = session.full_two_port(START, STOP, flip, segments=2)
    truth = demo_filter(data.freq)
    np.testing.assert_allclose(data.s_matrix(), truth, atol=1e-6)
    assert len(data) == 2 * session.device.datapoints

    cal_file = tmp_path / "x.cal"
    session.save_calibration(cal_file)
    other = VNASession("virtual:demo").connect()
    other.load_calibration(cal_file)
    assert other.calibration.isCalculated
    info = session.info()
    assert info["name"] == "Virtual VNA"


def test_session_points_validation(session):
    with pytest.raises(ValueError):
        session.set_points(123)
    session.set_points(201)
    data = session.sweep(START, STOP, averages=2, truncates=0)
    assert len(data) == 201


def write_limits(path, value=-6.0) -> str:
    LimitSpec(
        "filter",
        [LimitSegment("s21", "logmag", "lower", 420e6, 450e6, value)],
    ).save(path)
    return str(path)


def test_sequence_run(session, tmp_path):
    limits = write_limits(tmp_path / "limits.json")
    seq_file = tmp_path / "seq.json"
    seq_file.write_text(
        json.dumps(
            {
                "name": "Filter test",
                "sweep": {"start": START, "stop": STOP, "segments": 2},
                "processing": {"smoothing": 0.5},
                "limits": "limits.json",
                "steps": [
                    {"action": "prompt", "message": "Connect {serial}"},
                    {"action": "sweep"},
                    {"action": "check"},
                    {"action": "save", "path": "out/{serial}.s2p"},
                    {"action": "report", "path": "out/{serial}.html"},
                    {"action": "log", "path": "out/log.csv"},
                ],
            }
        )
    )
    prompts = []
    result = Sequence.load(seq_file).run(session, "SN1", prompts.append)
    assert prompts == ["Connect SN1"]
    assert result.verdict == "PASS"
    assert (tmp_path / "out/SN1.s2p").exists()
    assert "PASS" in (tmp_path / "out/SN1.html").read_text("utf-8")
    assert "SN1" in (tmp_path / "out/log.csv").read_text("utf-8")
    assert limits


def test_sequence_rejects_unknown_action():
    with pytest.raises(ValueError):
        Sequence({"steps": [{"action": "explode"}]})


def test_cli_sweep_pass_fail(tmp_path, capsys):
    good = write_limits(tmp_path / "good.json", -6.0)
    bad = write_limits(tmp_path / "bad.json", 5.0)
    out = tmp_path / "dut.s2p"
    args = ["sweep", "--start", "300M", "--stop", "600M", "-s", "2"]
    assert main([*args, "--limits", good, "--out", str(out)]) == EXIT_PASS
    assert SweepData.load(str(out)).freq[0] == pytest.approx(300e6)
    assert main([*args, "--limits", bad]) == EXIT_FAIL
    assert "FAIL" in capsys.readouterr().out
    assert main(["check", str(out), "--limits", good]) == EXIT_PASS
    assert main(["check", str(tmp_path / "missing.s1p")]) == EXIT_ERROR


def test_cli_run_sequence(tmp_path):
    write_limits(tmp_path / "limits.json")
    seq = tmp_path / "seq.json"
    seq.write_text(
        json.dumps(
            {
                "device": "virtual:ideal",
                "sweep": {"start": START, "stop": STOP},
                "limits": "limits.json",
                "steps": [{"action": "sweep"}, {"action": "check"}],
            }
        )
    )
    assert main(["run", str(seq), "--yes"]) == EXIT_PASS


def http(method, url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_rest_and_websocket(session):
    server = ApiServer(session, "127.0.0.1", 0).start()
    host, port = server.address
    base = f"http://{host}:{port}"
    try:
        status, body = http("GET", f"{base}/api/info")
        assert status == 200
        assert json.loads(body)["name"] == "Virtual VNA"
        assert http("GET", f"{base}/api/last")[0] == 404

        # websocket client
        sock = socket.create_connection((host, port), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall(
            (
                f"GET /ws HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        response = b""
        while b"\r\n\r\n" not in response:
            response += sock.recv(1)
        assert b"101" in response.split(b"\r\n")[0]

        status, body = http(
            "POST", f"{base}/api/sweep", {"start": START, "stop": STOP}
        )
        assert status == 200
        sweep = json.loads(body)
        assert len(sweep["freq"]) == session.device.datapoints
        opcode, payload = ws_read_frame(sock)
        assert opcode == 1
        pushed = json.loads(payload)
        assert pushed["type"] == "sweep"
        assert pushed["freq"] == sweep["freq"]
        sock.close()

        spec = LimitSpec(
            "x", [LimitSegment("s21", "logmag", "lower", 420e6, 450e6, -60)]
        ).to_dict()
        status, body = http("POST", f"{base}/api/check", {"limits": spec})
        assert status == 200
        assert json.loads(body)["passed"] is True
        status, body = http("GET", f"{base}/api/touchstone?ports=2")
        assert status == 200
        assert body.startswith(b"# HZ S RI R 50")
        assert http("POST", f"{base}/api/sweep", {"start": 1})[0] == 400
        assert http("GET", f"{base}/api/nope")[0] == 404
    finally:
        server.stop()


def test_shipped_examples_pass(tmp_path):
    import shutil
    from pathlib import Path

    examples = Path(__file__).parents[2] / "examples"
    for name in ("sequence_example.json", "limits_example.json"):
        shutil.copy(examples / name, tmp_path / name)
    seq = Sequence.load(tmp_path / "sequence_example.json")
    with VNASession("virtual:ideal") as session:
        result = seq.run(session, "T1")
    assert result.verdict == "PASS", result.limit_result.summary()
    assert (tmp_path / "results" / "results.csv").exists()
