v0.3.7
======

- Added a delta marker
- Segments can now have exponential different step widths
  (see logarithmic sweeping)
- More different data points selectable
  (shorter are useful on logarithmic sweeping)
- Scrollable marker column
- Markers initialize on start, middle, end
- Added a wavelength field to Markers 
- 32 bit windows binaries build in actions
- Stability improvements due to better exception handling


v0.3.6
======

- Implemented bandwidth setting in device management

v0.3.5
======

- Sweep worker now initializes full dataset on setting changes.
  Therefore no resize of charts when doing multi segment sweep
- Changing datapoints in DeviceSettings are reflected in SweepSettings widget step size
- Simplified calibration code by just using scipy.interp1d with fill\_value
- Established Interface class to ease locking and allow non usb connections in future
- Cleaned up VNA code. Added some pause statements to get more robust readings
- Added MagLoopAnalysis
- Touchstone class can now generate interpolated Datapoints for a given frequency
  Will be usefull in future analysis code
- Fixed a bug in Version comparison


v0.3.4
======

- Refactored Analysis
- Add Antenna Analysis
- Fixed bug in Through Calibration
- Fixed bug in s2p saving
- Fixed crash when clicking connect with no device connected
- Fixed module error with source installation if
  pkg\_resources missing

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

