#!/bin/sh
export PYTHONPATH="src"
python3 -Xfrozen_modules=off -m debugpy --listen 5678 --wait-for-client "$@"
