#!/bin/bash
echo 'OpenMandriva platform config generator'

extra_cfg_options="$EXTRA_CFG_OPTIONS"
extra_cfg_urpm_options="$EXTRA_CFG_URPM_OPTIONS"
uname="$UNAME"
email="$EMAIL"
platform_arch="$PLATFORM_ARCH"
platform_name=${PLATFORM_NAME:-"openmandriva"}
repo_url="$REPO_URL"
repo_names="$REPO_NAMES"

default_cfg=/etc/mock-urpm/default.cfg
gen_included_repos() {

names_arr=($repo_names)
urls_arr=($repo_url)

for (( i=0; i<${#names_arr[@]}; i++ ));
do
	for (( j=0; j<${#urls_arr[@]}; j++ ));
	do
		echo '"'${names_arr[i]}'"': '"'${urls_arr[j]}'"', >> $default_cfg
	done
done
# close urpmi repos section
echo '}' >> $default_cfg
}

if [ "$platform_arch" == 'aarch64' ] ; then
cat <<EOF> $default_cfg
config_opts['target_arch'] = '$platform_arch --without check --without uclibc --without dietlibc'
config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'aarch64')
config_opts['urpmi_options'] = '--no-suggests --no-verify-rpm --ignoresize --ignorearch --excludedocs --downloader wget --fastunsafe $extra_cfg_options'
config_opts['urpm_options'] = '--xml-info=never $extra_cfg_urpm_options'
EOF

elif [ "$platform_arch" == 'armv7hl' ] ; then
cat <<EOF> $default_cfg
config_opts['target_arch'] = '$platform_arch --without check --without uclibc'
config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'armv7hl', 'armv7l')
config_opts['urpmi_options'] = '--no-suggests --no-verify-rpm --ignoresize --ignorearch --excludedocs --downloader wget --fastunsafe $extra_cfg_options'
config_opts['urpm_options'] = '--xml-info=never $extra_cfg_urpm_options'
EOF
else

cat <<EOF> $default_cfg
config_opts['target_arch'] = '$platform_arch --without uclibc'
config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64')
config_opts['urpmi_options'] = '--no-suggests --no-verify-rpm --ignoresize --excludedocs --downloader wget --fastunsafe $extra_cfg_options'
config_opts['urpm_options'] = '--xml-info=never $extra_cfg_urpm_options'
EOF
fi

cat <<EOF>> $default_cfg
config_opts['root'] = '$platform_name-$platform_arch'
config_opts['chroot_setup'] = 'basesystem-minimal locales locales-en distro-release-OpenMandriva gnupg rpm-build urpmi wget meta-task task-devel clang'
config_opts['urpm_options'] = '--xml-info=never $extra_cfg_urpm_options'

# If it's True - current urpmi configs will be copied to the chroot.
# Ater that other media will be added.
# config_opts['use_system_media'] = True

config_opts['plugin_conf']['root_cache_enable'] = False
config_opts['plugin_conf']['ccache_enable'] = False
config_opts['use_system_media'] = False
config_opts['basedir'] = '/var/lib/mock-urpm/'
config_opts['cache_topdir'] = '/var/cache/mock-urpm/'

config_opts['dist'] = 'cooker'  # only useful for --resultdir variable subst
config_opts['macros']['%packager'] = '$uname <$email>'

config_opts["urpmi_media"] = {
EOF

gen_included_repos

cat $default_cfg
