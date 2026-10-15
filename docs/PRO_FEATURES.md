# NanoVNA-Saver Pro features

This fork adds bench-top VNA style measurement features, production test
automation and a simulated device on top of NanoVNA-Saver. Everything below
works with real hardware and with the **Virtual VNA** (port `Virtual VNA
(demo)` in the port list, always available).

## Faster core

* Sweeps are processed as numpy arrays: raw → calibration → fixture removal →
  running average → smoothing. Calibration correction is ~200× faster than
  before at 10 000 points (identical results).
* Charts are redrawn at most every 50 ms, independent of the segment count.
* NanoVNA-H/H4 firmware with `scan_bin` (DiSlord) is read in binary, one scan
  per segment for frequencies and both channels. Other firmware ≥ 0.7.1 uses
  one text scan per segment instead of two. If binary data looks wrong the
  driver falls back to text automatically.
* Connecting to a device no longer blocks the user interface.

## Trace processing (Sweep settings → Trace processing)

* **Smoothing aperture** – moving average across frequency, in percent of the
  span, applied to the complex data (magnitude, phase and Smith stay
  consistent).
* **Running average** – in continuous mode every new sweep is blended into the
  trace with weight 1/N; noise settles immediately instead of after N sweeps.
* The active processing is shown in the top right corner of every chart
  (e.g. `Avg 3/8 · Smo 2% · PortExt`). Processing also applies to exported
  files.

## Calibration (Calibration window)

* **Cal kit library** – builtin kits plus your own kits stored as JSON
  (`%APPDATA%/NanoVNASaver/calkits` on Windows,
  `~/.local/share/NanoVNASaver/calkits` elsewhere). *Use kit* fills the
  coefficient fields, *Save fields as kit* stores the current fields,
  import/export to share kits.
* **Health** – warns when the sweep exceeds the calibrated range
  (extrapolation), when the calibration is older than 8 h and when error terms
  are interpolated. *Verify load/open/short* checks a re-measured standard
  (load must show > 30 dB return loss).
* Calibration standards are always captured from the raw data, even when a
  calibration, fixture or smoothing is active.
* Calibration files store their creation time (`! Created: ...`).

## Fixture / Z0 window

* **Port extension** per port: delay (ps) and loss (dB at 1 GHz, scaled with
  √f). *Auto (open)* / *Auto (short)* fit port 1 from a measurement of the
  open/short at the end of the fixture, *Auto (thru)* fits port 2 from S21 of
  a through.
* **De-embedding** of measured 2-port fixtures (`.s2p`) at port 1 and port 2.
  With full 2-port data the de-embedding is exact (T-parameters); with forward
  data S11 is exact and S21 is corrected for the fixture transmission.
* **Reference impedance** – renormalises S-parameters to any Z0 (e.g. 75 Ω);
  Smith chart, VSWR, impedance and marker readouts follow.

## Full 2-port window

NanoVNAs only measure forward (S11, S21). Measure forward, turn the DUT
around, measure again, combine: with a full 2-port calibration (short, open,
load, isolation, through) the result is a fully error corrected S-matrix
(including load match). Without it a 1-port / response corrected
approximation is used. Save as `.s2p`; *Files → Save 2-port* also writes the
measured S12/S22.

## Traces & limits window

* 4 traces, each with its own parameter (S11, S21, S12, S22, gated S11) and
  format: log/lin magnitude, phase, unwrapped phase, group delay (adjustable
  aperture), VSWR, real/imag, R, X, |Z|, series L/C, Q, Smith, polar.
* **Memory**: *Data → Memory*, then per trace *Data + Mem*, *Data / Mem*,
  *Data − Mem*.
* **Markers** M1–M4, drag them in any rectangular trace. Search: min, max,
  next peak left/right, target value, bandwidth (−3 dB or any level, peak or
  notch) with center frequency and Q. *Track* repeats min/max on every sweep.
* **Limit lines** from a JSON file (see below) with a large PASS / FAIL
  banner; optional CSV log of every finished sweep.
* **HTML report** with verdict, limit table, charts (inline SVG) and
  measurement metadata – print to PDF from the browser if needed.

## Matching window

L-network solutions (series/shunt L and C values) that match the load
impedance at a frequency (or marker 1, or a manually entered impedance) to
the reference impedance.

