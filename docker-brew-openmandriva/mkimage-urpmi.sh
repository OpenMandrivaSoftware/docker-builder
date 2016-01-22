#!/usr/bin/env bash
#
# Script to create OpenMandriva official base images for integration with stackbrew 
# library.
# Based on https://github.com/juanluisbaptiste/docker-brew-mageia
#

set -e

mkimg="$(basename "$0")"

usage() {
	echo >&2 "usage: $mkimg --rootfs=rootfs_path --version=openmandriva_version [--mirror=url]"
	echo >&2 "   ie: $mkimg --rootfs=. --version=cooker --mirror=http://abf-downloads.rosalinux.ru/cooker/repository/x86_64/main/release/"
	echo >&2 "       $mkimg --rootfs=. --version=cooker"
	echo >&2 "       $mkimg --rootfs=/tmp/rootfs --version=openmandriva2014.0 --arch=x86_64"
	exit 1
}

optTemp=$(getopt --options '+d,v:,m:,a:,s,h' --longoptions 'rootfs:,version:,mirror:,arch:,with-systemd, help' --name mkimage-urpmi -- "$@")
eval set -- "$optTemp"
unset optTemp

installversion=
mirror=
while true; do
        case "$1" in
                -d|--rootfs) dir=$2 ; shift 2 ;;
                -v|--version) installversion="$2" ; shift 2 ;;
                -m|--mirror) mirror="$2" ; shift 2 ;;
                -a|--arch) arch="$2" ; shift 2 ;;
                -s|--with-systemd) systemd=true ; shift ;;
                -h|--help) usage ;;
                 --) shift ; break ;;
        esac
done

#dir="$1"
rootfsDir="$dir/rootfs"
#shift


#[ "$dir" ] || usage

if [ -z $installversion ]; then
        # Attempt to match host version
        if [ -r /etc/distro-release ]; then
                installversion="$(sed 's/^[^0-9\]*\([0-9.]\+\).*$/\1/' /etc/version)"
        else
                echo "Error: no version supplied and unable to detect host openmandriva version"
                exit 1
        fi
fi

if [ -z $mirror ]; then
        # No repo provided, use main
	mirror=http://abf-downloads.rosalinux.ru/$installversion/repository/$arch/main/release/
fi

if [ ! -z $systemd ]; then
        echo -e "--------------------------------------"
        echo -e "Creating image with systemd support."
        echo -e "--------------------------------------\n"
        systemd="systemd" 
fi

(
        urpmi.addmedia main_release \
                $mirror \
                --urpmi-root "$rootfsDir"
        urpmi basesystem-minimal urpmi locales locales-en $systemd \
                --auto \
                --no-suggests \
		--no-verify-rpm \
                --urpmi-root "$rootfsDir" \
                --root "$rootfsDir"
)

"$(dirname "$BASH_SOURCE")/.febootstrap-minimize" "$rootfsDir"

if [ -d "$rootfsDir/etc/sysconfig" ]; then
        # allow networking init scripts inside the container to work without extra steps
        echo 'NETWORKING=yes' > "$rootfsDir/etc/sysconfig/network"
fi

if [ ! -z $systemd ]; then
	#Prevent systemd from starting unneeded services
	(cd $rootfsDir/lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
        rm -f $rootfsDir/lib/systemd/system/multi-user.target.wants/*;\
        rm -f $rootfsDir/etc/systemd/system/*.wants/*;\
        rm -f $rootfsDir/lib/systemd/system/local-fs.target.wants/*; \
        rm -f $rootfsDir/lib/systemd/system/sockets.target.wants/*udev*; \
        rm -f $rootfsDir/lib/systemd/system/sockets.target.wants/*initctl*; \
        rm -f $rootfsDir/lib/systemd/system/basic.target.wants/*;\
        rm -f $rootfsDir/lib/systemd/system/anaconda.target.wants/*;
fi


# Docker mounts tmpfs at /dev and procfs at /proc so we can remove them
rm -rf "$rootfsDir/dev" "$rootfsDir/proc"
mkdir -p "$rootfsDir/dev" "$rootfsDir/proc"

# make sure /etc/resolv.conf has something useful in it
mkdir -p "$rootfsDir/etc"
cat > "$rootfsDir/etc/resolv.conf" <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

if [ ! -z $systemd ]; then
    tarFile="$dir/rootfs-systemd.tar.xz"
else
    tarFile="$dir/rootfs.tar.xz"
fi
    
touch "$tarFile"

(
        set -x
        tar --numeric-owner -caf "$tarFile" -C "$rootfsDir" --transform='s,^./,,' .
)

( set -x; rm -rf "$rootfsDir" )
