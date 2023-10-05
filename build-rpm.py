#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import yaml
import requests
import json
import sys
import time
import rpm
import hashlib
import io
import mmap
import re
import config_generator
import check_error
import magic
import gzip
import struct
import socket

get_home = os.environ.get('HOME')
package = os.environ.get('PACKAGE')
git_repo = os.environ.get('GIT_REPO')
# FIXME workaround for https://github.com/OpenMandrivaSoftware/rosa-build/issues/161
if git_repo[0:17] == 'git://github.com/':
    git_repo='https://github.com/' + git_repo[17:]

file_store_base = os.environ.get('FILE_STORE_ADDR')
build_package = get_home + '/' + package

if os.environ.get('COMMIT_HASH') is None:
    project_version = os.environ.get('PROJECT_VERSION')
else:
    project_version = os.environ.get('COMMIT_HASH')

extra_build_src_rpm_options = list(filter(None, [x for x in os.environ.get('EXTRA_BUILD_SRC_RPM_OPTIONS', '').split(' ') if x]))
extra_build_rpm_options = list(filter(None, [x for x in os.environ.get('EXTRA_BUILD_RPM_OPTIONS', '').split(' ') if x]))
platform_arch = os.environ.get('PLATFORM_ARCH')
platform_name = os.environ.get('PLATFORM_NAME')
rerun_tests = os.environ.get('RERUN_TESTS')
use_extra_tests = os.environ.get("USE_EXTRA_TESTS")
save_buildroot = os.environ.get('SAVE_BUILDROOT')
#print(os.environ.keys())

# static
# /home/omv/output
mock_binary = '/usr/bin/mock'
mock_config = '/etc/mock/'
output_dir = get_home + '/output'
c_data = output_dir + '/container_data.json'
root_log = output_dir + '/root.log.gz'

spec_name = []
rpm_packages = []
src_rpm = []
logfile = output_dir + '/' + 'test.' + time.strftime("%m-%d-%Y-%H-%M-%S") + '.log'

def is_valid_hostname(hostname):
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    if len(hostname) > 255:
        return False
    if re.match(r"[a-f0-9]{12}", hostname.split(".")[0]):
        print("BUILDER: container hostname does not pass naming policy [{}]".format(hostname))
        return False
    else:
        print("BUILDER: hostname: {} linting passed".format(hostname))
        return True


def print_log(message):
    try:
        logger = open(logfile, 'a')
        logger.write(message + '\n')
        logger.close()
    except IOError:
        print("BUILDER: Can't write to log file: " + logfile)
    print(message)


def get_size(filename):
    file_stats = os.stat(filename)
    return file_stats.st_size


def download_hash(hashsum, pkg_name=''):
    fstore_json_url = '{}/api/v1/file_stores.json?hash={}'.format(
        file_store_base, hashsum)
    fstore_file_url = '{}/api/v1/file_stores/{}'.format(
        file_store_base, hashsum)
    resp = requests.get(fstore_json_url)
    if resp.status_code == 404:
        print("BUILDER: requested file [{}] not found".format(
            fstore_json_url))
    if resp.status_code == 200:
        # this code responsible for fetching names from abf
        # we not using it because of in names with +, + replaces with _
        # e.g gtk-_3.0
        if not pkg_name:
            page = resp.content.decode('utf-8')
            page2 = json.loads(page)
            pkg_name = page2[0]['file_name']
        download_file = requests.get(fstore_file_url, stream=True)
        source_tarball = build_package + '/' + pkg_name
        with open(source_tarball, 'wb') as f:
            for chunk in download_file.iter_content(chunk_size=1048576):
                if chunk:
                    f.write(chunk)


def remove_changelog(spec):
    if os.path.isfile(spec):
        try:
            subprocess.check_output(['sed', '-i', '/%changelog/,$d', spec])
        except subprocess.CalledProcessError as e:
            print(e.output)
            pass

def validate_spec(path):
    spec = [f for f in os.listdir(path) if f.endswith('.spec')]
    if len(spec) > 1:
        print("BUILDER: found more than 1 RPM spec file in %s" % path)
        sys.exit(1)
    elif len(spec) == 0:
        print("BUILDER: no RPM spec file found.")
        sys.exit(1)
    else:
        print("BUILDER: RPM spec file name is %s" % spec[0])
        spec_name.append(spec[0])
        print("BUILDER: single RPM spec file in build directory, check passed")
        # print("cleanup %changelog entries")
        # remove_changelog(path + '/' + spec[0])