## TDR window: time gate

Enable the gate, set start/stop distance (velocity factor applied), choose
band pass (keep) or notch (remove). The gated S11 is available as trace
parameter *S11 gated* and can be shown as reference trace in all charts.

## Virtual VNA

* `virtual:demo` – band pass filter DUT (435 MHz) with a realistic error
  model and noise.
* `virtual:antenna` – dual band (145/435 MHz) antenna.
* `virtual:ideal` – no error model, no noise.
* `virtual:<file.s1p|s2p>` – replays a Touchstone file as DUT.

The calibration assistant switches the virtual standards automatically; the
full 2-port window reverses the virtual DUT automatically.

## Command line: `nanovna-pro`

Exit code 0 = pass (or no limits), 1 = fail, 2 = error.

```
nanovna-pro ports
nanovna-pro sweep -d COM3 --start 1G --stop 3G -n 101 -s 4 \
    --cal antenna.cal --limits examples/limits_example.json \
    --out dut.s1p --report dut.html --serial SN042 --log results.csv
nanovna-pro check measured.s2p --limits filter.json --report filter.html
nanovna-pro run examples/sequence_example.json --serial SN042
nanovna-pro serve -d virtual:demo --port 8765
```

Sweep options: `--smooth PCT`, `--z0`, `--port1-delay PS`,
`--port1-loss DB`, `--port2-delay`, `--port2-loss`, `--kit NAME|file.json`,
`-a/--averages`, `--log-sweep`.

## Python API

```python
from NanoVNASaver.engine.session import VNASession

with VNASession("virtual:demo") as vna:          # or "COM3"
    vna.load_calibration("antenna.cal")          # kit="Ideal" by default
    data = vna.sweep(300e6, 600e6, points=101, segments=4)
    print(vna.check("examples/limits_example.json").summary())
    data.save("dut.s1p")

    # scripted calibration
    for std in ("short", "open", "load", "isolation", "thru"):
        input(f"connect {std}")
        vna.capture_standard(std, 300e6, 600e6, segments=4)
    vna.apply_calibration("Ideal")
    vna.save_calibration("new.cal")
```

`SweepData` holds `freq`, `s11`, `s21` (and `s12`, `s22` after a full 2-port
measurement) as numpy arrays. The math is in `NanoVNASaver.engine`
(`deembed`, `dsp`, `formats`, `limits`, `matching`, `search`, `tdr`,
`report`).

## REST / WebSocket API (`nanovna-pro serve`)

Binds to 127.0.0.1 by default (no authentication – do not expose it).

| Method | Path | Body / result |
| --- | --- | --- |
| GET | `/api/info` | device information |
| POST | `/api/sweep` | `{"start", "stop", "points", "segments", "averages", "smoothing"}` → `{"freq": [...], "s11": {"re": [...], "im": [...]}, "s21": ...}` |
| GET | `/api/last` | last sweep |
| GET | `/api/touchstone?ports=1\|2` | last sweep as Touchstone text |
| POST | `/api/check` | `{"limits": <limit spec>}` → pass/fail per segment |
| POST | `/api/continuous` | `{"enabled": true, "start", "stop", ...}` |
| GET | `/ws` | WebSocket, pushes `{"type": "sweep", ...}` for every sweep |

## File formats

Limit spec (`examples/limits_example.json`): `type` is `upper` (value must be
≤ limit) or `lower`; `value_stop` makes a sloped limit; `format` is one of
`logmag, linmag, phase, uphase, gdelay, vswr, real, imag, r, x, zmag, serl,
serc, q`.

Test sequence (`examples/sequence_example.json`): actions `prompt`, `sweep`,
`sweep2port`, `check`, `save`, `report`, `log`. Paths are relative to the
sequence file; placeholders `{serial}`, `{timestamp}`, `{date}`, `{name}`.

## Not covered / limitations

* The binary scan path follows the DiSlord firmware format but has only been
  tested against an emulated device – verify on your hardware (the driver
  falls back to text scanning if anything is inconsistent).
* The legacy charts of the main window are unchanged (QPainter); the new
  pyqtgraph display is the *Traces & limits* window.
* Complex reference impedances are supported by the engine API, the GUI
  accepts real values.
