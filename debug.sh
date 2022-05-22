#!/bin/sh
exec python -m debugpy --listen 5678 --wait-for-client $@
