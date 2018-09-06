docker-brew-openmandriva
==================

Scripts and files to create OpenMandriva official docker base images.

https://www.openmandriva.org/


# Build minimal openmandriva docker image
```sudo sh mkimage-urpmi.sh --rootfs=/tmp/ --version=cooker --arch=x86_64```

# Build ABF openmandriva/builder
```sudo sh mkimage-dnf.sh --rootfs=/tmp/ --version=cooker --arch=x86_64 --with-builder```
