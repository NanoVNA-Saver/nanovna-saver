# Installation Instructions

## Installation and Use with pip

Copy the link of the tgz from latest relaese and install it with pip install. e.g.:

    pip3 install https://github.com/NanoVNA-Saver/nanovna-saver/archive/refs/tags/v0.5.5.tar.gz

Once completed run with the following command: `NanoVNASaver`

The instructions omit the easiest way to get the program running under Linux - no installation - just start it in the git directory. This makes it difficult for pure users, e.g. hams, who therefore even try to run the Windows exe version under Wine.

Proposal - Add these sections below to the top README.md, e.g. between "Detailed installation instructions" and "Using the software" (Please review and add e.g. more necessary debian packages):

## Running on Linux without installation

The program simply works from the source directory without having to install it.

Simple step-by-step instruction, open a terminal window and type:

    sudo apt install git python3-pyqt5 python3-numpy python3-scipy
    git clone https://github.com/NanoVNA-Saver/nanovna-saver
    cd nanovna-saver

Perhaps your system needs a few additional python modules:

- Run with `python nanovna-saver.py` and look at the response of (e.g. missing modules).
- Install the missing modules, preferably via `sudo apt install ...`

until `nanovna-saver.py` starts up.

Now the program can be used from the `nanovna-saver` directory.

## Installing via DEB for Debian (and Ubuntu)

The installation has the benefit that it allows you to run the program from anywhere, because the
main program is found via the regular `$PATH` and the modules are located in the Python module path.

If you're using a debian based distro you should consider to build your own `*.deb` package.
This has the advantage that NanoVNASaver can be installed and uninstalled cleanly in the system.

For this you need to install `python3-stdeb` - the module for converting Python code and modules into a Debian package:

    apt install python3-stdeb

Then you can build the package via:

    make deb

This package can be installed the usual way with

    sudo dpkg -i nanovnasaver....deb
or

   sudo apt install ./nanovnasaver....deb

### Installing via RPM (experimental)

`make rpm` builds an (untested) rpm package that can be installed on your system the usual way.

## Ubuntu 20.04 / 22.04 / 24.04

1. Install python3 and pip

        sudo apt install python3 python3-pip libxcb-cursor-dev
        python3 -m venv ~/.venv_nano
        . ~/.venv_nano/bin/activate
        pip install -U pip

2. Clone repo and cd into the directory

        git clone https://github.com/NanoVNA-Saver/nanovna-saver
        cd nanovna-saver

3. Update pip and run the pip installation

        python3 -m pip install .

   (You may need to install the additional packages python3-distutils,
   python3-setuptools and python3-wheel for this command to work on some
   distributions.)

4. Once completed run with the following command

        . ~/.venv_nano/bin/activate
        python3 nanovna-saver.py

## Automated MacOS Build Script

1. If needed, install dependencies

        brew install python pyqt
2. Run the automated build script

        ./build-macos-app.sh
3. Open the completed app

        open ./dist/NanoVNASaver/NanoVNASaver.app
   or double-click on NanoVNASaver.app in finder. 

## MacPorts

Via a MacPorts distribution maintained by @ra1nb0w.

1. Install MacPorts following the [install guide](https://www.macports.org/install.php)

2. Install NanoVNASaver :

        sudo port install NanoVNASaver

3. Now you can run the software from shell `NanoVNASaver` or run as app
   `/Applications/MacPorts/NanoVNASaver.app`

## Homebrew

1. Install Homebrew from <https://brew.sh/> (This will ask for your password)

        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

2. Python :

        brew install python

3. Pip :<br/>
    Download the get-pip.py file and run it to install pip

        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py

4. NanoVNASaver Installation : <br/>
    clone the source code to the nanovna-saver folder

        git clone https://github.com/NanoVNA-Saver/nanovna-saver
        cd nanovna-saver

5. Install local pip packages

        python3 -m pip install .

6. Run nanovna-saver in the nanovna-saver folder by:

        python3 nanovna-saver.py
