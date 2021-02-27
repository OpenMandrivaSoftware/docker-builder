#!/usr/bin/env bash
set -x
#
set -e

mkimg="$(basename "$0")"
common_pwd="$PWD"

usage() {
	cat >&2 <<EOF
usage: $mkimg --rootfs=rootfs_path --version=openmandriva_version [--mirror=url]
       $mkimg --rootfs=/tmp/rootfs --version=openmandriva2014.0 --arch=x86_64
       $mkimg --rootfs=. --version=cooker --mirror=http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/release/
       $mkimg --rootfs=. --version=cooker
EOF
	exit 1
}

optTemp=$(getopt --options '+d,v:,m:,a:,s,b,U,p,h,+x' --longoptions 'rootfs:,version:,mirror:,arch:,with-systemd,with-builder,without-user,with-passwd,help,extra-package:' --name mkimage-dnf -- "$@")
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
	-b|--with-builder) builder=true ; shift ;;
	-p|--with-passwd) passwd=true ; shift ;;
	-U|--without-user) without_user=true ; shift ;;
	-h|--help) usage ;;
	-x|--extra-package) extra_packages="$extra_packages $2" ; shift 2 ;;
	--) shift ; break ;;
	esac
done

if [ -z "${installversion}" ]; then
	# Attempt to match host version
	if grep -q Cooker /etc/os-release; then
		installversion=cooker
	elif grep -q Rolling /etc/os-release; then
		installversion=rolling
	else
		installversion="$(rpm --eval %distro_release)"
	fi
	if [ -z "${installversion}" ]; then
		echo "Error: no version supplied and unable to detect host openmandriva version"
		exit 1
	fi
fi

[ -z "$arch" ] && arch="`uname -m`"
[ -z "$rootfsdir" ] && rootfsdir="$common_pwd/docker-brew-openmandriva/${installversion}"

target=$(mktemp -d --tmpdir $(basename $0).XXXXXX)
mkdir -m 755 "$target"/dev
mknod -m 600 "$target"/dev/console c 5 1
mknod -m 600 "$target"/dev/initctl p
mknod -m 666 "$target"/dev/full c 1 7
mknod -m 666 "$target"/dev/null c 1 3
mknod -m 666 "$target"/dev/ptmx c 5 2
mknod -m 666 "$target"/dev/random c 1 8
mknod -m 666 "$target"/dev/tty c 5 0
mknod -m 666 "$target"/dev/tty0 c 4 0
mknod -m 666 "$target"/dev/urandom c 1 9
mknod -m 666 "$target"/dev/zero c 1 5

errorCatch() {
	echo "Error catched. Exiting"
	rm -rf "${target}"
	exit 1
}

trap errorCatch ERR SIGHUP SIGINT SIGTERM

if [ -n "${mirror}" ]; then
	# If mirror provided, use it exclusively
	reposetup="--disablerepo=* --repofrompath=omvrel,$mirror/$installversion/repository/$arch/main/release/ --repofrompath=omvup,$mirror/$installversion/repository/$arch/main/updates/ --enablerepo=omvrel --enablerepo=omvup"
else
	# If mirror is *not* provided, use mirrorlist
	reposetup="--disablerepo=* --enablerepo=openmandriva-${arch} --enablerepo=updates-${arch}"

	mkdir -p ${target}/etc/yum.repos.d
	cat >${target}/etc/yum.repos.d/openmandriva-${arch}.repo <<EOF
[openmandriva-$arch]
name=OpenMandriva $installversion - $arch
baseurl=http://abf-downloads.openmandriva.org/$installversion/repository/$arch/main/release/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-OpenMandriva
failovermethod=priority
enabled=1

[updates-$arch]
name=OpenMandriva $installversion - $arch - Updates
baseurl=http://abf-downloads.openmandriva.org/$installversion/repository/$arch/main/updates/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-OpenMandriva
failovermethod=priority
enabled=1
EOF
	echo "Repository config:" >/dev/stderr
	cat ${target}/etc/yum.repos.d/openmandriva-${arch}.repo >/dev/stderr
fi

if [ ! -z "${systemd}" ]; then
	printf '%b\n' '--------------------------------------'
	printf '%b\n' 'Creating image with systemd support.'
	printf '%b\n' '--------------------------------------'
	systemd="systemd passwd"
fi

# run me here
install_chroot(){
	dnf \
		--refresh \
		${reposetup} \
		--installroot="${target}" \
		--nogpgcheck \
		--forcearch="${arch}" \
		--releasever="${installversion}" \
		--setopt=install_weak_deps=False \
		--nodocs --assumeyes \
		install basesystem-minimal openmandriva-repos dnf locales locales-en ${systemd}

	if [ $? != 0 ]; then
		echo "Creating dnf chroot failed."
		errorCatch
	fi
}

install_chroot

