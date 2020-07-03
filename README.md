[![Latest Release](https://img.shields.io/github/v/release/NanoVNA-Saver/nanovna-saver.svg)](https://github.com/NanoVNA-Saver/nanovna-saver/releases/latest)
[![License](https://img.shields.io/github/license/NanoVNA-Saver/nanovna-saver.svg)](https://github.com/NanoVNA-Saver/nanovna-saver/blob/master/LICENSE)
[![Downloads](https://img.shields.io/github/downloads/NanoVNA-Saver/nanovna-saver/total.svg)](https://github.com/NanoVNA-Saver/nanovna-saver/releases/)
[![GitHub Releases](https://img.shields.io/github/downloads/NanoVNA-Saver/nanovna-saver/latest/total)](https://github.com/NanoVNA-Saver/nanovna-saver/releases/latest)
[![Donate](https://img.shields.io/badge/paypal-donate-yellow.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=T8KTGVDQF5K6E&item_name=NanoVNASaver+Development&currency_code=EUR&source=url)

NanoVNASaver
============

A multiplatform tool to save Touchstone files from the NanoVNA, 
sweep frequency spans in segments to gain more than 101 data
points, and generally display and analyze the resulting data.

 - Copyright 2019, 2020 Rune B. Broberg 
 - Copyright 2020 NanoVNA-Saver Authors

# Latest Changes 

## Changes in v0.3.4
- Refactored Analysis
- Add Antenna Analysis
- Fixed bug in Through Calibration
- Fixed bug in s2p saving
- Fixed crash when clicking connect with no device connected
- Fixed module error with source installation if
  pkg\_resources missing
  
## Changes in v0.3.3
- Fixed data acquisition with S-A-A-2 / NanoVNA V2
- Refactored calibration code
- Calibration data between known datapoints is now 
  interpolated using spline interpolation
- Fixed Through Calibration (CH0 -> CH1)

## Changes in v0.3.2
- This adds support for the SAA2, a VNA  loosely based on the
  original NanoVNA  with frequency range up to 3GHz. 
- Added ability to add use an attenuator and add the Antenuation 
  in s11 sweep settings for amplifier measurements.


# Introduction 
This software connects to a NanoVNA and extracts the data for
display on a computer and allows saving the sweep data to Touchstone files.

Current features:
- Reading data from a NanoVNA -- Compatible devices: NanoVNA, NanoVNA-H,
  NanoVNA-H4, NanoVNA-F, AVNA via Teensy
- Splitting a frequency range into multiple segments to increase resolution
  (tried up to >10k points)
- Averaging data for better results particularly at higher frequencies
- Displaying data on multiple chart types, such as Smith, LogMag, Phase and
  VSWR-charts, for both S11 and S21
- Displaying markers, and the impedance, VSWR, Q, equivalent
  capacitance/inductance etc. at these locations
- Displaying customizable frequency bands as reference, for example amateur
  radio bands
- Exporting and importing 1-port and 2-port Touchstone files
- TDR function (measurement of cable length) - including impedance display
- Filter analysis functions for low-pass, high-pass, band-pass and band-stop
  filters
- Display of both an active and a reference trace
- Live updates of data from the NanoVNA, including for multi-segment sweeps
- In-application calibration, including compensation for non-ideal calibration
  standards
- Customizable display options, including "dark mode"
- Exporting images of plotted values

0.1.4:
![Screenshot of version 0.1.4](https://i.imgur.com/ZoFsV2V.png)

## Running the application

The software was written in Python on Windows, using Pycharm, and the modules
PyQT5, numpy, scipy and pyserial.

#### Binary releases
You can find 64bit binary releases for Windows, Linux and MacOS under
https://github.com/NanoVNA-Saver/nanovna-saver/releases/

### Windows
Versions older than Windows 7 are not known to work.  

#### Windows 7
It requires Service Pack 1 and [Microsoft VC++ Redistributable] 
(https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads).
For most users, this would already be installed.

#### Windows 10
The downloadable executable runs directly, and requires no installation. 

##### Installation and Use with pip

1. Clone repo and cd into the directory

        git clone https://github.com/NanoVNA-Saver/nanovna-saver
        cd nanovna-saver

2. Run the pip installation

        pip3 install .

3. Once completed run with the following command

        NanoVNASaver

### Linux
#### Ubuntu 18.04 & 19.04
##### Installation and Use with pip
1. Install python3.7 and pip

        sudo apt install python3.7 python3-pip

3. Clone repo and cd into the directory 
		
        git clone https://github.com/NanoVNA-Saver/nanovna-saver
        cd nanovna-saver

4. Update pip and run the pip installation

        python3.7 -m pip install -U pip
        python3.7 -m pip install .
    
(You may need to install the additional packages python3-distutils,
python3-setuptools and python3-wheel for this command to work on some
distributions.)
    
5. Once completed run with the following command

        python3.7 nanovna-saver.py
    
    
### Mac OS:
#### MacPorts

Via a MacPorts distribution maintained by @ra1nb0w.

1. Install MacPorts following the 
   [install guide](https://www.macports.org/install.php)
2. Install NanoVNASaver :

        sudo port install NanoVNASaver

3. Now you can run the software from shell `NanoVNASaver` or run as app
   `/Applications/MacPorts/NanoVNASaver.app`

#### Homebrew
1. Install Homebrew
             From : https://brew.sh/

	     /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

2. Python :

        brew install python

3. NanoVNASaver Installation

        git clone git clone https://github.com/NanoVNA-Saver/nanovna-saver
        cd nanovna-saver
        
4. Install local pip packages

        python3 -m pip install .
        NanoVNASaver

## Using the software

Connect your NanoVNA to a serial port, and enter this serial port in the serial
port box.  If the NanoVNA is connected before the application starts, it should
be automatically detected. Otherwise, click "Rescan". Click "Connect to device"
to connect.

The app can collect multiple segments to get more accurate measurements. Enter
the number of segments to be done in the "Segments" box. Each segment is 101
data points, and takes about 1.5 seconds to complete.

Frequencies are entered in Hz, or suffixed with k or M.  Scientific notation
(6.5e6 for 6.5MHz) also works.

Markers can be manually entered, or controlled using the mouse. For mouse
control, select the active marker using the radio buttons, or hold "shift"
while clicking to drag the nearest marker. The marker readout boxes show the
actual frequency where values are measured.  Marker readouts can be hidden
using the "hide data" button when not needed.

Display settings are available under "Display setup". These allow changing the
chart colours, the application font size and which graphs are displayed.  The
settings are saved between program starts.

### Calibration
_Before using NanoVNA-Saver, please ensure that the device itself is in a
reasonable calibration state._ A calibration of both ports across the entire
frequency span, saved to save slot 0, is sufficient.  If the NanoVNA is
completely uncalibrated, its readings may be outside the range accepted by the
application.

In-application calibration is available, either assuming ideal standards or
with relevant standard correction. To manually calibrate, sweep each standard
in turn and press the relevant button in the calibration window.
For assisted calibration, press the "Calibration Assistant" button.  If desired, 
enter a note in the provided field describing the conditions under which the
calibration was performed.

Calibration results may be saved and loaded using the provided buttons at the
bottom of the window.  Notes are saved and loaded along with the calibration
data.

![Screenshot of Calibration Window](https://i.imgur.com/p94cxOX.png)

Users of known characterized calibration standard sets can enter the data for
these, and save the sets.

After pressing _Apply_, the calibration is immediately applied to the latest
sweep data.

_Currently, load capacitance is unsupported_

### TDR
To get accurate TDR measurements, calibrate the device, and attach the cable to
be measured at the calibration plane - i.e. at the same position where the
calibration load would be attached.  Open the "Time Domain Reflectometry"
window, and select the correct cable type, or manually enter a propagation
factor.

### Frequency bands
Open the "Display setup" window to configure the display of frequency bands. By
clicking "show bands", predefined frequency bands will be shown on the
frequency-based charts.  Click manage bands to change which bands are shown,
and the frequency limits of each.  Bands default and reset to European amateur
radio band frequencies.

## License
This software is licensed under version 3 of the GNU General Public License. It
comes with NO WARRANTY.

You can use it, commercially as well. You may make changes to the code, but I
(and the license) ask that you give these changes back to the community.

## Links
* Ohan Smit wrote an introduction to using the application:
  [https://zs1sci.com/blog/nanovnasaver/]
* HexAndFlex wrote a 3-part (thus far) series on Getting Started with the NanoVNA:
  [https://hexandflex.com/2019/08/31/getting-started-with-the-nanovna-part-1/] - Part 3 is dedicated to NanoVNASaver:
  [https://hexandflex.com/2019/09/15/getting-started-with-the-nanovna-part-3-pc-software/]
* Gunthard Kraus did documentation in English and German:
  [http://www.gunthard-kraus.de/fertig_NanoVNA/English/]
  [http://www.gunthard-kraus.de/fertig_NanoVNA/Deutsch/]

## Credits
Original application by Rune B. Broberg (5Q5R)

Contributions and changes by Holger Müller, David Hunt and others.

TDR inspiration shamelessly stolen from the work of Salil (VU2CWA) at
https://nuclearrambo.com/wordpress/accurately-measuring-cable-length-with-nanovna/

TDR cable types by Larry Goga.

Bugfixes and Python installation work by Ohan Smit.

Thanks to everyone who have tested, commented and inspired.  Particular thanks
go to the alpha testing crew who suffer the early instability of new versions.

This software is available free of charge. If you read all this way, and you
*still* want to support it, you may donate to the developer using the button
below:

[![Paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=T8KTGVDQF5K6E&item_name=NanoVNASaver+Development&currency_code=EUR&source=url)
