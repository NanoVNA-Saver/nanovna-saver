Changelog
=========

0.5.4-pre
---------

 - simplyfied sweep worker
 - fixed calibration data loading
 - explicit import of scipy functions - #555
 - bugfix for python3.8 compatability
 - refactoring of Analysis modules

0.5.3
-----

 - Int casts due to python 3.10 extension interface changes
 - Pycodestyle changes

0.5.2
-----

 - Using more integer divisions to get right type for QPainter
   points

0.5.1
-----

 - fixed crashing polar charts on python3.10  #528 (#539)

0.5.0
-----

 - Fix crash on open in use serial device
 - Use a Defaults module for all settings -
   ignores old .ini settings
 - Refactoring and unifying Chart classes
 - No more automatic update checks (more privacy)
 - Corrected error handling in NanaVNA\_V2 code 

0.4.0
-----

 - PA0JOZ Enhanced Response Correction
 - Fix linux binary build
 - Many bugfixes

v0.3.10
------

- Default Band ranges for 5 and 9cm
- Layout should fit on smaller screens
- Fixed fixed axis settings
- Show VNA type in port selector
- Recognise tinySA (screenshot only)
- Some more cables in TDR
- Reference plane applied after calibration
- Calibration fixes by DiSlord

v0.3.9
------

- TX Power on V2
- New analysis
- Magnitude Z Chart
- VSWR Chart improvements

v0.3.8
------

- Allow editing of bands above 2.4GHz
- Restore column layout on start
- Support for Nanovna-F V2
- Fixes a crash with S21 hack

v0.3.7
------

- Added a delta marker
- Segments can now have exponential different step widths
  (see logarithmic sweeping)
- More different data points selectable
  (shorter are useful on logarithmic sweeping)
- Scrollable marker column
- Markers initialize on start, middle, end
- Frequency input is now more "lazy"
  10m, 50K and 1g are now valid for 10MHz, 50kHz and 1GHz
- Added a wavelength field to Markers
- 32 bit windows binaries build in actions
- Stability improvements due to better exception handling
- Workaround for wrong first S21mag value on V2 devices

v0.3.6
------

- Implemented bandwidth setting in device management

v0.3.5
------

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
------

- Refactored Analysis
- Add Antenna Analysis
- Fixed bug in Through Calibration
- Fixed bug in s2p saving
- Fixed crash when clicking connect with no device connected
- Fixed module error with source installation if
  pkg\_resources missing

v0.3.3
------

- Fixed data acquisition with S-A-A-2 / NanoVNA V2
- Refactored calibration code
- Calibration data between known datapoints in now
  interpolated by spline interpolation
- Fixed through calibration

v0.3.2
------

- fixed crash with averaging sweeps
  also averaging now discards reading by geometrical distance

v0.3.1
------

- fixed crash with calibration assistant

v0.3.0
------

- Support for S-A-A-2 / NanoVNA V2
- Support for 202 Datapoints/scan with NanoVNA-H
- Support for attenuator at S11
- Massive code separation to easy additon of
  Hardware, Charts, Analysis ...

Known Issues
------------

- -H / -H4 supports depends on Firmware
