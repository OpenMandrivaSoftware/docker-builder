#!/usr/bin/env python3
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
        print("Can't write to log file: " + conf)
    # print(message)


def generate_config():
    if os.path.exists(conf):
        os.remove(conf)  # this deletes the file

    uname = os.getenv('UNAME')
    if not uname:
        print("Environment variable: [%s] not set." % (uname))
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
        print_conf("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'riscv64')")
    if platform_arch == "znver1":
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('x86_64', 'znver1')")
    if platform_arch == "e2kv4":
        # use e2kv4 march option
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('x86_64', 'e2k')")
    accepted_arches = {'x86_64', 'i686', 'i586'}
    if platform_arch in accepted_arches:
        print_conf("config_opts['target_arch'] = '%s'" % platform_arch)
        print_conf("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64')")

    print_conf("config_opts['root'] = '%s-%s'" % (platform_name, platform_arch))
    print_conf("config_opts['chroot_setup_cmd'] = ('install', 'basesystem-build', 'dwz', 'dnf', 'magic-devel')")
    print_conf("config_opts['package_manager'] = 'dnf'")
    print_conf("config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--setopt=install_weak_deps=False', '--setopt=tsflags=nodocs', '--forcearch=%s']" % platform_arch)
    print_conf("config_opts['dnf_builddep_opts'] = ['--refresh', '--forcearch=%s']" % platform_arch)
    print_conf("config_opts['useradd'] = '/usr/sbin/useradd -o -m -u {{chrootuid}} -g {{chrootgid}} -d {{chroothome}} {{chrootuser}}'")
    print_conf("config_opts['releasever'] = '0'")
    print_conf("config_opts['rpmbuild_networking'] = False")
    # print_conf("config_opts['plugin_conf']['bind_mount_enable'] = True")
    # print_conf("config_opts['plugin_conf']['bind_mount_opts']['dirs'].append(('/etc/hosts', '/etc/resolv.conf'))")
    print_conf("config_opts['rpmbuild_timeout'] = 86400")
    print_conf("config_opts['isolation'] = 'simple'")
    print_conf("config_opts['use_nspawn'] = False")
    print_conf("config_opts['tar'] = 'gnutar'")
    print_conf("config_opts['use_bootstrap'] = False")
    print_conf("config_opts['basedir'] = '/var/lib/mock/'")
    print_conf("config_opts['cache_topdir'] = '/var/cache/mock/'")
    print_conf("config_opts['nosync'] = False")
    print_conf("config_opts['dynamic_buildrequires'] = True")
    # https://github.com/rpm-software-management/mock/issues/661
    print_conf("config_opts['nosync_force'] = False")
    # compress logs
    print_conf("config_opts['plugin_conf']['compress_logs_enable'] = True")
    print_conf("config_opts['plugin_conf']['compress_logs_opts']['command'] = '/usr/bin/gzip -9 --force'")
    # Some packages (at the moment, gcc, llvm and glibc - due to
    # crosscompilers being built in the same source tree - and chromium
    # because it's simply inefficient code), require LOADS of space for
    # the BUILD and BUILDROOT directories - causing them to fail even
    # on a rather generous tmpfs
    huge_packages = ['gcc', 'llvm', 'glibc', 'chromium-browser-stable', 'chromium-browser-beta', 'chromium-browser-dev', 'qt6-qtwebengine']
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
    if platform_arch == "e2k":
        print_conf("config_opts['macros']['%debug_package'] = '%{nil}'")
    print_conf("config_opts['plugin_conf']['ccache_enable'] = False")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['compress_program'] = ''")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['extension'] = ''")
    print_conf("config_opts['plugin_conf']['root_cache_enable'] = True")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['age_check'] = True")
    print_conf("config_opts['plugin_conf']['root_cache_opts']['max_age_days'] = 1")
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
