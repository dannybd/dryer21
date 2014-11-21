#!/bin/sh

# This is the directory that will be built.
JAIL_DIR=/jail

if [ "$(id -u)" != "0" ]; then
    echo "This must be run as root."
    exit 1
fi

echo "Attempting to make target directory: $JAIL_DIR"

if [ -d "$JAIL_DIR" ]; then
    echo "Target directory already exists."
    exit 1
fi

# Make the jail directory.
mkdir "$JAIL_DIR"