def download_yml(yaml_file):
    if os.path.exists(yaml_file) and os.path.isfile(yaml_file):
        try:
            data = yaml.safe_load(open(yaml_file))
        except yaml.YAMLError as e:
            print("BUILDER: Error parsing .abf.yml: %s" % e)
            sys.exit(1)
        if ('sources' not in data) or len(data['sources']) == 0:
            print("BUILDER: WARNING: .abf.yml contains no or empty sources section")
        else:
            for key, value in data['sources'].items():
                print("BUILDER: downloading source %s" % key)
                download_hash(value, key)
    else:
        print("BUILDER: .abf.yml not found")

# func to remove leftovers
# from prev. build


def remove_if_exist(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            try:
                subprocess.check_output(['/usr/bin/sudo', '-E', 'rm', '-rf', path])
                print("BUILDER: removed %s" % path)
            except subprocess.CalledProcessError as e:
                print(e.output)
                return
        if os.path.isfile(path):
            try:
                subprocess.check_output(['/usr/bin/sudo', '-E', 'rm', '-f', path])
                print("BUILDER: removed %s" % path)
            except subprocess.CalledProcessError as e:
                print(e.output)
                return


def clone_repo(git_repo, project_version):
    remove_if_exist(build_package)
    tries = 5
    for i in range(tries):
        try:
            print("BUILDER: Git repository cloning [{}], branch: [{}] to [{}]".format(git_repo, project_version, build_package))
            # please do not change this string
            # ROSA really use checkout to build specific commits
            subprocess.check_output(['git', 'clone', git_repo, build_package], timeout=3600, env={'LC_ALL': 'C.UTF-8'})
            subprocess.check_output(['git', 'checkout', project_version], cwd=build_package, timeout=3600, env={'LC_ALL': 'C.UTF-8'})
        except subprocess.CalledProcessError:
            if i < tries - 1:
                time.sleep(5)
                continue
            else:
                print("BUILDER: can not checkout the repository %s" % git_repo)
                sys.exit(1)
        break
    # generate commit_id
    git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=build_package, timeout=3600, env={'LC_ALL': 'C.UTF-8'})
    print(git_commit.decode('utf-8'), file=open(get_home + '/commit_hash', "a"))


def hash_file(rpm):
#    This function returns the SHA-1 hash
#    of the file passed into it

    # make a hash object
    h = hashlib.sha1()
    # open file for reading in binary mode
    with open(rpm, 'rb') as file:
        # loop till the end of the file
        chunk = 0
        while chunk != b'':
            # read only 1 Mbyte at a time
            chunk = file.read(1048576)
            h.update(chunk)
    # return the hex representation of digest
    return h.hexdigest()

def readRpmHeader(ts, filename):
    """ Read an rpm header. """
    fd = os.open(filename, os.O_RDONLY)
    h = ts.hdrFromFdno(fd)
    os.close(fd)
    return h

def validate_exclusive(srpm):
    """ Validate SRPM for ExcludeArch and/or ExclusiveArch. """
    rpm_ts = rpm.TransactionSet()
    rpm_ts.setVSFlags(~(rpm.RPMVSF_NEEDPAYLOAD))
    rpm_hdr = readRpmHeader(rpm_ts, srpm)
    if rpm_hdr['excludearch']:
        for a in rpm_hdr['excludearch']:
            if a == platform_arch:
                print("BUILDER: Architecture is excluded in RPM spec file (ExcludeArch tag)")
                sys.exit(6)
    if rpm_hdr['exclusivearch']:
        linted_arch = []
        for excl_arch in rpm_hdr['exclusivearch']:
            linted_arch.append(excl_arch)
        if platform_arch in linted_arch:
            print("BUILDER: ExclusiveArch header passed for %s" % platform_arch)
        else:
            print("BUILDER: ExclusiveArch test failed. Check RPM spec file for ExclusiveArch tag")
            sys.exit(6)


def container_data():
    """ Create container data for ABF, based on on RPM files. """
    rpm_ts = rpm.TransactionSet()
    multikeys = []
