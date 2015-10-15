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

build_rpm() {
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

git clone https://fedya@abf.io/openmandriva/${PACKAGE}.git $HOME/${PACKAGE}
if [ $? -ne '0' ] ; then
	echo '--> There are no such repository.'
	exit 1
fi

pushd $HOME/${PACKAGE}
/bin/bash /download_sources.sh
popd

# build package
}

generate_config
clone_repo
build_rpm
