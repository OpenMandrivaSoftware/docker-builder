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
