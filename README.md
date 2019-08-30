NanoVNASaver
============
A small tool to save touchstone files from the NanoVNA, and to allow sweeping frequency spans in sections to gain more than 101 data points.

Copyright 2019 Rune B. Broberg

### Introduction
This software connects to a NanoVNA and extracts the data for display on a computer, and for saving to Touchstone files.

Current features:
- Reading data from a NanoVNA
- Splitting a frequency range into multiple segments to increase resolution (tried up to >10k points)
- Displaying data on Smith charts and logmag-charts for both S11 and S21
- Displaying two markers, and the impedance and VSWR (against 50 ohm) at these locations
- Exporting S11 touchstone files

Expected features:
- 2-port Touchstone files
- Mouse control of markers
- Further data readout for markers, such as return loss
- TDR function (very important in this community ;-)
- Reading and displaying Touchstone files

![Screenshot of version 0.0.1](https://i.imgur.com/kcCC2eK.png)

### Windows

The software was written in Python on Windows, using Pycharm, and the modules PyQT5 and pyserial.

### Linux

In order to run this app in Linux environment, you'll need the following packages:

* `python3-serial`
* `python3-pyqt5`

### To Run

```sh
python3 nanovna-saver.py
```

### License
This software is licensed under version 3 of the GNU General Public License. It comes with NO WARRANTY.

You can use it, commercially as well. You may make changes to the code, but I (and the license) ask that you give these changes back to the community.
