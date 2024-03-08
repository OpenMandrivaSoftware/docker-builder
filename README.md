## About

OpenMandriva Docker Builder and Utilities
This repository contains a collection of scripts and Docker configurations for building and managing OpenMandriva Docker images, RPM packages, and development environments.
It is designed to streamline the process of creating OpenMandriva official Docker base images, building RPM packages, and setting up environments for various architectures including ARM and RISC-V.

## Features

Docker Image Building: Scripts for creating minimal and ABF (Automated Build Farm) Docker images for OpenMandriva.
Process Monitoring: A utility script to monitor and kill stalled processes, specifically targeting ldd.
Error Checking: A script to scan log files for known error patterns and log them for review.
Automated Build Requests: Scripts to automate the process of requesting build IDs, performing Git operations, and managing package builds.
RPM Package Building: A comprehensive script for building RPM packages, including environment setup, source downloading, spec file validation, and cleanup.
Configuration Generation: Generates configuration options for building packages, adjusting for specific package requirements and system resources.
Raspberry Pi Disk Preparation: A script for preparing a disk image for Raspberry Pi 3, including filesystem creation and package repository setup.

## Quickstart

```bash
git clone https://github.com/OpenMandrivaSoftware/docker-builder.git
```
Create builder image:

```bash
cd docker-builder
```

```bash
sudo sh docker-brew-openmandriva/mkimage-dnf.sh --rootfs=/tmp/ --version=cooker --arch=x86_64 --with-builder
```

## Remove stopped containers
```bash
docker rm -v $(docker ps -a -q -f status=exited)
```

## Run abf builder
```bash
docker run -ti --rm --privileged=true -h <yourname>.openmandriva.org \
        -e BUILD_TOKEN="your_token" \
        -e BUILD_ARCH="x86_64, znver1, i686, aarch64, riscv64" \
        -e BUILD_PLATFORM="cooker,rolling,rock" openmandriva/builder
```

## How to run ARMx or RISCV  builder
Install QEMU
```bash
sudo dnf install qemu qemu-riscv64-static qemu-riscv64-static qemu-arm-static qemu-aarch64-static
```
Restart binfmt service
```bash
sudo systemctl restart systemd-binfmt
```
Run builder

```bash
docker run -ti --rm --privileged=true -h <yourname>.openmandriva.org \
        -e BUILD_TOKEN="your_token" \
        -e BUILD_ARCH="riscv64" \
        -e BUILD_PLATFORM="cooker,4.3,rolling,rock" openmandriva/builder
```

## How to run build-rpm.py without docker
* cook enviroment [enviroment](https://github.com/OpenMandrivaSoftware/docker-builder/blob/master/Dockerfile.builder#L6)
* install mock
```bash
sudo dnf install -y mock
```
```bash
sudo echo "%mock ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
sudo usermod -a -G mock $USER
sudo chown -R $USER:mock /etc/mock
sudo dnf install -y mock git coreutils curl sudo rpmdevtools python-yaml
```


```bash
!!!DO NOT RUN IT OUT OF CONTAINER!!!

PACKAGE=htop \
GIT_REPO=git://github.com/OpenMandrivaAssociation/htop.git \
PROJECT_VERSION=master \
USE_EXTRA_TESTS=true PLATFORM_ARCH=x86_64 PLATFORM_NAME=cooker \
UNAME=fdrt EMAIL=fdrt@fdrt.com USE_MOCK_CACHE= EXTRA_CFG_OPTIONS= \
REPO_NAMES='cooker_main_release cooker_main_updates' \
REPO_URL='http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/release \
http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/updates' \
FILE_STORE_ADDR=https://file-store.openmandriva.org/ \
/usr/bin/python build-rpm.py
```

## Contributing
Contributions to this repository are welcome.Please ensure that your contributions adhere to the OpenMandriva coding standards and guidelines.

## License
This project is licensed under the MIT License.See the LICENSE file for details.

Acknowledgments
This repository is maintained by the OpenMandriva Association.
We thank all contributors for their efforts and contributions to the OpenMandriva project.
