docker-brew-openmandriva
==================

Scripts and files to create OpenMandriva official docker base images.

https://www.openmandriva.org/


# Build minimal openmandriva docker image
```cd .. ; sudo docker-brew-openmandriva/mkimage-urpmi.sh --version=cooker --arch=x86_64```

# Build ABF openmandriva/builder
```cd ..; sudo docker-brew-openmandriva/mkimage-dnf.sh --version=cooker --arch=x86_64 --with-builder```
