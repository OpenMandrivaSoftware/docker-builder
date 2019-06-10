#!/usr/bin/env python
import os
import subprocess
import yaml
import requests
import json
import sys
import time
import rpm
import hashlib


get_home = os.environ.get('HOME')
package = os.environ.get('PACKAGE')
git_repo = os.environ.get('GIT_REPO')
build_package = get_home + '/' + package
project_version = os.environ.get('PROJECT_VERSION')
extra_build_src_rpm_options = os.environ.get('EXTRA_BUILD_SRC_RPM_OPTIONS')
extra_build_rpm_options = os.environ.get('EXTRA_BUILD_RPM_OPTIONS')
# e.g. /home/omv/htop
# print(build_package)

platform_arch = os.getenv('PLATFORM_ARCH')
platform_name = os.getenv('PLATFORM_NAME')

# static
# /home/omv/output
mock_binary = '/usr/bin/mock'
mock_config = '/etc/mock/'
file_store_base = 'http://file-store.openmandriva.org'
output_dir = get_home + '/output'
c_data = output_dir + '/container_data.json'

spec_name = []
rpm_packages = []
src_rpm = []

def download_hash(hashsum):
    fstore_json_url = '{}/api/v1/file_stores.json?hash={}'.format(
        file_store_base, hashsum)
    fstore_file_url = '{}/api/v1/file_stores/{}'.format(
        file_store_base, hashsum)
    resp = requests.get(fstore_json_url)
    if resp.status_code == 404:
        print('requested package [{}] not found'.format(
            fstore_json_url))
    if resp.status_code == 200:
        page = resp.content.decode('utf-8')
        page2 = json.loads(page)
        name = page2[0]['file_name']
        download_file = requests.get(fstore_file_url)
        source_tarball = build_package + '/' + name
        with open(source_tarball, 'wb') as f:
            f.write(download_file.content)


def validate_spec(path):
    spec_counter = len([f for f in os.listdir(path) if f.endswith('.spec')])
    if spec_counter > 1:
        print('more than 1 specfile in %s' % path)
        sys.exit(1)
    else:
        for r, d, f in os.walk(path):
            for spec in f:
                if '.spec' in spec:
                    print('spec_name is %s' % spec)
                    spec_name.append(spec)

        print('single spec in repo, check passed')


def download_yml(yaml_file):
    if os.path.exists(yaml_file) and os.path.isfile(yaml_file):
        try:
            data = yaml.safe_load(open(yaml_file))
            for key, value in data['sources'].items():
                print('downloading %s' % key)
                download_hash(value)
        except yaml.YAMLError as exc:
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
            subprocess.check_output(['/usr/bin/git', 'clone', '-b', project_version, '--depth', '100', git_repo, build_package])
        except subprocess.CalledProcessError:
            if i < tries - 1:
                time.sleep(5)
                continue
            else:
                print('some issues with cloning repo %s' % git_repo)
                sys.exit(1)
        break


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
            # read only 1024 bytes at a time
            chunk = file.read(1024)
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
        for a in hdr['exclusivearch']:
            if a == platform_arch:
                break
            else:
                print("exclusive arch for package is %s" % (a.decode()))
                sys.exit(6)


def container_data():
    ts = rpm.ts()
    multikeys = []
#    rpm_packages = ['/home/fdrt/output/lib64png16_16-1.6.36-3-omv4000.x86_64.rpm']
    deps = ''
    for pkg in rpm_packages:
        # Do not check src.srm
        if os.path.basename(pkg).endswith("src.rpm"):
            continue
        fdno = os.open(pkg, os.O_RDONLY)
        hdr = ts.hdrFromFdno(fdno)
        name = hdr['name'].decode('utf-8')
        version = hdr['version'].decode('utf-8')
        release = hdr['release'].decode('utf-8')
        if hdr['epoch']:
            epoch = hdr['epoch'].decode('utf-8')
        else:
            epoch = 0
        shasum = hash_file(pkg)
        try:
            dependencies = subprocess.check_output(['dnf', 'repoquery', '-q', '--latest-limit=1', '--qf', '%{NAME}', '--whatrequires', name])
            # just a list of deps
            full_list = dependencies.decode().split('\n')
        except subprocess.CalledProcessError:
            print('some problem with dnf repoquery for %s' % name )
        package_info = dict([('name', name), ('version', version), ('release', release), ('epoch', epoch), ('fullname', pkg), ('sha1', shasum), ('dependent_packages', ' '.join(full_list))])
#        print(package_info)
        app_json = json.dumps(package_info, sort_keys=True, indent=4)
        multikeys.append(package_info)
#    print(multikeys)
    with open(c_data, 'w') as out_json:
        json.dump(multikeys, out_json, sort_keys=True, indent=4)


def build_rpm():
    tries = 3
    # pattern for retry
    pattern_for_retry = 'No matching package to install: (.*)'
    if os.environ.get("EXTRA_BUILD_SRC_RPM_OPTIONS") is None:
        extra_build_src_rpm_options = ''
    if os.environ.get("EXTRA_BUILD_RPM_OPTIONS") is None:
        extra_build_rpm_options = ''
    try:
        subprocess.check_output([mock_binary, '-v', '--update', '--configdir', mock_config, '--buildsrpm', '--spec=' + build_package + '/' + spec_name[0], '--source=' + build_package, '--no-cleanup-after', extra_build_src_rpm_options,
                                 '--resultdir=' + output_dir])
    except subprocess.CalledProcessError as e:
        print(e)
        sys.exit(1)
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
            if os.environ.get("EXTRA_BUILD_RPM_OPTIONS") is None:
                subprocess.check_output([mock_binary, '-v', '--update', '--configdir', mock_config, '--rebuild', src_rpm[0], '--no-cleanup-after', '--no-clean', '--resultdir=' + output_dir])
            else:
                subprocess.check_output([mock_binary, '-v', '--update', '--configdir', mock_config, '--rebuild', src_rpm[0], '--no-cleanup-after', '--no-clean', extra_build_rpm_options, '--resultdir=' + output_dir])
        except subprocess.CalledProcessError as e:
            print(e)
            if i < tries - 1:
                time.sleep(60)
                continue
            else:
                print('build failed')
                sys.exit(1)
        break
    for r, d, f in os.walk(output_dir):
        for rpm_pkg in f:
            if '.rpm' in rpm_pkg:
                rpm_packages.append(output_dir + '/' + rpm_pkg)
    container_data()



def cleanup_all():
    print('Cleaning up...')
    # files
    remove_if_exist('/etc/rpm/platform')
#    remove_if_exist('/etc/mock/default.cfg')
    # dirs
    remove_if_exist('/var/lib/mock/')
    # probably need to drop it and point in mock
#    remove_if_exist('/var/cache/mock/')
    remove_if_exist('/var/cache/dnf/')
    # /home/omv/package_name
    remove_if_exist(build_package)
    remove_if_exist('/home/omv/build_fail_reason.log')
    remove_if_exist(output_dir)


#cleanup_all()
clone_repo(git_repo, project_version)
validate_spec(build_package)
download_yml(build_package + '/' + '.abf.yml')
build_rpm()
container_data()
#validate_exclusive('get-skypeforlinux-8.44.0.40-1.src.rpm')
#validate_exclusive('/home/fdrt/output/dos2unix-7.4.0-1.src.rpm')