if [ ! -z "${systemd}" ]; then
# Prevent systemd from starting unneeded services
	(cd "${target}"/lib/systemd/system/sysinit.target.wants/; for i in *; do [ "$i" = 'systemd-tmpfiles-setup.service' ] || rm -f "${i}"; done); \
	rm -f "${target}"/lib/systemd/system/multi-user.target.wants/*;\
	rm -f "${target}"/etc/systemd/system/*.wants/*;\
	rm -f "${target}"/lib/systemd/system/local-fs.target.wants/*; \
	rm -f "${target}"/lib/systemd/system/sockets.target.wants/*udev*; \
	rm -f "${target}"/lib/systemd/system/sockets.target.wants/*initctl*; \
	rm -f "${target}"/lib/systemd/system/basic.target.wants/*;\
	rm -f "${target}"/lib/systemd/system/anaconda.target.wants/*;
fi

# effectively: febootstrap-minimize --keep-zoneinfo --keep-rpmdb --keep-services "$target".
#  locales
rm -rf "$target"/usr/{{lib,share}/locale,{lib,lib64}/gconv,bin/localedef,sbin/build-locale-archive}
#  docs and man pages
rm -rf "$target"/usr/share/{man,doc,info,gnome/help}
#  cracklib
rm -rf "$target"/usr/share/cracklib
#  i18n
rm -rf "$target"/usr/share/i18n
#  yum cache
rm -rf "$target"/var/cache/dnf/*

if [ -d "${target}"/etc/sysconfig ]; then
# allow networking init scripts inside the container to work without extra steps
cat > "$target"/etc/sysconfig/network <<EOF
NETWORKING=yes
HOSTNAME=localhost.localdomain
EOF
fi

# make sure /etc/resolv.conf has something useful in it
mkdir -p "${target}"/etc
cat > "${target}"/etc/resolv.conf <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

if [ ! -z "${without_user}" ]; then
	# Create user omv, password omv
	echo 'omv:x:1001:1001::/home/omv:/bin/bash' >>"${target}"/etc/passwd
	echo 'omv:$6$rG3bQ92hkTNubV1p$5qPB9FoXBhNcSE1FOklCoEDowveAgjSf2cHYVwCENZaWtgpFQaRRRN5Ihwd8nuaKMdA1R1XouOasJ7u5dbiGt0:17302:0:99999:7:::' >> "${target}"/etc/shadow
	echo 'omv:x:1001:' >>"${target}"/etc/group
	sed -i -e 's,wheel:x:10:$,wheel:x:10:omv,' "${target}"/etc/group
fi

if [ ! -z "${passwd}" ]; then
	ROOT_PASSWD="root"
	echo "change password to ${ROOT_PASSWD}"
	sudo chroot "${target}" /bin/bash -c "echo '${ROOT_PASSWD}' |passwd root --stdin"

	cat << EOF > "${target}"/README.omv
OpenMandriva $installversion distro
default login and password is root:root
You must change it!
EOF
fi

if [ ! -z "${systemd}" ]; then
	tarFile="${rootfsdir}"/rootfs-"${installversion}"-systemd.tar.xz
else
	tarFile="${rootfsdir}"/rootfs-"${installversion}".tar.xz
fi

pushd "${target}"

tar --numeric-owner -caf "${tarFile}" -c .
mv -f "${tarFile}" $common_pwd/docker-brew-openmandriva/$installversion/
pushd $common_pwd/docker-brew-openmandriva/$installversion/
docker build --tag=openmandriva/$installversion:$arch --file Dockerfile .

docker run -i -t --rm openmandriva/$installversion:$arch /bin/bash -c 'echo success'
docker push openmandriva/$installversion:$arch

docker manifest create openmandriva/cooker:latest \
	--amend openmandriva/cooker:x86_64 \
	--amend openmandriva/cooker:aarch64
docker manifest annotate openmandriva/cooker:latest openmandriva/cooker:x86_64 --os linux --arch amd64
docker manifest annotate openmandriva/cooker:latest openmandriva/cooker:aarch64 --os linux --arch arm64

if [ ! -z "${builder}" ]; then
	cd $common_pwd
	if [ "${arch}" = 'x86_64' ]; then
		sed -i "s/ARCH_TARGET/x86_64/g" Dockerfile.builder
	fi
	sed -i "s/ARCH_REL/${arch}/g" Dockerfile.builder
	docker build --tag=openmandriva/builder:$arch --file Dockerfile.builder .
	git checkout Dockerfile.builder

	docker manifest create openmandriva/builder:latest \
		--amend openmandriva/builder:x86_64 \
		--amend openmandriva/builder:aarch64
	docker manifest annotate openmandriva/builder:latest openmandriva/builder:x86_64 --os linux --arch amd64
	docker manifest annotate openmandriva/builder:latest openmandriva/builder:aarch64 --os linux --arch arm64
fi

popd
rm -rf "${target}"
