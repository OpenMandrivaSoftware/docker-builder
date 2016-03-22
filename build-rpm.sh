#!/bin/bash
set -x

cleanup() {
echo "cleanup"
sudo rm -fv /etc/rpm/platform
rm -fv /etc/mock-urpm/default.cfg
sudo rm -rf /var/lib/mock-urpm/*
# unmask/mask it, we need to keep logs
rm -rf $HOME/output/
rm -fv ~/build_fail_reason.log
}

cleanup

trap "sudo pkill -TERM -P $$; exit" EXIT

MOCK_BIN="/usr/bin/mock-urpm"
config_dir=/etc/mock-urpm/
build_package=$HOME/$PACKAGE
OUTPUT_FOLDER=${HOME}/output
# Qemu ARM binaries
QEMU_ARM_SHA="9c7e32080fab6751a773f363bfebab8ac8cb9f4a"
QEMU_ARM_BINFMT_SHA="10131ee0db7a486186c32e0cb7229f4368d0d28b"
QEMU_ARM64_SHA="240d661cee1fc7fbaf7623baa3a5b04dfb966424"
QEMU_ARM64_BINFMT_SHA="ec864fdf8b57ac77652cd6ab998e56fc4ed7ef5d"

filestore_url="http://file-store.openmandriva.org/api/v1/file_stores"
platform_arch="$PLATFORM_ARCH"
platform_name="$PLATFORM_NAME"
uname="$UNAME"
email="$EMAIL"
git_repo="$GIT_REPO"
project_version="$PROJECT_VERSION"
extra_build_rpm_options="$EXTRA_BUILD_RPM_OPTIONS"
extra_build_src_rpm_options="$EXTRA_BUILD_SRC_RPM_OPTIONS"
extra_cfg_options="$EXTRA_CFG_OPTIONS"
extra_cfg_urpm_options="$EXTRA_CFG_URPM_OPTIONS"

if [ "`uname -m`" = "x86_64" ] && echo "$platform_arch" |grep -qE 'i[0-9]86'; then
    # Change the kernel personality so build scripts don't think
    # we're building for 64-bit
    MOCK_BIN="/usr/bin/i386 $MOCK_BIN"
fi

echo "mount tmpfs filesystem to builddir"
sudo mount -a

generate_config() {
# Change output format for mock-urpm
sed '17c/format: %(message)s' $config_dir/logging.ini > ~/logging.ini
mv -f ~/logging.ini $config_dir/logging.ini

EXTRA_CFG_OPTIONS="$extra_cfg_options" \
  EXTRA_CFG_URPM_OPTIONS="$extra_cfg_urpm_options" \
  UNAME=$uname \
  EMAIL=$email \
  PLATFORM_NAME=$platform_name \
  PLATFORM_ARCH=$platform_arch \
  /bin/bash "/mdv/config-generator.sh"
}

container_data() {
# Generate data for container
c_data=$OUTPUT_FOLDER/container_data.json
project_name=`echo ${git_repo} | sed s%.*/%% | sed s/.git$//`
echo '[' > ${c_data}
for rpm in ${OUTPUT_FOLDER}/*.rpm; do
  nevr=(`rpm -qp --queryformat "%{NAME} %{EPOCH} %{VERSION} %{RELEASE}" ${rpm}`)
  name=${nevr[0]}
  if [ "${name}" != '' ] ; then
    fullname=`basename $rpm`
    epoch=${nevr[1]}
    version=${nevr[2]}
    release=${nevr[3]}

    dep_list=""
    [[ ! "${fullname}" =~ ".*src.rpm$" ]] && dep_list=`urpmq --whatrequires ${name} | sort -u | xargs urpmq --sourcerpm | cut -d\  -f2 | rev | cut -f3- -d- | rev | sort -u | grep -v "^${project_name}$" | xargs echo`
    sha1=`sha1sum ${rpm} | awk '{ print $1 }'`

    echo "--> dep_list for '${name}':"
    echo ${dep_list}

    echo '{' >> ${c_data}
    echo "\"dependent_packages\":\"${dep_list}\","    >> ${c_data}
    echo "\"fullname\":\"${fullname}\","              >> ${c_data}
    echo "\"sha1\":\"${sha1}\","                      >> ${c_data}
    echo "\"name\":\"${name}\","                      >> ${c_data}
    echo "\"epoch\":\"${epoch}\","                    >> ${c_data}
    echo "\"version\":\"${version}\","                >> ${c_data}
    echo "\"release\":\"${release}\""                 >> ${c_data}
    echo '},' >> ${c_data}
  fi
done
# Add '{}'' because ',' before
echo '{}' >> ${c_data}
echo ']' >> ${c_data}

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
wget -O $HOME/qemu-aarch64 --content-disposition $filestore_url/$QEMU_ARM64_SHA --no-check-certificate &> /dev/null
wget -O $HOME/qemu-aarch64-binfmt --content-disposition $filestore_url/$QEMU_ARM64_BINFMT_SHA --no-check-certificate &> /dev/null
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
wget -O $HOME/qemu-arm --content-disposition $filestore_url/$QEMU_ARM_SHA  --no-check-certificate &> /dev/null
wget -O $HOME/qemu-arm-binfmt --content-disposition $filestore_url/$QEMU_ARM_BINFMT_SHA --no-check-certificate &> /dev/null
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

# We will rerun the build in case when repository is modified in the middle,
# but for safety let's limit number of retest attempts
# (since in case when repository metadata is really broken we can loop here forever)
MAX_RETRIES=5
WAIT_TIME=60
RETRY_GREP_STR="You may need to update your urpmi database\|problem reading synthesis file of medium\|retrieving failed: "

echo '--> Build src.rpm'
try_rebuild=true
retry=0
while $try_rebuild
do
    rm -rf $OUTPUT_FOLDER
    $MOCK_BIN -v --configdir=$config_dir --buildsrpm --spec=$build_package/${PACKAGE}.spec --sources=$build_package --no-cleanup-after $extra_build_src_rpm_options --resultdir=$OUTPUT_FOLDER
    rc=$?
    try_rebuild=false
    if [[ $rc != 0 && $retry < $MAX_RETRIES ]] ; then
	if grep -q "$RETRY_GREP_STR" $OUTPUT_FOLDER/root.log; then
	    try_rebuild=true
	    (( retry=$retry+1 ))
	    echo "--> --> Repository was changed in the middle, will rerun the build. Next try (${retry} from ${MAX_RETRIES})..."
	    echo "--> Delay ${WAIT_TIME} sec..."
	    sleep $WAIT_TIME
	fi
    fi
done

# Save exit code
rc=$?
kill $subshellpid
echo '--> Done.'

# Check exit code after build
if [ $rc != 0 ] ; then
  echo '--> Build failed: mock-urpm encountered a problem.'
  # 99% of all build failures at src.rpm creation is broken deps
  # m1 show only first match -oP show only matching
  grep -m1 -oP "\(due to unsatisfied(.*)$" $OUTPUT_FOLDER/root.log >> ~/build_fail_reason.log
  exit 1
fi

echo '--> Build rpm'
$MOCK_BIN -v --configdir=$config_dir --rebuild $OUTPUT_FOLDER/*.src.rpm --no-cleanup-after --no-clean $extra_build_rpm_options --resultdir=$OUTPUT_FOLDER

# Save exit code
rc=$?
kill $subshellpid
echo '--> Done.'

# Check exit code after build
if [ $rc != 0 ] ; then
  echo '--> Build failed: mock-urpm encountered a problem.'
# clean all the rpm files because build was not completed
  grep -m1 -oP "error: (.*)$" $OUTPUT_FOLDER/build.log >> ~/build_fail_reason.log
  rm -rf $OUTPUT_FOLDER/*.rpm
  exit 1
fi

# Extract rpmlint logs into separate file
echo "--> Grepping rpmlint logs from $OUTPUT_FOLDER/build.log to $OUTPUT_FOLDER/rpmlint.log"
sed -n "/Executing \"\/usr\/bin\/rpmlint/,/packages and.*specfiles checked/p" $OUTPUT_FOLDER/build.log > $OUTPUT_FOLDER/rpmlint.log
echo "--> Create rpm -qa list"
rpm --root=/var/lib/mock-urpm/openmandriva-$platform_arch/root/ -qa >> $OUTPUT_FOLDER/rpm-qa.log

}

find_spec() {
# Check count of *.spec files (should be one)
x=`ls -1 | grep '.spec$' | wc -l | sed 's/^ *//' | sed 's/ *$//'`
spec_name=`ls -1 | grep '.spec$'`
if [ $x -eq '0' ] ; then
    echo '--> There are no spec files in repository.'
    exit 1
else
  if [ $x -ne '1' ] ; then
    echo '--> There are more than one spec file in repository.'
    exit 1
  fi
fi
}

clone_repo() {

MAX_RETRIES=5
WAIT_TIME=60
try_reclone=true
retry=0
while $try_reclone
do
	rm -rf $HOME/${PACKAGE}
	git clone $git_repo $HOME/${PACKAGE}
	rc=$?
	try_reclone=false
	if [[ $rc != 0 && $retry < $MAX_RETRIES ]] ; then
	  try_reclone=true
	  (( retry=$retry+1 ))
	  echo "--> Something wrong with git repository, next try (${retry} from ${MAX_RETRIES})..."
	  echo "--> Delay ${WAIT_TIME} sec..."
	  sleep $WAIT_TIME
	fi
done

# checkout specific branch/tag if defined
if [[ ! -z "$project_version" ]] ; then
pushd $HOME/${PACKAGE}
git checkout $project_version
git rev-parse HEAD > $HOME/commit_hash
popd
fi

pushd $HOME/${PACKAGE}
# download sources from .abf.yml
/bin/bash /mdv/download_sources.sh
# count number of specs (should be 1)
find_spec
popd

# build package
}

generate_config
clone_repo
build_rpm
container_data
# wipe package
rm -rf $HOME/${PACKAGE}
