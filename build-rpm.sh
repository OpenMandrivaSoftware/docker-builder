#!/bin/bash
set -x

MOCK_BIN=/usr/bin/mock-urpm
config_dir=/etc/mock-urpm/
build_package=$HOME/$PACKAGE
OUTPUT_FOLDER=${HOME}/output

platform_arch="$PLATFORM_ARCH"
platform_name="$PLATFORM_NAME"
uname="$UNAME"
email="$EMAIL"
git_repo="$GIT_REPO"
commit_hash="$COMMIT_HASH"

echo "mount tmpfs filesystem to builddir"
sudo mount -a
if [ ! -d "$OUTPUT_FOLDER" ]; then
        mkdir -p $OUTPUT_FOLDER
else
        rm -f $OUTPUT_FOLDER/*
fi

generate_config() {
# Change output format for mock-urpm
sed '17c/format: %(message)s' $config_dir/logging.ini > ~/logging.ini
mv -f ~/logging.ini $config_dir/logging.ini

EXTRA_CFG_OPTIONS="$extra_cfg_options" \
  UNAME=$uname \
  EMAIL=$email \
  PLATFORM_NAME=$platform_name \
  PLATFORM_ARCH=$platform_arch \
  /bin/bash "/config-generator.sh"
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

if [[ "$platform_arch" == "aarch64" ]]; then
if [ $cpu != "aarch64" ] ; then
# this string responsible for "cannot execute binary file"
wget -O $HOME/qemu-aarch64 --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/6a2070ba0764eade5d161c34b708975c30606123 --no-check-certificate &> /dev/null
wget -O $HOME/qemu-aarch64-binfmt --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/b351026c6e3c7f5796320600651473b6547f46f8 --no-check-certificate &> /dev/null
chmod +x $HOME/qemu-aarch64 $HOME/qemu-aarch64-binfmt
# hack to copy qemu binary in non-existing path
(while [ ! -e  /var/lib/mock-urpm/openmandriva-$platform_arch/root/usr/bin/ ]
 do sleep 1;done
 sudo cp $HOME/qemu-* /var/lib/mock-urpm/openmandriva-$platform_arch/root/usr/bin/) &
 subshellpid=$!
fi
# remove me in future
sudo sh -c "echo '$platform_arch-mandriva-linux-gnueabi' > /etc/rpm/platform"
fi

if [[ "$platform_arch" == "armv7hl" ]]; then
if [ $cpu != "arm" ] ; then
# this string responsible for "cannot execute binary file"
# change path to qemu
wget -O $HOME/qemu-arm --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/96712ca87706e93356bf62b930530613c9c934d6 --no-check-certificate &> /dev/null
wget -O $HOME/qemu-arm-binfmt --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/65efec31ef6a636ae9593fff56d812026fcad903 --no-check-certificate &> /dev/null
chmod +x $HOME/qemu-arm $HOME/qemu-arm-binfmt
# hack to copy qemu binary in non-existing path
(while [ ! -e  /var/lib/mock-urpm/openmandriva-$platform_arch/root/usr/bin/ ]
 do sleep 1;done
 sudo cp $HOME/qemu-* /var/lib/mock-urpm/openmandriva-$platform_arch/root/usr/bin/) &
 subshellpid=$!
fi
# remove me in future
sudo sh -c "echo '$platform_arch-mandriva-linux-gnueabi' > /etc/rpm/platform"
fi

}
probe_cpu
}

build_rpm() {
arm_platform_detector
echo '--> Build src.rpm'
$MOCK_BIN -v --configdir=$config_dir --buildsrpm --spec=$build_package/${PACKAGE}.spec --sources=$build_package --no-cleanup-after --resultdir=$OUTPUT_FOLDER
# Save exit code
rc=$?
kill $subshellpid
echo '--> Done.'

# Check exit code after build
if [ $rc != 0 ] ; then
  echo '--> Build failed: mock-urpm encountered a problem.'
  exit 1
fi

$MOCK_BIN -v --configdir=$config_dir --rebuild $OUTPUT_FOLDER/${PACKAGE}-*.src.rpm --no-cleanup-after --no-clean --resultdir=$OUTPUT_FOLDER
}

clone_repo() {

git clone $git_repo $HOME/${PACKAGE}
if [ $? -ne '0' ] ; then
	echo '--> There are no such repository.'
	exit 1
fi
# checkout specific commit hash if defined
if [[ ! -z "$commit_hash" ]] ; then
git checkout $commit_hash
if [ $? -ne '0' ] ; then
	echo '--> There are no such commit hash.'
	echo '--> $commit_hash'
	exit 1
fi
fi

pushd $HOME/${PACKAGE}
/bin/bash /download_sources.sh
popd

# build package
}

generate_config
clone_repo
build_rpm
