#!/usr/bin/env bash
set -x
#
set -e

mkimg="$(basename "$0")"

usage() {
    echo >&2 "usage: $mkimg --rootfs=rootfs_path --version=openmandriva_version [--mirror=url]"
    echo >&2 "       $mkimg --rootfs=/tmp/rootfs --version=3.0 --arch=x86_64 --with-updates"
    echo >&2 "       $mkimg --rootfs=/tmp/rootfs --version=openmandriva2014.0 --arch=x86_64"
    echo >&2 "       $mkimg --rootfs=. --version=cooker --mirror=http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/release/"
    echo >&2 "       $mkimg --rootfs=. --version=cooker"
    exit 1
}

optTemp=$(getopt --options '+d,v:,m:,a:,s,u,U,p,h,+x' --longoptions 'rootfs:,version:,mirror:,arch:,with-systemd,with-updates,without-user,with-passwd,help,extra-package:' --name mkimage-dnf -- "$@")
eval set -- "$optTemp"
unset optTemp

extra_packages=""

while true; do
    case "$1" in
	-d|--rootfs) rootfsdir=$2 ; shift 2 ;;
	-v|--version) installversion="$2" ; shift 2 ;;
	-m|--mirror) mirror="$2" ; shift 2 ;;
	-a|--arch) arch="$2" ; shift 2 ;;
	-s|--with-systemd) systemd=systemd ; shift ;;
	-u|--with-updates) updates=true ; shift ;;
	-p|--with-passwd) passwd=true ; shift ;;
	-U|--without-user) without_user=true ; shift ;;
	-h|--help) usage ;;
	-x|--extra-package) extra_packages="$extra_packages $2" ; shift 2 ;;
	--) shift ; break ;;
    esac
done

target_dir="${rootfsdir}/rootfs"

errorCatch() {
    echo "Error catched. Exiting"
    rm -rf "${target_dir}"
    exit 1
}

trap errorCatch ERR SIGHUP SIGINT SIGTERM

if [ -z "${installversion}" ]; then
# Attempt to match host version
    if [ -r /etc/distro-release ]; then
	installversion="$(rpm --eval %distro_release)"
    else
	echo "Error: no version supplied and unable to detect host openmandriva version"
	exit 1
    fi
fi

if [ ! -z "${mirror}" ]; then
        # If mirror provided, use it exclusively
        reposetup="--disablerepo=* --repofrompath=omvrel,$mirror/media/main/release/ --repofrompath=omvup,$mirror/media/main/updates/ --enablerepo=omvrel --enablerepo=omvup"
fi

if [ -z "${mirror}" ]; then
        # If mirror is *not* provided, use mirrorlist
        reposetup="--disablerepo=* --enablerepo=openmandriva-x86_64 --enablerepo=updates-x86_64"
fi

# Must be after the non-empty check or otherwise this will fail
if [ -z "${pkgmgr}" ]; then
        pkgmgr="dnf"
fi


# run me here
install_chroot(){
    dnf \
    --refresh \
    ${reposetup} \
    --installroot="${target_dir}" \
    --releasever="${installversion}" \
    --setopt=install_weak_deps=False \
    --nodocs --assumeyes \
    install basesystem-minimal openmandriva-repos ${pkgmgr} locales locales-en ${systemd}

    if [ $? != 0 ]; then
	echo "Creating dnf chroot failed."
	errorCatch
    fi
}

arm_platform_detector(){

probe_cpu() {
cpu="$(uname -m)"
case "${cpu}" in
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

# create path
if [ "${arch}" = 'aarch64' ]; then
    if [ "${cpu}" != 'aarch64' ]; then
	mkdir -p "${target_dir}"/usr/bin/
	sudo sh -c "echo '${arch}-mandriva-linux-gnueabi' > /etc/rpm/platform"
	cp /usr/bin/qemu-static-aarch64 "${target_dir}"/usr/bin/
    fi
fi

if echo "${arch}" |grep -qE '^arm'; then
    if [ "${cpu}" != 'arm' -a "${cpu}" != "aarch64" ] ; then
	mkdir -p "${target_dir}"/usr/bin/
	sudo sh -c "echo '${arch}-mandriva-linux-gnueabi' > /etc/rpm/platform"
	cp /usr/bin/qemu-static-arm "${target_dir}"/usr/bin/
    fi
fi
}
probe_cpu
}

arm_platform_detector
install_chroot

if [ ! -z "${systemd}" ]; then
    printf '%b\n' '--------------------------------------'
    printf '%b\n' 'Creating image with systemd support.'
    printf '%b\n' '--------------------------------------'
    systemd="systemd"
fi

if [ ! -z "${systemd}" ]; then
# Prevent systemd from starting unneeded services
    (cd "${target_dir}"/lib/systemd/system/sysinit.target.wants/; for i in *; do [ "$i" = 'systemd-tmpfiles-setup.service' ] || rm -f "${i}"; done); \
	rm -f "${target_dir}"/lib/systemd/system/multi-user.target.wants/*;\
	rm -f "${target_dir}"/etc/systemd/system/*.wants/*;\
	rm -f "${target_dir}"/lib/systemd/system/local-fs.target.wants/*; \
	rm -f "${target_dir}"/lib/systemd/system/sockets.target.wants/*udev*; \
	rm -f "${target_dir}"/lib/systemd/system/sockets.target.wants/*initctl*; \
	rm -f "${target_dir}"/lib/systemd/system/basic.target.wants/*;\
	rm -f "${target_dir}"/lib/systemd/system/anaconda.target.wants/*;
fi

if [ -d "${target_dir}"/etc/sysconfig ]; then
# allow networking init scripts inside the container to work without extra steps
    echo 'NETWORKING=yes' > "${target_dir}"/etc/sysconfig/network
fi

# make sure /etc/resolv.conf has something useful in it
mkdir -p "${target_dir}"/etc
cat > "${target_dir}"/etc/resolv.conf <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

if [ ! -z "${without_user}" ]; then
	# Create user omv, password omv
	echo 'omv:x:1001:1001::/home/omv:/bin/bash' >>"${target_dir}"/etc/passwd
	echo 'omv:$6$rG3bQ92hkTNubV1p$5qPB9FoXBhNcSE1FOklCoEDowveAgjSf2cHYVwCENZaWtgpFQaRRRN5Ihwd8nuaKMdA1R1XouOasJ7u5dbiGt0:17302:0:99999:7:::' >> "${target_dir}"/etc/shadow
	echo 'omv:x:1001:' >>"${target_dir}"/etc/group
	sed -i -e 's,wheel:x:10:$,wheel:x:10:omv,' "${target_dir}"/etc/group
fi

if [ ! -z "${passwd}" ]; then
	ROOT_PASSWD="root"
	echo "change password to ${ROOT_PASSWD}"
	sudo chroot "${target_dir}" /bin/bash -c "echo '${ROOT_PASSWD}' |passwd root --stdin"

	cat << EOF > "${target_dir}"/README.omv
OpenMandriva $installversion distro
default login and password is root:root
You must change it!
EOF
fi

if [ ! -z "${systemd}" ]; then
    tarFile="${rootfsdir}"/rootfs-"${arch}"-systemd.tar.xz
else
    tarFile="${rootfsdir}"/rootfs-"${arch}".tar.xz
fi

cd "${target_dir}"
rm -fv usr/bin/qemu-*
tar --numeric-owner -caf "${tarFile}" -c .
cd ..
rm -rf "${target_dir}"
rm -fv /etc/rpm/platform
