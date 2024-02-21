#!/bin/bash

echo "NOTICE: As of March 31, 2024, make-system-user is officially deprecated. Please see https://forum.snapcraft.io/t/make-system-user-deprecation/39044 for more info." 1>&2

$SNAP/bin/python3 $SNAP/bin/msu.py "$@"
