# Builds a NanoVNASaver.app on MacOS
# ensure you have pyqt >=6.4 installed (brew install pyqt)
#
export VENV_DIR=macbuildenv

# setup build venv
python3 -m venv ${VENV_DIR}
. ./${VENV_DIR}/bin/activate

# install required dependencies (pyqt libs must be installed on the system)
python3 -m pip install pip==24.2 setuptools==75.2.0
pip install -r requirements.txt
pip install PyInstaller==6.11.0

python3 setup.py -V

pyinstaller --onedir -p src -n NanoVNASaver nanovna-saver.py --window --clean  -y -i icon_48x48.icns
tar -C dist -zcf ./dist/NanoVNASaver.app-`uname -m`.tar.gz  NanoVNASaver.app

deactivate
rm -rf ${VENV_DIR}