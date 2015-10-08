# docker-mock-urpm
Build RPMs using the Mock-Urpm Project (for any platform)

docker run -t -e MOCK_CONFIG=cooker-x86_64 -e SOURCE_RPM=htop-1.0.3-5.src.rpm -v /tmp/rpmbuild/:/rpmbuild --privileged=true openmandriva/builder
