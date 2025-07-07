# Builds a NanoVNASaver.app on MacOS
# ensure you have pyqt >=6.4 installed (brew install pyqt)
#
export VENV_DIR=macbuildenv

# setup build venv
python3 -m venv ${VENV_DIR}
. ./${VENV_DIR}/bin/activate

# install required dependencies (pyqt libs must be installed on the system)
python3 -m pip install pip==24.2 setuptools==75.2.0

# install project dependencies including dev dependencies (which contains pyinstaller)
pip install -e ".[dev]"

# compile UI files first (required before importing NanoVNASaver)
echo "Compiling UI files..."
python3 -m tools.ui_compile

# show version info
python3 -c "import NanoVNASaver; print(f'NanoVNASaver version: {NanoVNASaver.__version__}')"

# ensure pyinstaller is available
which pyinstaller || pip install pyinstaller

pyinstaller --onedir -p src -n NanoVNASaver src/NanoVNASaver/__main__.py --recursive-copy-metadata NanoVNASaver --window --clean  -y -i NanoVNASaver_48x48.icns --recursive-copy-metadata NanoVNASaver
tar -C dist -zcf ./dist/NanoVNASaver.app-`uname -m`.tar.gz  NanoVNASaver.app

deactivate
rm -rf ${VENV_DIR}