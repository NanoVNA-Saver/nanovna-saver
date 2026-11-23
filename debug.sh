#!/bin/bash
# export PYTHONPATH="src"
export SRC=$(dirname $(realpath $0))/src
uv run python -Xfrozen_modules=off -m debugpy --listen 5678 --wait-for-client -c "
import sys

sys.path.insert(0, \"$SRC\")

import NanoVNASaver.__main__
NanoVNASaver.__main__.main()
"
