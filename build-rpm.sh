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
# (tpg) remove package
rm -rf $HOME/${PACKAGE}
# (tpg) remove old files
# in many cases these are leftovers when build fails
# would be nice to remove them to free disk space
find $HOME -maxdepth 1 ! -name 'qemu-a*' ! -name 'docker-worker' ! -name '.gem' ! -name 'envfile' -mmin +1500 -exec rm -rf '{}' \;  &> /dev/null
}

cleanup

MOCK_BIN="/usr/bin/mock-urpm"
config_dir=/etc/mock-urpm/
# $PACKAGE same as project name
# e.g. github.com/OpenMandrivaAssociation/htop
build_package=$HOME/$PACKAGE
OUTPUT_FOLDER=${HOME}/output
# Qemu ARM binaries
QEMU_ARM_SHA="9c7e32080fab6751a773f363bfebab8ac8cb9f4a"
QEMU_ARM_BINFMT_SHA="10131ee0db7a486186c32e0cb7229f4368d0d28b"
QEMU_ARM64_SHA="240d661cee1fc7fbaf7623baa3a5b04dfb966424"
QEMU_ARM64_BINFMT_SHA="ec864fdf8b57ac77652cd6ab998e56fc4ed7ef5d"

GREP_PATTERN='error: (.*)$|Segmentation Fault|cannot find (.*)$|undefined reference (.*)$|cp: (.*)$|Hunk #1 FAILED|\(due to unsatisfied(.*)$'

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
comma=0
for rpm in ${OUTPUT_FOLDER}/*.rpm; do
    nevr=(`rpm -qp --queryformat "%{NAME} %{EPOCH} %{VERSION} %{RELEASE}" ${rpm}`)
    name=${nevr[0]}
    if [ "${name}" != '' ] ; then
	if [ $comma -eq 1 ]
	then
		echo -n "," >> ${c_data}
	fi
	if [ $comma -eq 0 ]
	then
		comma=1
	fi
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
	echo '}' >> ${c_data}
    fi
done
echo ']' >> ${c_data}

}

download_cache() {

if [[ "${CACHED_CHROOT_SHA1}" != '' ]] ; then
# if chroot not exist download it
    if [ ! -f $HOME/${CACHED_CHROOT_SHA1}.tar.xz ]; then
	curl -L "${filestore_url}/${CACHED_CHROOT_SHA1}" -o "$HOME/${CACHED_CHROOT_SHA1}.tar.xz"
    fi
# unpack in root
    echo "Extracting chroot $CACHED_CHROOT_SHA1"
    if echo "${CACHED_CHROOT_SHA1} $HOME/${CACHED_CHROOT_SHA1}.tar.xz" | sha1sum -c --status &> /dev/null; then
	sudo tar -xf $HOME/${CACHED_CHROOT_SHA1}.tar.xz -C /
    else
	echo "Building without cached chroot, becasue SHA1 is wrong."
	export CACHED_CHROOT_SHA1=""
    fi
fi

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
	if [ ! -e $HOME/qemu-aarch64 ] || [ $QEMU_ARM64_SHA != `sha1sum $HOME/qemu-aarch64 | awk '{print $1}'` ]; then

	    wget -O $HOME/qemu-aarch64 --content-disposition $filestore_url/$QEMU_ARM64_SHA --no-check-certificate &> /dev/null
	fi

	if [ ! -e $HOME/qemu-aarch64-binfmt ] || [ $QEMU_ARM64_BINFMT_SHA != `sha1sum $HOME/qemu-aarch64-binfmt | awk '{print $1}'` ]; then
	    wget -O $HOME/qemu-aarch64-binfmt --content-disposition $filestore_url/$QEMU_ARM64_BINFMT_SHA --no-check-certificate &> /dev/null
	fi
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
	if [ ! -e $HOME/qemu-arm ] || [ $QEMU_ARM_SHA != `sha1sum $HOME/qemu-arm | awk '{print $1}'` ]; then
	    wget -O $HOME/qemu-arm --content-disposition $filestore_url/$QEMU_ARM_SHA --no-check-certificate &> /dev/null
	fi

	if [ ! -e $HOME/qemu-arm-binfmt ] || [ $QEMU_ARM_BINFMT_SHA != `sha1sum $HOME/qemu-arm-binfmt | awk '{print $1}'` ]; then
	    wget -O $HOME/qemu-arm-binfmt --content-disposition $filestore_url/$QEMU_ARM_BINFMT_SHA --no-check-certificate &> /dev/null
	fi
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
MAX_RETRIES=10
WAIT_TIME=60
RETRY_GREP_STR="You may need to update your urpmi database\|problem reading synthesis file of medium\|retrieving failed: "

echo '--> Build src.rpm'
try_rebuild=true
retry=0
while $try_rebuild
do
    rm -rf $OUTPUT_FOLDER
    if [[ "${CACHED_CHROOT_SHA1}" != '' ]] ; then
	echo "--> Uses cached chroot with sha1 '$CACHED_CHROOT_SHA1'..."
	$MOCK_BIN --chroot "urpmi.removemedia -a"
	$MOCK_BIN --readdrepo -v --configdir $config_dir
	$MOCK_BIN -v --configdir=$config_dir --buildsrpm --spec=$build_package/${PACKAGE}.spec --sources=$build_package --no-cleanup-after --no-clean $extra_build_src_rpm_options --resultdir=$OUTPUT_FOLDER
    else
	$MOCK_BIN -v --configdir=$config_dir --buildsrpm --spec=$build_package/${PACKAGE}.spec --sources=$build_package --no-cleanup-after $extra_build_src_rpm_options --resultdir=$OUTPUT_FOLDER
    fi

    rc=${PIPESTATUS[0]}
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

# Check exit code after build
if [ $rc != 0 ] || [ ! -e $OUTPUT_FOLDER/*.src.rpm ]; then
    echo '--> Build failed: mock-urpm encountered a problem.'
    # 99% of all build failures at src.rpm creation is broken deps
    # m1 show only first match -oP show only matching
    grep -m1 -oP "\(due to unsatisfied(.*)$" $OUTPUT_FOLDER/root.log >> ~/build_fail_reason.log
    [ -n $subshellpid ] && kill $subshellpid
    exit 1
fi

echo '--> Done.'

echo '--> Build rpm'
try_rebuild=true
retry=0
while $try_rebuild
do
    $MOCK_BIN -v --configdir=$config_dir --rebuild $OUTPUT_FOLDER/*.src.rpm --no-cleanup-after --no-clean $extra_build_rpm_options --resultdir=$OUTPUT_FOLDER
    rc=${PIPESTATUS[0]}
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

# Check exit code after build
if [ $rc != 0 ]; then
    echo '--> Build failed: mock-urpm encountered a problem.'
# clean all the rpm files because build was not completed
    grep -m1 -i -oP "$GREP_PATTERN" $OUTPUT_FOLDER/root.log >> ~/build_fail_reason.log
    rm -rf $OUTPUT_FOLDER/*.rpm
    [ -n $subshellpid ] && kill $subshellpid
    exit 1
fi
echo '--> Done.'

# Extract rpmlint logs into separate file
echo "--> Grepping rpmlint logs from $OUTPUT_FOLDER/build.log to $OUTPUT_FOLDER/rpmlint.log"
sed -n "/Executing \"\/usr\/bin\/rpmlint/,/packages and.*specfiles checked/p" $OUTPUT_FOLDER/build.log > $OUTPUT_FOLDER/rpmlint.log
echo "--> Create rpm -qa list"
rpm --root=/var/lib/mock-urpm/openmandriva-$platform_arch/root/ -qa >> $OUTPUT_FOLDER/rpm-qa.log

# Test RPM files
TEST_CHROOT_PATH=$($MOCK_BIN --configdir=$config_dir --print-root-path)
test_code=0
test_log="$OUTPUT_FOLDER"/tests.log
echo '--> Checking if rpm packages can be installed' >> $test_log
sudo mkdir -p "$TEST_CHROOT_PATH"/test_root
sudo cp "$OUTPUT_FOLDER"/*.rpm "$TEST_CHROOT_PATH"/

try_retest=true
retry=0
while $try_retest
do
    sudo chroot $TEST_CHROOT_PATH urpmi --split-length 0 --downloader wget --wget-options --auth-no-challenge -v --debug --no-verify-rpm --fastunsafe --no-suggests --test `ls  $TEST_CHROOT_PATH | grep rpm` --root test_root --auto > $test_log.tmp 2>&1
    test_code=$?
    try_retest=false
    if [[ $test_code != 0 && $retry < $MAX_RETRIES ]] ; then
	if grep -q "$RETRY_GREP_STR" $test_log.tmp; then
	    echo '--> Repository was changed in the middle, will rerun the tests' >> $test_log
	    sleep $WAIT_TIME
	    sudo chroot $chroot_path urpmi.update -a >> $test_log 2>&1
	    try_retest=true
	    (( retry=$retry+1 ))
	fi
    fi
done

cat $test_log.tmp >> $test_log
echo 'Test code output: ' $test_code >> $test_log 2>&1
sudo rm -f  $TEST_CHROOT_PATH/*.rpm
sudo rm -rf $TEST_CHROOT_PATH/test_root
rm -f $test_log.tmp

# Check exit code after testing
if [ $test_code != 0 ] ; then
    echo '--> Test failed, see: tests.log'
    test_code_exit=5
fi
# End tests

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

validate_arch() {
# check if spec file have set ExcludeArch or ExclusiveArch against build arch target
    BUILD_TYPE=`grep -i '^excludearch:.*$\|^exclusivearch:.*$' *.spec | awk -F'[:]' '{print $1}'`

# check if spec file have both ExcludeArch and ExclusiveArch set up
    [[ ${#BUILD_TYPE} > 15 ]] && echo "Spec file has set ExcludeArch and ExclusiveArch. Exiting!" && exit 1

    SPEC_ARCH=(`grep -i '^excludearch:.*$\|^exclusivearch:.*$' *.spec | awk -F'[[:blank:]]' '{$1="";print $0}' | sort -u`)

# validate platform against spec file settings
    validate_build() {
        local _PLATFORM=($1)
# count for occurences
	for item in ${SPEC_ARCH[@]}; do
	    if [[ "${_PLATFORM[@]}" =~ "${item}" ]] ; then
		FOUND_MATCH=1
		echo "--> Found match of ${item} in ${_PLATFORM[@]} for ${BUILD_TYPE}"
	    fi
	done

	if [ -n "${FOUND_MATCH}" -a "${BUILD_TYPE,,}" = "excludearch" ]; then
	    echo "--> Build for this architecture is forbidden because of ${BUILD_TYPE} set in spec file!"
	    exit 6
	elif [ -z "${FOUND_MATCH}" -a "${BUILD_TYPE,,}" = "exclusivearch" ]; then
	    echo "--> Build for this architecture is forbidden because of ${BUILD_TYPE} set in spec file!"
	    exit 6
	else
	    echo "--> Spec validated for ExcludeArch and ExclusiveArch. Continue building."
	fi
    }

# translate arch into various options that may be set up in spec file
    case ${PLATFORM_ARCH,,} in
	armv7hl)
                validate_build "armx %armx %{armx} armv7hl"
                ;;
        aarch64)
                validate_build "armx %armx %{armx} aarch64"
                ;;
    i386|i586)
                validate_build "ix86 %ix86 %{ix86} i586 %i586 %{i586} i386 %i386 %{i386}"
                ;;
        x86_64)
                validate_build "x86_64 %x86_64 %{x86_64}"
                ;;
            *)
                echo "--> ${BUILD_TYPE} validated."
                ;;
    esac
}

clone_repo() {

MAX_RETRIES=5
WAIT_TIME=60
try_reclone=true
retry=0
while $try_reclone
do
    rm -rf $HOME/${PACKAGE}
# checkout specific branch/tag if defined
    if [[ ! -z "$project_version" ]]; then
# (tpg) clone only history of 100 commits to reduce bandwith
	git clone --depth 100 -b $project_version $git_repo $HOME/${PACKAGE}
	pushd $HOME/${PACKAGE}
	git rev-parse HEAD > $HOME/commit_hash
	popd
    else
	git clone --depth 100 $git_repo $HOME/${PACKAGE}
    fi
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

pushd $HOME/${PACKAGE}
# count number of specs (should be 1)
find_spec
# check for excludearch or exclusivearch
validate_arch
# download sources from .abf.yml
/bin/bash /mdv/download_sources.sh
popd

# build package
}

generate_config
clone_repo
download_cache
build_rpm
container_data
# wipe package
rm -rf $HOME/${PACKAGE}
