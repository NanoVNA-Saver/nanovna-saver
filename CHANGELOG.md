v0.3.3
======

- Fixed data acquisition with S-A-A-2 / NanoVNA V2
- Refactored calibration code
- Calibration data between known datapoints in now
  interpolated by spline interpolation
- Fixed through calibration 

v0.3.2
======

- fixed crash with averaging sweeps
  also averaging now discards reading by geometrical distance

v0.3.1
======

- fixed crash with calibration assistant

v0.3.0
======

- Support for S-A-A-2 / NanoVNA V2
- Support for 202 Datapoints/scan with NanoVNA-H
- Support for attenuator at S11
- Massive code separation to easy additon of
  Hardware, Charts, Analysis ...

Known Issues
------------

- -H / -H4 supports depends on Firmware

