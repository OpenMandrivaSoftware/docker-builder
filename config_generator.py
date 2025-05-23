#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from stat import *
import os
import sys
common_string = """
config_opts['yum.conf'] = \"\"\"
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
metadata_expire=60s
best=1\n"""

conf = '/etc/mock/default.cfg'

def print_conf(message):
    try:
        logFile = open(conf, 'a')
        logFile.write(message + '\n')
        logFile.close()
    except:
        print("BUILDER: Can't write to log file: " + conf)
    # print(message)


def generate_config():
    print("BUILDER: Starting script: config_generator.py")

    if os.path.exists(conf):
        os.remove(conf)  # this deletes the file

    uname = os.getenv('UNAME')
    if not uname:
        print("BUILDER: Environment variable: [%s] not set." % (uname))
        sys.exit(1)
    email = os.getenv('EMAIL')
    platform_arch = os.getenv('PLATFORM_ARCH')
    platform_name = os.getenv('PLATFORM_NAME')
    repo_url = os.getenv('REPO_URL')
    repo_names = os.getenv('REPO_NAMES')
    rebuild_cache = os.getenv('REBUILD_CACHE')
    extra_cfg_options = os.getenv('EXTRA_CFG_OPTIONS')
    save_buildroot = os.environ.get('SAVE_BUILDROOT')

    if platform_arch == 'aarch64':
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'aarch64')")
    if platform_arch == "armv7hnl":
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'armv8hcnl', 'armv8hnl', 'armv8hl', 'armv7hnl', 'armv7hl', 'armv7l', 'aarch64')")
    if platform_arch == "riscv64":
        print_conf("config_opts['target_arch'] = '%s --without check --without pgo'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'riscv64', 'aarch64')")
    if platform_arch == "znver1":
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('x86_64', 'znver1')")
    if platform_arch == "loongarch64":
        print_conf("config_opts['target_arch'] = '%s --without check --without webkit --without mono'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('loongarch64')")
    if platform_arch == "e2kv4":
        # use e2kv4 march option
        print_conf("config_opts['target_arch'] = '%s --without check'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('e2kv6', 'e2k', 'e2kv4')")
        if os.getenv('PACKAGE') and os.getenv('PACKAGE').startswith(('qt5-', 'qt6-', 'qt-')):
            # We can't use nodocs with qt5-* packages because docs for
            # one package need to access docs for other packages to
            # crossreference them
            print_conf("config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--forcearch=e2k']")
        else:
            print_conf("config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--setopt=tsflags=nodocs', '--forcearch=e2k']")
        print_conf("config_opts['dnf_builddep_opts'] = ['--refresh', '--forcearch=e2k']")
    else:
        if os.getenv('PACKAGE') and os.getenv('PACKAGE').startswith(('qt5-', 'qt6-', 'qt-', 'kf6-')):
            # We can't use nodocs with qt5-* packages because docs for
            # one package need to access docs for other packages to
            # crossreference them
            print_conf("config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--forcearch=%s']" % platform_arch)
            print_conf("config_opts['dnf5_common_opts'] = ['--refresh', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--no-gpgchecks']")
        else:
            print_conf("config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--setopt=tsflags=nodocs', '--forcearch=%s']" % platform_arch)
            print_conf("config_opts['dnf5_common_opts'] = ['--refresh', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--no-gpgchecks', '--no-docs' ]")
        print_conf("config_opts['dnf_builddep_opts'] = ['--refresh', '--forcearch=%s']" % platform_arch)

    accepted_arches = {'x86_64', 'i686', 'i586'}
    if platform_arch in accepted_arches:
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64')")

    print_conf("config_opts['root'] = '%s-%s'" % (platform_name, platform_arch))
    print_conf("config_opts['chroot_setup_cmd'] = ['--refresh', 'install', 'basesystem-build', 'dnf', 'dwz', 'magic-devel', '--forcearch=%s']" % platform_arch)
    # Keep using dnf4 on 6.0, everything else is moving on
    if platform_name == "6.0":
        print_conf("config_opts['package_manager'] = 'dnf'")
    else:
        print_conf("config_opts['package_manager'] = 'dnf5'")

    print_conf("config_opts['dnf5_command'] = '/usr/bin/dnf5'")
    print_conf("config_opts['system_dnf5_command'] = '/usr/bin/dnf5'")
    print_conf("config_opts['dnf5_install_command'] = 'install dnf5'")
    print_conf("config_opts['dnf5_disable_plugins'] = []")
    # No --allowerasing with remove, per
    # https://github.com/rpm-software-management/dnf5/issues/729
    print_conf("config_opts['dnf5_avoid_opts'] = {'remove': ['--allowerasing']}")
    print_conf("config_opts['plugin_conf']['hw_info_enable'] = False")
    print_conf("config_opts['releasever'] = '0'")
    if any(keyword in repo_url for keyword in ['contrib', 'unsupported']):
        print_conf("config_opts['rpmbuild_networking'] = True")
    else:
        print_conf("config_opts['rpmbuild_networking'] = False")
    print_conf("config_opts['use_host_resolv'] = True")
    print_conf("config_opts['plugin_conf']['bind_mount_enable'] = True")
    print_conf("config_opts['package_manager_max_attempts'] = 3")
    print_conf("config_opts['package_manager_attempt_delay'] = 15")
    # chromium with CFE can take a lot longer than 36000 seconds (10 hours)...
    # gcc can take even longer when building all combinations of crosscompilers
    # and offload targets.
    if os.getenv('PACKAGE') and os.getenv('PACKAGE').startswith(('gcc')):
        print_conf("config_opts['rpmbuild_timeout'] = 144000")
    elif os.getenv('PACKAGE') and os.getenv('PACKAGE').startswith(('chromium', 'llvm', 'nodejs', 'qt6-qtwebengine', 'rust')):
        print_conf("config_opts['rpmbuild_timeout'] = 72000")
    else:
        print_conf("config_opts['rpmbuild_timeout'] = 36000")
    print_conf("config_opts['isolation'] = 'simple'")
    print_conf("config_opts['use_nspawn'] = False")
