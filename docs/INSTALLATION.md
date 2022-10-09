Installation Instructions
=========================

## Ubuntu 20.04 / 22.04


1. Install python3.8 and pip

        sudo apt install python3.8 python3-pip
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