#    rpm_packages = ['/home/fdrt/output/libinput10-1.13.2-1-omv4000.i686.rpm']
    for pkg in rpm_packages:
        # Do not check src.srm
        rpm_hdr = readRpmHeader(rpm_ts, pkg)
        if rpm_hdr['epoch']:
            epoch = rpm_hdr['epoch']
        else:
            epoch = 0
        shasum = hash_file(pkg)
        # init empty list
        full_list = []
        if not os.path.basename(pkg).endswith("src.rpm"):
            try:
                dependencies = subprocess.check_output(['dnf5', 'repoquery', '-q', '--latest-limit=1', '--qf', '%{NAME}', '--whatrequires', rpm_hdr['name']], timeout=3600, env={'LC_ALL': 'C.UTF-8'})
                full_list = dependencies.decode().split('\n')
            except subprocess.CalledProcessError:
                print("BUILDER: A problem occured when running dnf repoquery for %s" % name)
        package_info = dict([('name', rpm_hdr['name']), ('version', rpm_hdr['version']), ('release', rpm_hdr['release']), ('size', get_size(pkg)), ('epoch', epoch), ('fullname', pkg.split('/')[-1]), ('sha1', shasum), ('dependent_packages', ' '.join(full_list))])
        multikeys.append(package_info)
    with open(c_data, 'w') as out_json:
        json.dump(multikeys, out_json, sort_keys=True, separators=(',', ':'))


def extra_tests(only_rpms):
    # here only rpm packages, not debuginfo or debugsource
    skip_debuginfo = [s for s in only_rpms if "debuginfo" not in s and "debugsource" not in s and "src.rpm" not in s]
    # check_package
    try:
        print("BUILDER: test installing %s" % list(only_rpms))
        subprocess.check_call([mock_binary, '--init', '--quiet', '--configdir', mock_config, '--install'] + list(skip_debuginfo))
        shutil.copy('/var/lib/mock/{}-{}/result/root.log'.format(platform_name, platform_arch), logfile)
        print("BUILDER: all tested packages successfully installed")
    except subprocess.CalledProcessError as cpe:
        print("BUILDER: %s failed with exit status %u" % (cpe.cmd, cpe.returncode))
        print("BUILDER: Extra tests stderr: %s" % (cpe.stderr))
        shutil.copy('/var/lib/mock/{}-{}/result/root.log'.format(platform_name, platform_arch), logfile)
        # tests failed
        sys.exit(5)
    # stage2
    # check versions
    rpm_ts = rpm.TransactionSet()
    try:
        for pkg in skip_debuginfo:
            rpm_hdr = readRpmHeader(rpm_ts, pkg)
            rpm_name = rpm_hdr['name']
            if rpm_hdr['epoch']:
                rpm_epoch = rpm_hdr['epoch']
            else:
                rpm_epoch = 0
            rpm_evr = '{}:{}-{}'.format(rpm_epoch, rpm_hdr['version'], rpm_hdr['release'])
            tries = 0
            while tries < 3:
                check_string = 'LC_ALL=C.UTF-8 dnf5 {} repoquery -q --qf %{{EPOCH}}:%{{VERSION}}-%{{RELEASE}} --latest-limit=1 {}'.format("--refresh" if tries > 0 else "", rpm_name)
                try:
                    print("BUILDER: getting RPM version from repository")
                    inrepo_version = subprocess.check_output([mock_binary, '--enable-network', '--shell', '-v', '--', check_string], stderr=subprocess.PIPE ).decode('utf-8')
                    print_log("BUILDER: repository version of this package is : {}".format(inrepo_version))
                    break
                except subprocess.CalledProcessError as e:
                    print(e)
                    print("BUILDER: {} returned with exit code {}".format(e.cmd, e.returncode))
                    print("BUILDER: getting RPM version stdout: %s" % (e.stdout))
                    print("BUILDER: getting RPM version stderr: %s" % (e.stderr))
                    # Let's see if it's a connection problem...
                    try:
                        hostname = 'google.com'
                        host = socket.gethostbyname(hostname)
                        s = socket.create_connection((host, 80), 2)
                        s.close
                        print("BUILDER: Network seems to be up")
                    except subprocess.CalledProcessError as cpe:
                        print("BUILDER: Seems to be a connectivity problem:{}".format(cpe))
                    # This can happen while metadata is being updated, so
                    # let's try again
                    tries += 1
                    if tries >= 3:
                        sys.exit(5)
                    time.sleep(5)
            # rpmdev-vercmp 0:7.4.0-1 0:7.4.0-1
            inrepo_version = 0 if not inrepo_version else inrepo_version
            print_log("BUILDER: repository package version is: %s" % inrepo_version)

            try:
                print_log("BUILDER: running rpmdev-vercmp %s %s" % (rpm_evr, str(inrepo_version)))
                a = subprocess.check_call(['rpmdev-vercmp', rpm_evr, str(inrepo_version)])
                if a == 0:
                    print_log("BUILDER: Package {} is either the same, older, or another problem. Extra tests failed".format(rpm_name))
                    sys.exit(5)
            except subprocess.CalledProcessError as e:
                exit_code = e.returncode
                if exit_code == 11:
                    print_log("BUILDER: package is newer than in repository")
                    sys.exit(0)
                print_log("BUILDER: package is older, the same version as in repository or other issue")
                sys.exit(5)
    except subprocess.CalledProcessError as e:
        print_log(e)
        print_log("BUILDER: failed to compare package versions with repository")
        sys.exit(5)


