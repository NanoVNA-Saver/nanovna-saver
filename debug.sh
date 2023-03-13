#!/bin/sh
export PYTHONPATH="src"
exec python -m debugpy --listen 5678 --wait-for-client $@
