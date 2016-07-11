docker-brew-openmandriva
==================

Scripts and files to create OpenMandriva official docker base images.

https://www.openmandriva.org/

# Build base chroot
sudo sh mkimage-urpmi.sh --rootfs=/tmp/ --version=cooker --arch=x86_64