def save_build_root():
    if save_buildroot == 'true':
        saveroot = '/var/lib/mock/{}-{}/root/'.format(platform_name, platform_arch)
        try:
            subprocess.check_output(['sudo', 'tar', '-czf', output_dir + '/buildroot.tar.gz', saveroot])
            print_log("BUILDER: build root contents was saved to buildroot.tar.gz")
        except subprocess.CalledProcessError as e:
            print_log(e)
            print_log("BUILDER: failed to create buildroot.tar.gz")


def relaunch_tests():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    config_generator.generate_config()
    # clone repo and generate config
    clone_repo(git_repo, project_version)
    packages = os.getenv('PACKAGES')
    for package in packages.split():
        print("BUILDER: downloading package {} for testing".format(package))
        # download packages to /home/omv/pkg_name/
        download_hash(package)
        # build package is /home/omv/pkg_name
    for r, d, f in os.walk(build_package):
        for rpm_pkg in f:
            if rpm_pkg.endswith('.rpm'):
                rpm_packages.append(build_package + '/' + rpm_pkg)
    for r, d, f in os.walk(build_package):
        for srpm in f:
            if '.src.rpm' in srpm:
                src_rpm.append(build_package + '/' + srpm)
    # exclude src.rpm
    only_rpms = set(rpm_packages) - set(src_rpm)
    extra_tests(only_rpms)


