## Quickstart

Clone repository

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
        -e BUILD_ARCH="x86_64 armv7hl i586 i686 aarch64" \
        -e BUILD_PLATFORM="cooker,4.0,rolling,rock" openmandriva/builder
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
        -e BUILD_PLATFORM="cooker,4.0,rolling,rock" openmandriva/builder
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
PACKAGE=htop GIT_REPO=git://github.com/OpenMandrivaAssociation/htop.git \
USE_EXTRA_TESTS=true PLATFORM_ARCH=x86_64 PLATFORM_NAME=cooker \
UNAME=fdrt EMAIL=fdrt@fdrt.com USE_MOCK_CACHE= EXTRA_CFG_OPTIONS= \
REPO_NAMES='cooker_main_release cooker_main_updates' \
REPO_URL='http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/release \
http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/updates'\
PROJECT_VERSION=master /usr/bin/python build-rpm.py
```
## How to remove stopped containers
```bash
docker rm -v $(docker ps -a -q -f status=exited)
```
