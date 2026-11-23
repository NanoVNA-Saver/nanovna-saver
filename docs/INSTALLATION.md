# Installation Instructions

## Installation and Use with pipx
For installation it is recommended to use pipx instead of pip.  Most installations nowadays require the usage of a virtual environment when using pip, pipx automatically arranges this for you.

Installing the latest release with pipx install. e.g.:

    pipx install git+https://github.com/NanoVNA-Saver/nanovna-saver

Or if you want to install a specific version use:

    pipx install git+https://github.com/NanoVNA-Saver/nanovna-saver@v0.7.3

Once completed run with the following command: `NanoVNASaver`

## Installing via DEB for Debian (and Ubuntu)
🚧 TODO: this is currently broken

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
🚧 TODO: this is currently broken

`make rpm` builds an (untested) rpm package that can be installed on your system the usual way.

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

6. Run nanovna-saver folder by:

        NanoVNASaver