def build_rpm():
    config_generator.generate_config()
    tries = 5
    # pattern for retry
    pattern_for_retry = '(.*)(Failed to download|Error downloading)(.*)'
    if not os.environ.get('MOCK_CACHE'):
        # /var/cache/mock/cooker-x86_64/root_cache/
        print("BUILDER: MOCK_CACHE is none, than need to clear platform cache")
        remove_if_exist('/var/cache/mock/{}-{}/root_cache/'.format(platform_name, platform_arch))
    for i in range(tries):
        try:
            print("BUILDER: Starting to build SRPM.")
            subprocess.check_output([mock_binary, '--update', '--quiet', '--configdir', mock_config, '--buildsrpm', '--spec=' + build_package + '/' + spec_name[0], '--source=' + build_package, '--no-cleanup-after'] + extra_build_src_rpm_options + ['--resultdir=' + output_dir])
        except subprocess.CalledProcessError as e:
            if i < tries - 1:
                print("BUILDER: something went wrong with SRPM creation, usually it is bad metadata or missed sources in .abf.yml")
                # remove cache dir
                remove_if_exist('/var/cache/mock/{}-{}/dnf_cache/'.format(platform_name, platform_arch))
                continue
            if i == tries - 1:
                print(e)
                raise
        break

    for r, d, f in os.walk(output_dir):
        for srpm in f:
            if '.src.rpm' in srpm:
                src_rpm.append(output_dir + '/' + srpm)
    print("BUILDER: created SRPM is %s" % src_rpm[0])
    # validate src.rpm here
    validate_exclusive(src_rpm[0])
    # for exclusive_arches
    for i in range(tries):
        try:
            print("BUILDER: building RPM")
            subprocess.check_output([mock_binary, '-v', '--update', '--configdir', mock_config, '--rebuild', src_rpm[0],
                    '--no-cleanup-after', '--no-clean'] + extra_build_rpm_options + ['--resultdir=' + output_dir])
        except subprocess.CalledProcessError as e:
            # check here that problem not related to metadata
            print(e)
            if os.path.exists(root_log) and os.path.getsize(root_log) > 0:
                sz = os.path.getsize(root_log)
                if magic.detect_from_filename(root_log).mime_type == 'application/gzip':
                    handle = open(root_log, "r")
                    # let's mmap piece of memory
                    # as we unpacked gzip
                    tmp_mm = mmap.mmap(handle.fileno(), sz, access=mmap.ACCESS_READ)
                    real_sz = struct.unpack("@I", tmp_mm[-4:])[0]
                    mm = mmap.mmap(-1, real_sz, prot=mmap.PROT_READ | mmap.PROT_WRITE)
                    gz = gzip.GzipFile(fileobj=tmp_mm)
                    for line in gz:
                        mm.write(line)
                    tmp_mm.close()
                    error = re.search(pattern_for_retry.encode(), mm)
                    gz.close()
                    handle.close()
                    mm.close()
                else:
                    msgf = io.open(root_log, "r", encoding="utf-8")
                    mm = mmap.mmap(msgf.fileno(), sz, access=mmap.ACCESS_READ)
                    error = re.search(pattern_for_retry.encode(), mm)
                    msgf.close()
                    mm.close()
                # probably metadata not ready
                if error:
                    # print(error.group().decode())
                    if i < tries - 1:
                        print("BUILDER: problems with metadata in repository, restarting build in 60 seconds")
                        # remove cache dir
                        remove_if_exist('/var/cache/mock/{}-{}/dnf_cache/'.format(platform_name, platform_arch))
                        time.sleep(60)
                        continue
                    if i == tries - 1:
                        raise
                else:
                    print("BUILDER: building RPM failed")
                    # /usr/bin/python /mdv/check_error.py --file "${OUTPUT_FOLDER}"/root.log >> ~/build_fail_reason.log
                    # add here check_error.py
                    check_error.known_errors(root_log, get_home + '/build_fail_reason.log')
                    # function to make tar.xz of target platform
                    save_build_root()
                    remove_if_exist(build_package)
                    sys.exit(1)
            else:
                sys.exit(1)
        break
    for r, d, f in os.walk(output_dir):
        for rpm_pkg in f:
            if rpm_pkg.endswith('.rpm'):
                rpm_packages.append(output_dir + '/' + rpm_pkg)
    # rpm packages
    print(rpm_packages)
    container_data()
    save_build_root()
    if use_extra_tests == 'true':
        only_rpms = set(rpm_packages) - set(src_rpm)
        extra_tests(only_rpms)


def cleanup_all():
    print("BUILDER: Cleaning up the environment")
    # wipe letfovers
    # MASK me if you run the script under your user
    # it will wipe whole your /home/user dir
    for dirpath, dirnames, filenames in os.walk(get_home):
        for name in dirnames:
            shutil.rmtree(os.path.join(dirpath, name))
    # files
    # clean not umounted dirs by mock
    umount_dirs = ["/root/var/cache/dnf", "/root/var/cache/yum", "/root/proc", "/root/sys", "/root/dev/pts", "/root/dev/shm"]
    for dirs in ["/var/lib/mock/{}-{}".format(platform_name, platform_arch) + s for s in umount_dirs]:
      if os.path.exists(dirs):
        try:
          subprocess.check_output(['sudo', 'umount', '-ql', dirs], text=True)
        except subprocess.CalledProcessError as e:
          print(e.output)
          continue

    remove_if_exist('/etc/rpm/platform')
    remove_if_exist('/var/lib/mock/{}-{}/result/'.format(platform_name, platform_arch))
    remove_if_exist('/var/lib/mock/{}-{}/root/builddir/'.format(platform_name, platform_arch))
    # /home/omv/package_name
    remove_if_exist(build_package)
    remove_if_exist(get_home + '/build_fail_reason.log')
    remove_if_exist(get_home + '/commit_hash')
    remove_if_exist(output_dir)


if __name__ == '__main__':
    print("BUILDER: Starting script: build-rpm.py")
    print("BUILDER: Re-running tests? %s" % rerun_tests)
    cleanup_all()
    if is_valid_hostname(socket.gethostname()) is False:
        sys.exit(1)
    if rerun_tests is not None:
        relaunch_tests()
    else:
        clone_repo(git_repo, project_version)
        validate_spec(build_package)
        download_yml(build_package + '/' + '.abf.yml')
        build_rpm()