#    print_conf("config_opts['tar'] = 'bsdtar'")
    print_conf("config_opts['opstimeout'] = 18000")
    print_conf("config_opts['use_bootstrap'] = False")
    print_conf("config_opts['basedir'] = '/var/lib/mock/'")
    print_conf("config_opts['cache_topdir'] = '/var/cache/mock/'")
    print_conf("config_opts['nosync'] = False")
    print_conf("config_opts['dynamic_buildrequires'] = True")
    # https://github.com/rpm-software-management/mock/issues/661
    print_conf("config_opts['nosync_force'] = False")
    print_conf("config_opts['ssl_ca_bundle_path'] = None")
    print_conf("config_opts['ssl_extra_certs'] = None")
    # compress logs
    print_conf("config_opts['plugin_conf']['compress_logs_enable'] = True")
    print_conf("config_opts['plugin_conf']['compress_logs_opts']['command'] = '/usr/bin/gzip -9 --force'")
    # Some packages (at the moment, gcc, llvm and glibc - due to
    # crosscompilers being built in the same source tree - and chromium
    # because it's simply inefficient code), require LOADS of space for
    # the BUILD and BUILDROOT directories - causing them to fail even
    # on a rather generous tmpfs
    huge_packages = ['gcc', 'llvm', 'glibc', 'chromium', 'chromium-browser-stable', 'chromium-browser-beta', 'chromium-browser-dev', 'qt6-qtwebengine', 'rust']
    # enable tmpfs for builder with 64gb+
    # only if save_buildroot is false and the package isn't blacklisted
    if save_buildroot != 'true' and not os.getenv('PACKAGE') in huge_packages:
        print_conf("config_opts['plugin_conf']['tmpfs_enable'] = True")
        print_conf("config_opts['plugin_conf']['tmpfs_opts'] = {}")
        print_conf("config_opts['plugin_conf']['tmpfs_opts']['required_ram_mb'] = 64000")
        print_conf("config_opts['plugin_conf']['tmpfs_opts']['max_fs_size'] = '80%'")
        print_conf("config_opts['plugin_conf']['tmpfs_opts']['mode'] = '0755'")
        print_conf("config_opts['plugin_conf']['tmpfs_opts']['keep_mounted'] = False")

    print_conf("config_opts['dist'] = '%s'" % platform_name)
    print_conf("config_opts['macros']['%%packager'] = '%s <%s>'" % (uname, email))
    print_conf("config_opts['macros']['%_topdir'] = '%s/build' % config_opts['chroothome']")
    print_conf("config_opts['macros']['%_rpmfilename'] = '%%{NAME}-%%{VERSION}-%%{RELEASE}-%%{DISTTAG}.%%{ARCH}.rpm'")
    print_conf("config_opts['macros']['%cross_compiling'] = '0' # ABF should generally be considered native builds")
    if platform_arch == "e2kv4":
        print_conf("config_opts['macros']['%debug_package'] = '%{nil}'")
    print_conf("config_opts['plugin_conf']['ccache_enable'] = False")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['compress_program'] = ''")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['extension'] = ''")
    print_conf("config_opts['plugin_conf']['root_cache_enable'] = True")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['age_check'] = True")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['max_age_days'] = 3")
    print_conf("config_opts['plugin_conf']['package_state_enable'] = True")
    print_conf("config_opts['plugin_conf']['package_state_opts'] = {}")
    print_conf("config_opts['plugin_conf']['package_state_opts']['available_pkgs'] = False")
    print_conf("config_opts['plugin_conf']['package_state_opts']['installed_pkgs'] = True")
    print_conf(common_string)
    repo_names = repo_names.split()
    repo_urls = repo_url.split()
    repo_conf = dict(zip(repo_names, repo_urls))
    print_conf("\n".join("[{}]\nname={}\nbaseurl={}{}\ngpgcheck=0\nenabled=1\n".format(k, k, k[:0], v) for k, v in repo_conf.items()))
    print_conf('"""')
    # it's a hack to modify time of /etc/mock/default.cfg
    # to prevent root cache recreation
    # and yes, mock recreates whole cache
    # if default.cfg were changed
    st = os.stat(conf)
    atime = st[ST_ATIME]  # access time
    mtime = st[ST_MTIME]  # modification time
    # rebuild cache every 4 hours
    new_mtime = mtime - (4*3600)
    os.utime(conf, (atime, new_mtime))
