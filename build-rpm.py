#!/usr/bin/env python
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

get_home = os.environ.get('HOME')
package = os.environ.get('PACKAGE')
git_repo = os.environ.get('GIT_REPO')
file_store_base = os.environ.get('FILE_STORE_ADDR')
build_package = get_home + '/' + package

if os.environ.get("COMMIT_HASH") is None:
    project_version = os.environ.get('PROJECT_VERSION')
else:
    project_version = os.environ.get('COMMIT_HASH')

if os.environ.get("EXTRA_BUILD_SRC_RPM_OPTIONS") is None:
    extra_build_src_rpm_options = ''
else:
    extra_build_src_rpm_options = os.environ.get('EXTRA_BUILD_SRC_RPM_OPTIONS')

if os.environ.get("EXTRA_BUILD_RPM_OPTIONS") is None:
    extra_build_rpm_options = ''
else:
    extra_build_rpm_options = os.environ.get('EXTRA_BUILD_RPM_OPTIONS')


platform_arch = os.getenv('PLATFORM_ARCH')
platform_name = os.getenv('PLATFORM_NAME')
rerun_tests = os.environ.get('RERUN_TESTS')
save_buildroot = os.environ.get('SAVE_BUILDROOT')
print('rerun tests is %s' % rerun_tests)
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


