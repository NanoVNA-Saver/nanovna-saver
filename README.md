NanoVNASaver
============
A small tool to save touchstone files from the NanoVNA, and to allow sweeping frequency spans in sections to gain more than 101 data points.

Copyright 2019 Rune B. Broberg

### Introduction
This software connects to a NanoVNA and extracts the data for display on a computer, and for saving to Touchstone files.

Current features:
- Reading data from a NanoVNA
- Splitting a frequency range into multiple segments to increase resolution (tried up to >10k points)
- Displaying data on Smith charts and LogMag-charts for both S11 and S21
- Displaying two markers, and the impedance and VSWR (against 50 ohm) at these locations
- Exporting 1-port and 2-port Touchstone files
- TDR function (measurement of cable length)
- Reading and displaying Touchstone files as reference traces

Expected features:
- Mouse control of markers
- Further data readout for markers, such as return loss/forward gain

0.0.3:
![Screenshot of version 0.0.3](https://i.imgur.com/Cyp4gax.png)
0.0.2:
![Screenshot of version 0.0.2](https://i.imgur.com/eoLwv35.png)
0.0.1:
![Screenshot of version 0.0.1](https://i.imgur.com/kcCC2eK.png)

### Windows

The software was written in Python on Windows, using Pycharm, and the modules PyQT5, numpy and pyserial.

### Linux

In order to run this app in Linux environment, you'll need the following packages:

* `python3-serial`
* `python3-pyqt5`
* `numpy`

### Installation and Use with pip

1. Clone repo and cd into the directory 
   - `git clone https://github.com/mihtjel/nanovna-saver`
   - `cd nanovna-saver`

2. Run the pip installation

    `pip install .`
    
2. Once completed run with the following command

    `NanoVNASaver` 

### Using the software

Connect your NanoVNA to a serial port, and enter this serial port in the serial port box. Click "Open serial" to connect.

The app can collect multiple sweeps to get more accurate measurements. Enter the number of sweeps to be done in the
sweep count box. Each sweep is 101 data points, and takes about 1.5 seconds to complete.

Marker frequencies are entered in Hz. Press enter after typing the frequency for it to take effect.

To get accurate TDR measurements, calibrate the device, and attach the cable to be measured at the calibration plane -
ie. at the same position where the calibration load would be attached.

### License
This software is licensed under version 3 of the GNU General Public License. It comes with NO WARRANTY.

You can use it, commercially as well. You may make changes to the code, but I (and the license) ask that you give these changes back to the community.

### Credits
Original application by Rune B. Broberg (5Q5R)

TDR inspiration shamelessly stolen from the work of Salil (VU2CWA) at https://nuclearrambo.com/wordpress/accurately-measuring-cable-length-with-nanovna/

Thanks to everyone who have tested, commented and inspired.