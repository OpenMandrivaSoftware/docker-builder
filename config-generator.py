#!/usr/bin/env python
import os
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
metadata_expire=0
best=1\n"""

def generate_config(uname, email, platform_name, platform_arch, repo_url, repo_names, extra_cfg_options, rebuild_cache):
    uname = os.getenv(uname)
#    if not uname:
#        print("Environment variable: [%s] not set." % (uname))
#        sys.exit(1)
    email = os.getenv(email)
    platform_arch = os.getenv('PLATFORM_ARCH')
    platform_name = os.getenv('PLATFORM_NAME')
    repo_url = os.getenv(repo_url)
    repo_names = os.getenv(repo_names)
    rebuild_cache = os.getenv(rebuild_cache)
    extra_cfg_options = os.getenv(extra_cfg_options)
#    print(uname, email, platform_arch, platform_name, repo_names, repo_url, extra_cfg_options, rebuild_cache)


    if platform_arch == 'aarch64':
        print("config_opts['target_arch'] = '%s'" % platform_arch)
        print("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'aarch64')")
    if platform_arch == "armv7hnl":
        print("config_opts['target_arch'] = '%s'" % platform_arch)
        print("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'armv8hcnl', 'armv8hnl', 'armv8hl', 'armv7hnl', 'armv7hl', 'armv7l', 'aarch64')")
    if platform_arch == "riscv64":
        print("config_opts['target_arch'] = '%s --without check'" % platform_arch)
        print("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64', 'riscv64')")
    if platform_arch == "znver1":
        print("config_opts['target_arch'] = '%s'" % platform_arch)
        print("config_opts['legal_host_arches'] = (x86_64', 'znver1')")
    if platform_arch == "x86_64" or "i686":
        print("config_opts['target_arch'] = '%s'" % platform_arch)
        print("config_opts['legal_host_arches'] = ('i586', 'i686', 'x86_64')")

    print("config_opts['root'] = '%s-%s'" % (platform_name, platform_arch))
    print("config_opts['chroot_setup_cmd'] = ('install', 'basesystem-minimal', 'locales', 'locales-en', 'distro-release-OpenMandriva', 'gnupg', 'shadow', 'rpm-build', 'glibc-devel' ,'wget', 'task-devel', 'openmandriva-repos-pkgprefs', 'rpmlint-distro-policy', 'dwz')")
    print("config_opts['package_manager'] = 'dnf'")
    print("config_opts['dnf_common_opts'] = ['--refresh', '--disableplugin=local', '--setopt=deltarpm=False', '--forcearch=%s']" % platform_arch)
    print("config_opts['dnf_builddep_opts'] = ['--refresh', '--forcearch=%s']" % platform_arch)
    print("config_opts['useradd'] = '/usr/sbin/useradd -o -m -u %(uid)s -g %(gid)s -d %(home)s %(user)s'")
    print("config_opts['releasever'] = '0'")
    print("config_opts['use_nspawn'] = False")
    print("config_opts['tar'] = 'bsdtar'")
    print("config_opts['basedir'] = '/var/lib/mock/'")
    print("config_opts['cache_topdir'] = '/var/cache/mock/'")
    print("config_opts['nosync'] = True")
    # enable tmpfs for builder with 64gb+
    print("config_opts['plugin_conf']['tmpfs_enable'] = True")
    print("config_opts['plugin_conf']['tmpfs_opts'] = {}")
    print("config_opts['plugin_conf']['tmpfs_opts']['required_ram_mb'] = 64000")
    print("config_opts['plugin_conf']['tmpfs_opts']['max_fs_size'] = '80%'")
    print("config_opts['plugin_conf']['tmpfs_opts']['mode'] = '0755'")
    print("config_opts['plugin_conf']['tmpfs_opts']['keep_mounted'] = False")

    print("config_opts['dist'] = '%s'" % platform_name)
    print("config_opts['macros']['%%packager'] = '%s <%s>'" % (uname, email))
    print("config_opts['macros']['%_topdir'] = '%s/build' % config_opts['chroothome']")
    print("config_opts['macros']['%_rpmfilename'] = '%%{NAME}-%%{VERSION}-%%{RELEASE}-%%{DISTTAG}.%%{ARCH}.rpm'")
    print("config_opts['macros']['%cross_compiling'] = '0' # ABF should generally be considered native builds")
    print("config_opts['plugin_conf']['ccache_enable'] = False")
    print("config_opts['plugin_conf']['root_cache_opts']['compress_program'] = ''")
    print("config_opts['plugin_conf']['root_cache_opts']['extension'] = ''")
    print("config_opts['plugin_conf']['root_cache_enable'] = True")
    print("config_opts['plugin_conf']['root_cache_opts']['age_check'] = True")
    print("config_opts['plugin_conf']['root_cache_opts']['max_age_days'] = 1")
    print("config_opts['plugin_conf']['package_state_enable'] = True")
    print("config_opts['plugin_conf']['package_state_opts'] = {}")
    print("config_opts['plugin_conf']['package_state_opts']['available_pkgs'] = False")
    print("config_opts['plugin_conf']['package_state_opts']['installed_pkgs'] = True")
    print(common_string)
    repo_names = repo_names.split()
    repo_urls = repo_url.split()
    repo_conf = dict(zip(repo_names, repo_urls))
    print("\n".join("[{}]\nname={} {}\n{}\ngpgcheck=0\nenabled=1\n".format(k, k, k[:0], v) for k, v in repo_conf.items()))
    print('"""')

generate_config('UNAME',
                'EMAIL',
                'PLATFORM_NAME',
                'PLATFORM_ARCH',
                'REPO_URL',
                'REPO_NAMES',
                'EXTRA_CFG_OPTIONS', 'REBUILD_CACHE')