def print_log(message):
    try:
        logger = open(logfile, 'a')
        logger.write(message + '\n')
        logger.close()
    except IOError:
        print("Can't write to log file: " + logfile)
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
        print('requested package [{}] not found'.format(
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


def validate_spec(path):
    spec = [f for f in os.listdir(path) if f.endswith('.spec')]
    if len(spec) > 1:
        print('more than 1 specfile in %s' % path)
        sys.exit(1)
    else:
        print('spec_name is %s' % spec[0])
        spec_name.append(spec[0])
        print('single spec in repo, check passed')


def download_yml(yaml_file):
    if os.path.exists(yaml_file) and os.path.isfile(yaml_file):
        try:
            data = yaml.safe_load(open(yaml_file))
            for key, value in data['sources'].items():
                print('downloading %s' % key)
                download_hash(value, key)
        except yaml.YAMLError as exc:
            print('.abf.yml probably damaged')
            print(exc)
    else:
        print('abf.yml not found')

# func to remove leftovers
# from prev. build


def remove_if_exist(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            try:
                subprocess.check_output(
                    ['/usr/bin/sudo', '-E', 'rm', '-rf', path])
            except subprocess.CalledProcessError as e:
                print(e.output)
                return
        if os.path.isfile(path):
            try:
                subprocess.check_output(
                    ['/usr/bin/sudo', '-E', 'rm', '-f', path])
            except subprocess.CalledProcessError as e:
                print(e.output)
                return


def clone_repo(git_repo, project_version):
    remove_if_exist(build_package)
    tries = 5
    for i in range(tries):
        try:
            print('cloning [{}], branch: [{}] to [{}]'.format(git_repo, project_version, build_package))
            subprocess.check_output(['/usr/bin/git', 'clone', git_repo, build_package])
            subprocess.check_output(['git', 'checkout', project_version], cwd=build_package)
        except subprocess.CalledProcessError:
            if i < tries - 1:
                time.sleep(5)
                continue
            else:
                print('some issues with cloning repo %s' % git_repo)
                sys.exit(1)
        break
    # generate commit_id
    git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=build_package)
    print(git_commit.decode('utf-8'), file=open(get_home + '/commit_hash', "a"))


def hash_file(rpm):
    """"This function returns the SHA-1 hash
    of the file passed into it"""
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


def validate_exclusive(srpm):
    ts = rpm.TransactionSet()
    ts.setVSFlags(~(rpm.RPMVSF_NEEDPAYLOAD))
    fdno = os.open(srpm, os.O_RDONLY)
    hdr = ts.hdrFromFdno(fdno)
    if hdr['excludearch']:
        for a in hdr['excludearch']:
            if a == platform_arch:
                print("Architecture is excluded per package spec file (ExcludeArch tag)")
                sys.exit(6)
    if hdr['exclusivearch']:
        linted_arch = []
        for excl_arch in hdr['exclusivearch']:
            linted_arch.append(excl_arch)
        if platform_arch in linted_arch:
            print('exclusivearch header passed for %s' % platform_arch)
        else:
            print('exclusive arch test failed')
            print('Check spec for ExclusiveArch tag')
            sys.exit(6)


def container_data():
    ts = rpm.ts()
    multikeys = []
#    rpm_packages = ['/home/fdrt/output/libinput10-1.13.2-1-omv4000.i686.rpm']
    for pkg in rpm_packages:
        # Do not check src.srm
        fdno = os.open(pkg, os.O_RDONLY)
        hdr = ts.hdrFromFdno(fdno)
        name = hdr['name']
        version = hdr['version']
        release = hdr['release']
        if hdr['epoch']:
            epoch = hdr['epoch']
        else:
            epoch = 0
        shasum = hash_file(pkg)
        # init empty list
        full_list = []
        if not os.path.basename(pkg).endswith("src.rpm"):
            try:
                dependencies = subprocess.check_output(
                    ['dnf', 'repoquery', '-q', '--latest-limit=1', '--qf', '%{NAME}', '--whatrequires', name])
                # just a list of deps
                full_list = dependencies.decode().split('\n')
            except subprocess.CalledProcessError:
                print('some problem with dnf repoquery for %s' % name)
        package_info = dict([('name', name), ('version', version), ('release', release), ('size', get_size(pkg)), ('epoch', epoch), ('fullname', pkg.split('/')[-1]), ('sha1', shasum), ('dependent_packages', ' '.join(full_list))])

#        print(package_info)
        app_json = json.dumps(package_info, sort_keys=True, indent=4)
        multikeys.append(package_info)
#    print(multikeys)
    with open(c_data, 'w') as out_json:
        json.dump(multikeys, out_json, sort_keys=True, indent=4)


def extra_tests():
    only_rpms = set(rpm_packages) - set(src_rpm)
    # check_package
    try:
        print('installing %s' % list(only_rpms))
        subprocess.check_call(
            [mock_binary, '--init', '--configdir', mock_config, '--install'] + list(only_rpms))
        shutil.copy('/var/lib/mock/{}-{}/result/root.log'.format(platform_name, platform_arch), logfile)
        print('all packages successfully installed')
    except subprocess.CalledProcessError:
        shutil.copy('/var/lib/mock/{}-{}/result/root.log'.format(platform_name, platform_arch), logfile)
        # tests failed
        sys.exit(5)
    # stage2
    # check versions
    # here only rpm packages, not debuginfo
    skip_debuginfo = [s for s in only_rpms if "debuginfo" not in s]
    ts = rpm.ts()
    try:
        for pkg in skip_debuginfo:
            fdno = os.open(pkg, os.O_RDONLY)
            hdr = ts.hdrFromFdno(fdno)
            name = hdr['name']
            version = hdr['version']
            release = hdr['release']
            if hdr['epoch']:
                epoch = hdr['epoch']
            else:
                epoch = 0
            evr = '{}:{}-{}'.format(epoch, version, release)
            check_string = 'LC_ALL=C dnf repoquery -q --qf %{{EPOCH}}:%{{VERSION}}-%{{RELEASE}} --latest-limit=1 {}'.format(name)
            try:
                inrepo_version = subprocess.check_output([mock_binary, '--quiet', '--shell', '-v', check_string]).decode('utf-8')
                print_log('repo version is : {}'.format(inrepo_version))
            except subprocess.CalledProcessError as e:
                print(e)
                sys.exit(5)
            # rpmdev-vercmp 0:7.4.0-1 0:7.4.0-1
            if inrepo_version:
                print_log('repo version is: %s' % inrepo_version)
            else:
                inrepo_version = 0
            try:
                print_log('run rpmdev-vercmp %s %s' %
                          (evr, str(inrepo_version)))
                a = subprocess.check_call(
                    ['rpmdev-vercmp', evr, str(inrepo_version)])
                if a == 0:
                    print_log(
                        'Package {} is either the same, older, or another problem. Extra tests failed'.format(name))
                    sys.exit(5)
            except subprocess.CalledProcessError as e:
                exit_code = e.returncode
                if exit_code == 11:
                    print_log('package newer than in repo')
                    sys.exit(0)
                print_log('package older, same or other issue')
                sys.exit(5)
    except subprocess.CalledProcessError as e:
        print_log(e)
        print_log('failed to check packages')
        sys.exit(5)


def save_build_root():
    if save_buildroot == 'true':
        saveroot = '/var/lib/mock/{}-{}/root/'.format(platform_name, platform_arch)
        try:
            subprocess.check_output(['sudo', 'tar', '-czf', output_dir + '/buildroot.tar.gz', saveroot])
        except subprocess.CalledProcessError as e:
            print_log(e)
            print_log('failed to make buildroot.tar.gz')


def relaunch_tests():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    config_generator.generate_config()
    # clone repo and generate config
    clone_repo(git_repo, project_version)
    packages = os.getenv('PACKAGES')
    for package in packages.split():
        print('downloading {}'.format(package))
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
    try:
        print('\n'.join(rpm_packages))
        subprocess.check_call([mock_binary, '--init', '--configdir', mock_config, '--install'] + list(only_rpms))
        print('packages %s installed successfully' % list(only_rpms))
        shutil.copy('/var/lib/mock/{}-{}/result/root.log'.format(platform_name, platform_arch), logfile)
    except subprocess.CalledProcessError as e:
        shutil.copy('/var/lib/mock/{}-{}/result/root.log'.format(platform_name, platform_arch), logfile)
        sys.exit(5)


def build_rpm():
    config_generator.generate_config()
    tries = 5
    # pattern for retry
    pattern_for_retry = '(.*)Failed to download(.*)'
    if not os.environ.get('MOCK_CACHE'):
        # /var/cache/mock/cooker-x86_64/root_cache/
        print("MOCK_CACHE is none, than need to clear platform cache")
        remove_if_exist('/var/cache/mock/{}-{}/root_cache/'.format(platform_name, platform_arch))
    for i in range(tries):
        try:
            if os.environ.get("EXTRA_BUILD_SRC_RPM_OPTIONS") == '':
                subprocess.check_output([mock_binary, '--update', '--configdir', mock_config, '--buildsrpm', '--spec=' + build_package + '/' + spec_name[0], '--source=' + build_package, '--no-cleanup-after',
                                         '--resultdir=' + output_dir])
            else:
                subprocess.check_output([mock_binary, '--update', '--configdir', mock_config, '--buildsrpm', '--spec=' + build_package + '/' + spec_name[0], '--source=' + build_package, '--no-cleanup-after', extra_build_src_rpm_options,
                                         '--resultdir=' + output_dir])
        except subprocess.CalledProcessError as e:
            if i < tries - 1:
                print('something went wrong with SRPM creation')
                print('usually it is bad metadata or missed sources in .abf.yml')
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
    print('srpm is %s' % src_rpm[0])
    # validate src.rpm here
    validate_exclusive(src_rpm[0])
    # for exclusive_arches
    for i in range(tries):
        try:
            if os.environ.get("EXTRA_BUILD_RPM_OPTIONS") == '':
                subprocess.check_call([mock_binary, '-v', '--update', '--configdir', mock_config, '--rebuild',
                                       src_rpm[0], '--no-cleanup-after', '--no-clean', '--resultdir=' + output_dir])
            else:
                subprocess.check_output([mock_binary, '-v', '--update', '--configdir', mock_config, '--rebuild', src_rpm[0],
                                         '--no-cleanup-after', '--no-clean', extra_build_rpm_options, '--resultdir=' + output_dir])
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
                        print('problems with metadata in repo, restarting build in 60 seconds')
                        # remove cache dir
                        remove_if_exist('/var/cache/mock/{}-{}/dnf_cache/'.format(platform_name, platform_arch))
                        time.sleep(60)
                        continue
                    if i == tries - 1:
                        raise
                else:
                    print('build failed')
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
    if os.environ.get("USE_EXTRA_TESTS") == 'true':
        extra_tests()


def cleanup_all():
    print('Cleaning up...')
    # wipe letfovers
    # MASK me if you run the script under your user
    # it will wipe whole your /home/user dir
    for dirpath, dirnames, filenames in os.walk(get_home):
        for name in dirnames:
            shutil.rmtree(os.path.join(dirpath, name))
    # files
    remove_if_exist('/etc/rpm/platform')
#    remove_if_exist('/etc/mock/default.cfg')
    # dirs
    remove_if_exist('/var/lib/mock/')
    # probably need to drop it and point in mock
#    remove_if_exist('/var/cache/mock/')
#    remove_if_exist('/var/cache/dnf/')
    # /home/omv/package_name
    remove_if_exist(build_package)
    remove_if_exist(get_home + '/build_fail_reason.log')
    remove_if_exist(get_home + '/commit_hash')
    remove_if_exist(output_dir)
    print('run dnf clean metadata')
    try:
        subprocess.check_output(['/usr/bin/sudo', 'dnf', 'clean', 'all'])
    except subprocess.CalledProcessError as e:
        print(e.output)
        pass


if __name__ == '__main__':
    cleanup_all()
    if rerun_tests == 'true':
        relaunch_tests()
    else:
        clone_repo(git_repo, project_version)
        validate_spec(build_package)
        download_yml(build_package + '/' + '.abf.yml')
        build_rpm()
