# docker-mock-urpm
Build RPMs using the Mock-Urpm Project (for any platform)

docker run -i -e MOCK_CONFIG=cooker-x86_64 -e SOURCES=. -e SPEC_FILE=weston.spec -e PACKAGE=weston -v /home/omv/output/:/home/omv/output/ --privileged=true openmandriva/builder
