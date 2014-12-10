#!/bin/sh

# This is the directory that will be built.
JAIL=/tmp/jail

if [ "$(id -u)" != "0" ]; then
    echo "This must be run as root."
    exit 1
fi

echo "Attempting to make target directory: $JAIL"

if false; then

if [ -d "$JAIL" ]; then
    echo "Target directory already exists, deleting it."
    rm -rf "$JAIL"
fi

# Make the jail directory.
mkdir "$JAIL"

# Copy over binaries and library dependencies.
# TODO: Properly credit that this code came from the lab, and ask if that's okay.
./chroot_copy.sh `which env` $JAIL
./chroot_copy.sh `which python` $JAIL
./chroot_copy.sh `which openssl` $JAIL

mkdir -p $JAIL/usr/lib $JAIL/lib/x86_64-linux-gnu $JAIL/usr/lib/x86_64-linux-gnu
cp -r /usr/lib/python2.7 $JAIL/usr/lib
cp /usr/lib/x86_64-linux-gnu/libsqlite3.so.0 $JAIL/usr/lib/x86_64-linux-gnu/
cp /lib/x86_64-linux-gnu/libnss_dns.so.2 $JAIL/lib/x86_64-linux-gnu
cp /lib/x86_64-linux-gnu/libresolv.so.2 $JAIL/lib/x86_64-linux-gnu
cp -r /lib/resolvconf $JAIL/lib

mkdir -p $JAIL/usr/local/lib
cp -r /usr/local/lib/python2.7 $JAIL/usr/local/lib

mkdir -p $JAIL/etc
cp /etc/localtime $JAIL/etc/
cp /etc/timezone $JAIL/etc/
cp /etc/resolv.conf $JAIL/etc/

mkdir -p $JAIL/usr/share/zoneinfo
cp -r /usr/share/zoneinfo/America $JAIL/usr/share/zoneinfo/

mkdir $JAIL/dev
mknod -m 444 $JAIL/dev/urandom c 1 9

# Build the various required directories.
mkdir $JAIL/dryer21/
mkdir $JAIL/dryer21/code/
mkdir $JAIL/dryer21/data/
mkdir $JAIL/dryer21/rpc/

# Create resource directories.
mkdir $JAIL/dryer21/data/seller_database
mkdir $JAIL/dryer21/data/redeemer_database
mkdir $JAIL/dryer21/data/signing_private_key
mkdir $JAIL/dryer21/data/collector_master_public_key
mkdir $JAIL/dryer21/data/collector_master_private_key
mkdir $JAIL/dryer21/data/dispenser_address
mkdir $JAIL/dryer21/data/dispenser_private_key
mkdir $JAIL/dryer21/data/mixin_address

# Initialize the starting databases.
python setup_databases.py $JAIL

fi

# Copy over required code.
cp permissions.py rpc_lib.py global_storage.py verify.py $JAIL/dryer21/code/
cp -r seller/ $JAIL/dryer21/code/
cp -r redeemer/ $JAIL/dryer21/code/
cp -r rpc_servers/ $JAIL/dryer21/code/
cp -r rpc_clients/ $JAIL/dryer21/code/

# Copy over keys.
cp keys/signing_private_key.txt $JAIL/dryer21/data/signing_private_key/
cp keys/collector_master_public_key.txt $JAIL/dryer21/data/collector_master_public_key
cp keys/collector_master_private_key.txt $JAIL/dryer21/data/collector_master_private_key
cp keys/dispenser_public_key.txt $JAIL/dryer21/data/dispenser_public_key
cp keys/dispenser_private_key.txt $JAIL/dryer21/data/dispenser_private_key
cp keys/mixin_address $JAIL/dryer21/data/mixin_address

# Make absolutely everything be owned by root to start with.
chown -R 0:0 $JAIL
# Make sure nothing is writable by anyone else.
chmod -R a-w $JAIL

