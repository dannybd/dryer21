#Dryer 21: Bitcoin goes in, Bitcoin goes out. Never a miscommunication.

##Installation

###First-time Installation:

    cd ~
    git clone http://github.com/dannybd/dryer21 dryer21
    cd dryer21
    sudo pip install flask PySocks PyCrypto
    sudo su
    kinit
    aklog
    cd pybitcointools
    python setup.py install
    cd ..
    ./chroot_setup.sh --rebuild # Only need to run with first time
    cd /tmp; chroot jail python dryer21/code/permissions.py --launch

If you make any code changes, be sure to re-run:

    ./chroot_setup.sh; cd /tmp; chroot jail python dryer21/code/permissions.py --launch

##How it Works