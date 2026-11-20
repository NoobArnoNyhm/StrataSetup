#!/bin/sh
set -eu

rm -f /tmp/pi-configured
python3 /opt/pi/configure.py
touch /tmp/pi-configured
exec "$@"
