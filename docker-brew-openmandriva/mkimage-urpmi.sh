#!/usr/bin/env bash
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

optTemp=$(getopt --options '+d,v:,m:,a:,s,u,p,h' --longoptions 'rootfs:,version:,mirror:,arch:,with-systemd,with-updates,with-passwd, help' --name mkimage-urpmi -- "$@")
eval set -- "$optTemp"
unset optTemp

while true; do
    case "$1" in
	-d|--rootfs) rootfsdir=$2 ; shift 2 ;;
	-v|--version) installversion="$2" ; shift 2 ;;
	-m|--mirror) mirror="$2" ; shift 2 ;;
	-a|--arch) arch="$2" ; shift 2 ;;
	-s|--with-systemd) systemd=true ; shift ;;
	-u|--with-updates) updates=true ; shift ;;
	-u|--with-passwd) passwd=true ; shift ;;
	-h|--help) usage ;;
	--) shift ; break ;;
    esac
done

target_dir="$rootfsdir/rootfs"

errorCatch() {
    echo "Error catched. Exiting"
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
    update_mirror=http://abf-downloads.openmandriva.org/$installversion/repository/$arch/main/updates/
fi


# run me here
install_chroot(){
    urpmi.addmedia main_release $mirror --urpmi-root "$target_dir";
if [ ! -z $updates ]; then
    urpmi.addmedia main_updates $update_mirror --urpmi-root "$target_dir";
fi
    urpmi basesystem-minimal passwd urpmi distro-release-OpenMandriva locales locales-en $systemd \
	--auto \
	--no-suggests \
	--no-verify-rpm \
	--urpmi-root "$target_dir" \
	--root "$target_dir"

    if [[ $? != 0 ]]; then
	echo "Creating urpmi chroot failed."
	errorCatch
    fi
}

arm_platform_detector(){

# Qemu ARM binaries
QEMU_ARM_SHA="9c7e32080fab6751a773f363bfebab8ac8cb9f4a"
QEMU_ARM_BINFMT_SHA="10131ee0db7a486186c32e0cb7229f4368d0d28b"
QEMU_ARM64_SHA="240d661cee1fc7fbaf7623baa3a5b04dfb966424"
QEMU_ARM64_BINFMT_SHA="ec864fdf8b57ac77652cd6ab998e56fc4ed7ef5d"

filestore_url="http://file-store.openmandriva.org/api/v1/file_stores"

probe_cpu() {
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
# download qemu binaries for non-native armx
if [[ "$arch" == "aarch64" ]]; then
    if [ $cpu != "aarch64" ] ; then
        if [ ! -e $HOME/qemu-aarch64 ] || [ $QEMU_ARM64_SHA != `sha1sum $HOME/qemu-aarch64 | awk '{print $1}'` ]; then

            wget -O $HOME/qemu-aarch64 --content-disposition $filestore_url/$QEMU_ARM64_SHA --no-check-certificate &> /dev/null
        fi

        if [ ! -e $HOME/qemu-aarch64-binfmt ] || [ $QEMU_ARM64_BINFMT_SHA != `sha1sum $HOME/qemu-aarch64-binfmt | awk '{print $1}'` ]; then
            wget -O $HOME/qemu-aarch64-binfmt --content-disposition $filestore_url/$QEMU_ARM64_BINFMT_SHA --no-check-certificate &> /dev/null
        fi
        chmod +x $HOME/qemu-aarch64 $HOME/qemu-aarch64-binfmt
    fi
    sudo sh -c "echo '$arch-mandriva-linux-gnueabi' > /etc/rpm/platform"
fi

# download qemu binaries for non-native armx
if [[ "$arch" == "armv7hl" ]]; then
    if [ $cpu != "arm" ] ; then
        if [ ! -e $HOME/qemu-arm ] || [ $QEMU_ARM_SHA != `sha1sum $HOME/qemu-arm | awk '{print $1}'` ]; then
            wget -O $HOME/qemu-arm --content-disposition $filestore_url/$QEMU_ARM_SHA --no-check-certificate &> /dev/null
        fi

        if [ ! -e $HOME/qemu-arm-binfmt ] || [ $QEMU_ARM_BINFMT_SHA != `sha1sum $HOME/qemu-arm-binfmt | awk '{print $1}'` ]; then
            wget -O $HOME/qemu-arm-binfmt --content-disposition $filestore_url/$QEMU_ARM_BINFMT_SHA --no-check-certificate &> /dev/null
        fi
        chmod +x $HOME/qemu-arm $HOME/qemu-arm-binfmt
    fi
    sudo sh -c "echo '$arch-mandriva-linux-gnueabi' > /etc/rpm/platform"
fi

# create path
if [[ "$arch" == "aarch64" ]]; then
    if [ $cpu != "aarch64" ] ; then
	mkdir -p $target_dir/usr/bin/
        cp -v $HOME/qemu-aarch64 $HOME/qemu-aarch64-binfmt $target_dir/usr/bin/
    fi
fi

if [[ "$arch" == "armv7hl" ]]; then
    if [ $cpu != "armb7hl" ] ; then
	mkdir -p $target_dir/usr/bin/
        cp -v $HOME/qemu-arm $HOME/qemu-arm-binfmt $target_dir/usr/bin/
    fi
fi
}
probe_cpu
}

arm_platform_detector
install_chroot

if [ ! -z $systemd ]; then
    echo -e "--------------------------------------"
    echo -e "Creating image with systemd support."
    echo -e "--------------------------------------\n"
    systemd="systemd"
fi

if [ ! -z $systemd ]; then
# Prevent systemd from starting unneeded services
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

if [ ! -z $passwd ]; then
ROOT_PASSWD="root"
echo "change password to $ROOT_PASSWD"
sudo chroot $target_dir /bin/bash -c "echo '$ROOT_PASSWD' |passwd root --stdin"

cat << EOF > $target_dir/README.omv
OpenMandriva $installversion distro
default login\password is root:root
You must change it!
EOF
fi

if [ ! -z $systemd ]; then
    tarFile="$rootfsdir/rootfs-${arch}-systemd.tar.xz"
else
    tarFile="$rootfsdir/rootfs-${arch}.tar.xz"
fi

pushd $target_dir
rm -fv usr/bin/qemu-*
tar --numeric-owner -caf $tarFile -c .
popd
rm -rf $target_dir
rm -fv /etc/rpm/platform
