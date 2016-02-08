#!/bin/bash
set -x

cleanup() {
echo "cleanup"
sudo rm -fv /etc/rpm/platform
rm -fv /etc/mock-urpm/default.cfg
sudo rm -rf /var/lib/mock-urpm/*
rm -rf $HOME/output/
}

cleanup

trap "sudo pkill -TERM -P $$; exit" EXIT

MOCK_BIN=/usr/bin/mock-urpm
config_dir=/etc/mock-urpm/
build_package=$HOME/$PACKAGE
OUTPUT_FOLDER=${HOME}/output
# Qemu ARM binaries
QEMU_ARM_SHA="723161ec6cdd569cf6897431c64629451f76a036"
QEMU_ARM_BINFMT_SHA="352b636da23bee8caf56f8fd000f908e45ae8386"
QEMU_ARM64_SHA="d77667285d3e2663842c7f160c5d4ed4aa209d96"
QEMU_ARM64_BINFMT_SHA="e523d6b5dc77288ff25071a4df9ddc307a717d9c"

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
    [[ ! "${fullname}" =~ ".*src.rpm$" ]] && dep_list=`sudo chroot ${chroot_path} urpmq --whatrequires ${name} | sort -u | xargs sudo chroot ${chroot_path} urpmq --sourcerpm | cut -d\  -f2 | rev | cut -f3- -d- | rev | sort -u | grep -v "^${project_name}$" | xargs echo`
#    [[ ! "${fullname}" =~ ".*src.rpm$" ]] && dep_list=`urpmq --whatrequires ${name} | sort -u | xargs urpmq --sourcerpm | cut -d\  -f2 | rev | cut -f3- -d- | rev | sort -u | grep -v "^${project_name}$" | xargs echo`
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
wget -O $HOME/qemu-aarch64 --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/$QEMU_ARM64_SHA --no-check-certificate &> /dev/null
wget -O $HOME/qemu-aarch64-binfmt --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/$QEMU_ARM64_BINFMT_SHA --no-check-certificate &> /dev/null
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
wget -O $HOME/qemu-arm --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/$QEMU_ARM_SHA  --no-check-certificate &> /dev/null
wget -O $HOME/qemu-arm-binfmt --content-disposition http://file-store.rosalinux.ru/api/v1/file_stores/$QEMU_ARM_BINFMT_SHA --no-check-certificate &> /dev/null
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
$MOCK_BIN -v --configdir=$config_dir --buildsrpm --spec=$build_package/${PACKAGE}.spec --sources=$build_package --no-cleanup-after $extra_build_src_rpm_options --resultdir=$OUTPUT_FOLDER
# Save exit code
rc=$?
kill $subshellpid
echo '--> Done.'

# Check exit code after build
if [ $rc != 0 ] ; then
  echo '--> Build failed: mock-urpm encountered a problem.'
  exit 1
fi

$MOCK_BIN -v --configdir=$config_dir --rebuild $OUTPUT_FOLDER/${PACKAGE}-*.src.rpm --no-cleanup-after --no-clean $extra_build_rpm_options --resultdir=$OUTPUT_FOLDER

# Extract rpmlint logs into separate file
echo "--> Grepping rpmlint logs from $OUTPUT_FOLDER//build.log to $OUTPUT_FOLDER//rpmlint.log"
sed -n "/Executing \"\/usr\/bin\/rpmlint/,/packages and.*specfiles checked/p" $OUTPUT_FOLDER/build.log > $OUTPUT_FOLDER/rpmlint.log

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
WAIT_TIME=10
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
git submodule update --init
git remote rm origin
git checkout $project_version
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
