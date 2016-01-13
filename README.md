## Quickstart

Create builder image:

```bash
docker build --tag=openmandriva/builder --file $HOME/docker-builder/Dockerfile.builder .
```

## Remove stopped containers
```bash
docker rm -v $(docker ps -a -q -f status=exited)
```

## Run abf builder
```bash
docker run -ti --rm --privileged=true -e BUILD_TOKEN="your_token" \
	-e BUILD_ARCH="x86_64 armv7hl i586 aarch64" \
	 -e BUILD_PLATFORM="cooker" openmandriva/builder
```

## Prepare Environment
## ARMv7
```bash
/etc/binfmt.d/arm.conf
```
```bash
:arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-arm-binfmt:P
```

## ARM64 (aarch64)
```bash
/etc/binfmt.d/aarch64.conf
```
```bash
:aarch64:M::\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\xb7\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-aarch64-binfmt:P
```
