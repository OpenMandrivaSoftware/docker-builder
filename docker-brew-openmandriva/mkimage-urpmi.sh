#!/usr/bin/env bash
#
set -e

mkimg="$(basename "$0")"

usage() {
	echo >&2 "usage: $mkimg --rootfs=rootfs_path --version=openmandriva_version [--mirror=url]"
	echo >&2 "   ie: $mkimg --rootfs=. --version=cooker --mirror=http://abf-downloads.openmandriva.org/cooker/repository/x86_64/main/release/"
	echo >&2 "       $mkimg --rootfs=. --version=cooker"
	echo >&2 "       $mkimg --rootfs=/tmp/rootfs --version=openmandriva2014.0 --arch=x86_64"
	exit 1
}

optTemp=$(getopt --options '+d,v:,m:,a:,s,h' --longoptions 'rootfs:,version:,mirror:,arch:,with-systemd, help' --name mkimage-urpmi -- "$@")
eval set -- "$optTemp"
unset optTemp

while true; do
	case "$1" in
			-d|--rootfs) rootfsdir=$2 ; shift 2 ;;
			-v|--version) installversion="$2" ; shift 2 ;;
			-m|--mirror) mirror="$2" ; shift 2 ;;
			-a|--arch) arch="$2" ; shift 2 ;;
			-s|--with-systemd) systemd=true ; shift ;;
			-h|--help) usage ;;
			--) shift ; break ;;
	esac
done

target_dir="$rootfsdir/rootfs"

errorCatch() {
    echo "Something went wrong. Exiting"
	rm -rf $target_dir
    exit 1
}

trap errorCatch ERR SIGHUP SIGINT SIGTERM

if [ -z $installversion ]; then
# Attempt to match host version
		if [ -r /etc/distro-release ]; then
			installversion="$(rpm --eval %distro_release)"
		else
			echo "Error: no version supplied and unable to detect host openmandriva version"
			exit 1
		fi
fi

if [ -z $mirror ]; then
# No repo provided, use main
	mirror=http://abf-downloads.openmandriva.org/$installversion/repository/$arch/main/release/
fi

# run me here
install_chroot(){
	urpmi.addmedia main_release $mirror --urpmi-root "$target_dir";
	urpmi basesystem-minimal urpmi distro-release-OpenMandriva locales locales-en $systemd \
		--auto \
		--no-suggests \
		--no-verify-rpm \
		--urpmi-root "$target_dir" \
		--root "$target_dir"

	[[ $? != 0 ]] && errorCatch
}

install_chroot

if [ ! -z $systemd ]; then
	echo -e "--------------------------------------"
	echo -e "Creating image with systemd support."
	echo -e "--------------------------------------\n"
	systemd="systemd"
fi

if [ ! -z $systemd ]; then
#Prevent systemd from starting unneeded services
	(cd $target_dir/lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
		rm -f $target_dir/lib/systemd/system/multi-user.target.wants/*;\
		rm -f $target_dir/etc/systemd/system/*.wants/*;\
		rm -f $target_dir/lib/systemd/system/local-fs.target.wants/*; \
		rm -f $target_dir/lib/systemd/system/sockets.target.wants/*udev*; \
		rm -f $target_dir/lib/systemd/system/sockets.target.wants/*initctl*; \
		rm -f $target_dir/lib/systemd/system/basic.target.wants/*;\
		rm -f $target_dir/lib/systemd/system/anaconda.target.wants/*;
fi

if [ -d "$target_dir/etc/sysconfig" ]; then
# allow networking init scripts inside the container to work without extra steps
	echo 'NETWORKING=yes' > "$target_dir/etc/sysconfig/network"
fi

# make sure /etc/resolv.conf has something useful in it
mkdir -p "$target_dir/etc"
cat > "$target_dir/etc/resolv.conf" <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

if [ ! -z $systemd ]; then
	tarFile="$rootfsdir/rootfs-${arch}-systemd.tar.xz"
else
	tarFile="$rootfsdir/rootfs-${arch}.tar.xz"
fi

pushd $target_dir
tar --numeric-owner -caf $tarFile -c .
popd
rm -rf $target_dir
