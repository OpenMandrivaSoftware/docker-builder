#!/bin/sh
set -x
echo '--> mdv-scripts/cached-chroot: build.sh'

MOCK_BIN=/usr/bin/mock-urpm
config_dir=/etc/mock-urpm/
OUTPUT_FOLDER=/home/omv/iso_builder/results
filestore_url="http://file-store.openmandriva.org/api/v1/file_stores"
distro_release=${DISTRO_RELEASE:-"cooker"}
platform_name=${PLATFORM_NAME:-"openmandriva"}
token="$TOKEN"
arches=${ARCHES:-"i586 x86_64 aarch64 armv7hl"}

chroot_path="/var/lib/mock-urpm"

cleanup() {
    echo "Cleaning up..."
    sudo rm -fv /etc/rpm/platform
    rm -fv /etc/mock-urpm/default.cfg
    sudo rm -rf ${chroot_path}/*
}

# wipe all
cleanup

if [ "`uname -m`" = "x86_64" ] && echo "$platform_arch" |grep -qE 'i[0-9]86'; then
    # Change the kernel personality so build scripts don't think
    # we're building for 64-bit
    MOCK_BIN="/usr/bin/i386 $MOCK_BIN"
fi

generate_config() {
# Change output format for mock-urpm
sed '17c/format: %(message)s' $config_dir/logging.ini > ~/logging.ini
mv -f ~/logging.ini $config_dir/logging.ini

if [[ ${distro_release,,} = cooker ]]; then
    repo_names="main"
    repo_url="http://abf-downloads.openmandriva.org/$distro_release/repository/$arch/main/release/"
else
    repo_names="main main_updates"
    repo_url="http://abf-downloads.openmandriva.org/$distro_release/repository/$arch/main/release/ http://abf-downloads.openmandriva.org/$distro_release/repository/$arch/main/updates/"
fi

DISTRO_RELEASE=$distro_release \
  PLATFORM_ARCH=$arch \
  REPO_NAMES=$repo_names REPO_URL=$repo_url \
  /bin/bash "/home/omv/iso_builder/config-generator.sh"
}

arm_platform_detector(){
probe_cpu() {
# probe cpu type
cpu=`uname -m`
case "$cpu" in
    i386|i486|i586|i686|i86pc|BePC|x86_64)
	cpu="i386"
   ;;
    armv[4-9]*)
	cpu="arm"
   ;;
    aarch64)
	cpu="aarch64"
   ;;
esac

if [[ "$arch" == "aarch64" ]]; then
    if [ $cpu != "aarch64" ] ; then
# this string responsible for "cannot execute binary file"
# hack to copy qemu binary in non-existing path
	(while [ ! -e  ${chroot_path}/$platform_name-$arch/root/usr/bin/ ]
	    do sleep 1;done
	    sudo cp /usr/bin/qemu-static-aarch64 ${chroot_path}/$platform_name-$arch/root/usr/bin/) &
	    subshellpid=$!
    fi
# remove me in future
    sudo sh -c "echo '$arch-mandriva-linux-gnueabi' > /etc/rpm/platform"
fi

if [[ "$arch" == "armv7hl" ]]; then
    if [ $cpu != "arm" ] ; then
# this string responsible for "cannot execute binary file"
# change path to qemu
# hack to copy qemu binary in non-existing path
	(while [ ! -e  ${chroot_path}/$platform_name-$arch/root/usr/bin/ ]
	    do sleep 1;done
	    sudo cp /usr/bin/qemu-static-arm ${chroot_path}/$platform_name-$arch/root/usr/bin/) &
	    subshellpid=$!
    fi
# remove me in future
    sudo sh -c "echo '$arch-mandriva-linux-gnueabi' > /etc/rpm/platform"
fi

}
probe_cpu
}

if [ ! -d "$OUTPUT_FOLDER" ]; then
    mkdir -p "$OUTPUT_FOLDER"
else
    rm -f "$OUTPUT_FOLDER"/*
fi

for arch in $arches ; do
    # init mock-urpm config
    generate_config
    arm_platform_detector

    $MOCK_BIN --init --configdir $config_dir -v --no-cleanup-after
    # Save exit code
    rc=$?
    echo '--> Done.'

    # Check exit code after build
    if [ $rc != 0 ] ; then
	echo '--> Build failed: mock-urpm encountered a problem.'
	cleanup
	exit 1
    fi

    chroot=`ls -1 ${chroot_path} | grep ${arch} | head -1`

    if [ "${chroot}" == '' ] ; then
    echo '--> Build failed: chroot does not exist.'
	cleanup
	exit 1
    fi

    # xz options -4e is 4th extreme level of compression, and -T0 is to use all available threads to speedup compress
    # need sudo to pack root:root dirs
    sudo XZ_OPT="-4e -T0" tar --no-xattrs --no-acls --absolute-paths -Jcvf "${OUTPUT_FOLDER}"/"${chroot}".tar.xz "${chroot_path}"/"${chroot}"

    # Save exit code
    rc=$?

    # Check exit code after build
    if [ $rc != 0 ] ; then
	echo '--> Build failed: tar encountered a problem.'
	cleanup
	exit 1
    fi
    sudo rm -rf ${chroot_path}/${chroot}
done

echo '--> Build has been done successfully!'
exit 0
