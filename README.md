# docker-mock-urpm
Build RPMs using the Mock-Urpm Project (for any platform)

docker run -i -e REPO="main contrib" -e PACKAGE=unzip -e UNAME=fedya -e EMAIL=alexander@openmandriva.org -e PLATFORM_NAME=cooker -e PLATFORM_ARCH=x86_64 -v /home/omv/output/:/home/omv/output/ --privileged=true openmandriva/builder

OR

docker run -i -e REPO="main" -e PACKAGE=unzip -e UNAME=fedya -e EMAIL=alexander@openmandriva.org -e PLATFORM_NAME=cooker -e PLATFORM_ARCH=aarch64 -v /home/omv/output/:/home/omv/output/ --privileged=true openmandriva/builder-aarch64

OR

docker run -i -e PACKAGE=unzip -e UNAME=fedya -e EMAIL=alexander@openmandriva.org -e PLATFORM_NAME=cooker -e PLATFORM_ARCH=armv7hl -v /home/omv/output/:/home/omv/output/ --privileged=true openmandriva/builder-armv7hl

# generate container

docker build --tag=openmandriva/builder --file $HOME/docker-builder/Dockerfile.x86_64 .

# remove stopped containers
docker rm -v $(docker ps -a -q -f status=exited)
