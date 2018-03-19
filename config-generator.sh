#!/bin/bash
printf '%s\n' '--> OpenMandriva platform config generator.'

extra_cfg_options="$EXTRA_CFG_OPTIONS"
uname="$UNAME"
email="$EMAIL"
platform_arch="$PLATFORM_ARCH"
platform_name=${PLATFORM_NAME:-"openmandriva"}
repo_url="$REPO_URL"
repo_names="$REPO_NAMES"
cache_enable="$CACHE_ENABLE"
default_cfg=/etc/mock/default.cfg

gen_included_repos() {

    names_arr=($repo_names)
    urls_arr=($repo_url)

    for (( i=0; i<${#names_arr[@]}; i++ ));
	do
	    printf "[${names_arr[i]}]\nname=${names_arr[i]}\nbaseurl=${urls_arr[i]}\ngpgcheck=0\nenabled=1\n\n" >> "${default_cfg}"
    done

    # close dnf repos section
    printf '%s\n' '"""' >> "${default_cfg}"
}

if [ "${platform_arch}" = 'aarch64' ]; then
cat <<EOF> $default_cfg
config_opts['target_arch'] = '$platform_arch'
config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'aarch64')
EOF

elif [ "${platform_arch}" = 'armv7hl' ]; then
cat <<EOF> $default_cfg
config_opts['target_arch'] = '$platform_arch'
config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'armv7hl', 'armv7l', 'aarch64')
EOF
else

cat <<EOF> $default_cfg
config_opts['target_arch'] = '$platform_arch'
config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64')
EOF
fi

cat <<EOF>> $default_cfg
config_opts['root'] = '$platform_name-$platform_arch'
config_opts['chroot_setup_cmd'] = ('install', 'basesystem-minimal', 'locales', 'locales-en', 'distro-release-OpenMandriva', 'gnupg', 'shadow', 'rpm-build', 'wget', 'task-devel', 'clang', 'openmandriva-repos-pkgprefs', 'rpmlint-distro-policy', 'dwz')
config_opts['package_manager'] = 'dnf'
config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--forcearch=$platform_arch']
config_opts['dnf_builddep_opts'] = ['--refresh', '--forcearch=$platform_arch']
config_opts['useradd'] = '/usr/sbin/useradd -o -m -u %(uid)s -g %(gid)s -d %(home)s %(user)s'
config_opts['releasever'] = '0' # at some point, this should be set by ABF
config_opts['use_nspawn'] = False

config_opts['basedir'] = '/var/lib/mock/'
config_opts['cache_topdir'] = '/var/cache/mock/'

config_opts['dist'] = 'cooker'  # only useful for --resultdir variable subst
config_opts['macros']['%packager'] = '$uname <$email>'
config_opts['macros']['%_topdir'] = '%s/build' % config_opts['chroothome']
config_opts['macros']['%_rpmfilename'] = '%%{NAME}-%%{VERSION}-%%{RELEASE}-%%{DISTTAG}.%%{ARCH}.rpm'
config_opts['macros']['%cross_compiling'] = '0' # ABF should generally be considered native builds
config_opts['plugin_conf']['ccache_enable'] = False
config_opts['plugin_conf']['root_cache_enable'] = '$cache_enable'
config_opts['plugin_conf']['root_cache_opts']['compress_program'] = "xz"
config_opts['plugin_conf']['root_cache_opts']['extension'] = ".xz"
config_opts['yum.conf'] = """
[main]
keepcache=1
debuglevel=2
reposdir=/dev/null
retries=20
obsoletes=1
gpgcheck=0
assumeyes=1
syslog_ident=mock
syslog_device=
install_weak_deps=0
metadata_expire=0
best=1

EOF

gen_included_repos
