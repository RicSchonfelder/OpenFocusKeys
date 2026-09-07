#!/bin/sh
cd "$(dirname "$0")"
nohup python3 app.py >/dev/null 2>&1 &
