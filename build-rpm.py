#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import yaml
import requests
import json
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
try:
  import libdnf5
except ImportError:
  print("Could not import the libdnf5 python module\nMake sure dnf5 python bindings are installed.")
  raise SystemExit

MANDATORY_ENV_VARS = ['HOME', 'PACKAGE', 'GIT_REPO', 'FILE_STORE_ADDR', 'PLATFORM_ARCH', 'PLATFORM_NAME', 'PROJECT_VERSION']

for var in MANDATORY_ENV_VARS:
    if var not in os.environ:
        raise EnvironmentError("Failed because '{}' is not set in environment.".format(var))

GET_HOME = os.environ.get('HOME')
PACKAGE = os.environ.get('PACKAGE')
GIT_REPO = os.environ.get('GIT_REPO')
# FIXME workaround for https://github.com/OpenMandrivaSoftware/rosa-build/issues/161
if GIT_REPO[0:17] == 'git://github.com/':
    GIT_REPO='https://github.com/' + GIT_REPO[17:]

FILE_STORE_BASE = os.environ.get('FILE_STORE_ADDR')
BUILD_PACKAGE = GET_HOME + '/' + PACKAGE

if os.environ.get('COMMIT_HASH') is None:
    PROJECT_VERSION = os.environ.get('PROJECT_VERSION')
else:
    PROJECT_VERSION = os.environ.get('COMMIT_HASH')

EXTRA_BUILD_SRC_RPM_OPTIONS = list(filter(None, [x for x in os.environ.get('EXTRA_BUILD_SRC_RPM_OPTIONS', '').split(' ') if x]))
EXTRA_BUILD_RPM_OPTIONS = list(filter(None, [x for x in os.environ.get('EXTRA_BUILD_RPM_OPTIONS', '').split(' ') if x]))
PLATFORM_ARCH = os.environ.get('PLATFORM_ARCH')
PLATFORM_NAME = os.environ.get('PLATFORM_NAME')
RERUN_TESTS = os.environ.get('RERUN_TESTS')
USE_EXTRA_TESTS = os.environ.get("USE_EXTRA_TESTS")
SAVE_BUILDROOT = os.environ.get('SAVE_BUILDROOT')

# Some static definitions
# /home/omv/output
MOCK_BINARY = '/usr/bin/mock'
MOCK_CONFIG = '/etc/mock/'
OUTPUT_DIR = GET_HOME + '/output'
ABF_DATA = OUTPUT_DIR + '/container_data.json'
ROOT_LOG = OUTPUT_DIR + '/root.log.gz'
LOGFILE = OUTPUT_DIR + '/' + 'extra_tests.' + time.strftime("%m-%d-%Y-%H-%M-%S") + '.log'
SPEC_NAME = []
RPM_PACKAGES = []
SRC_RPM = []

def is_valid_hostname(hostname):
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    if len(hostname) > 255:
        return False
    if re.match(r"[a-f0-9]{12}", hostname.split(".")[0]):
        print(f"BUILDER: Container hostname does not pass naming policy {hostname} .")
        return False
    else:
        print(f"BUILDER: Hostname: {hostname} linting passed.")
        return True


def print_log(message):
    try:
        logger = open(LOGFILE, 'a')
        logger.write(message + '\n')
        logger.close()
    except IOError:
        print(f"BUILDER: Can't write to log file: {LOGFILE}")
    print(message)


def download_from_fstore(file_hash, file_name=None):
    fstore_json_url = '{}/api/v1/file_stores.json?hash={}'.format(FILE_STORE_BASE, file_hash)
    fstore_file_url = '{}/api/v1/file_stores/{}'.format(FILE_STORE_BASE, file_hash)

    # Stream the file download in chunks
    with requests.get(fstore_file_url, stream=True) as response:
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # this code responsible for fetching names from abf
            # we not using it because of in names with +, + replaces with _
            # e.g gtk-_3.0
            if not file_name:
               page = response.content.decode('utf-8')
               page2 = json.loads(page)
               file_name = page2[0]['file_name']

            destination_file = BUILD_PACKAGE + '/' + file_name
            with open(destination_file, 'wb') as file:
                # Iterate over the content in chunks and write to the file
                for chunk in response.iter_content(chunk_size=1048576):
                    if chunk:
                        file.write(chunk)
            print(f"BUILDER: Download successful. File saved at {destination_file}")
        else:
            print(f"BUILDER: Error: Unable to download file {fstore_json_url}. Status code: {response.status_code}")


def remove_changelog(spec):
    if os.path.isfile(spec):
        try:
            with open(spec, 'r+') as f:
                content = f.read()
                f.seek(0)
                f.truncate()
                f.write(content.split('%changelog')[0])
        except Exception as e:
            print(f"Error deleting changelog: {e}")
            pass

def validate_spec(path):
    spec_fn = [f for f in os.listdir(path) if f.endswith('.spec')]
    print(f"BUILDER: Validating RPM spec files found in {path}")

    if len(spec_fn) > 1:
        print(f"BUILDER: Found more than 1 RPM spec file in {path}")
        raise SystemExit(1)
    elif len(spec_fn) == 0:
        print(f"BUILDER: No RPM spec file found in {path}")
        raise SystemExit(1)
    else:
        print(f"BUILDER: RPM spec file name is {spec_fn[0]}")
        try:
            build_spec = rpm.spec(path + '/' + spec_fn[0])
            rpm.reloadConfig()
        except ValueError:
            print(f"BUILDER: Failed to open: {spec_fn[0]}, not a valid spec file.")
            raise SystemExit(1)

    if (PLATFORM_ARCH in set(build_spec.sourceHeader[rpm.RPMTAG_EXCLUDEARCH]) and (len(set(build_spec.sourceHeader[rpm.RPMTAG_EXCLUDEARCH])) > 0)):
       print(f"BUILDER: Architecture {PLATFORM_ARCH} is excluded in RPM spec file (ExcludeArch tag). Exiting build.")
       raise SystemExit(6)

    if (PLATFORM_ARCH not in set(build_spec.sourceHeader[rpm.RPMTAG_EXCLUSIVEARCH]) and (len(set(build_spec.sourceHeader[rpm.RPMTAG_EXCLUSIVEARCH])) > 0)):
       print(f"BUILDER: Architecture {PLATFORMARCH} is not included in RPM spec file (ExclusiveArch tag). Exiting build.")
       raise SystemExit(6)

    SPEC_NAME.append(spec_fn[0])
    print("BUILDER: Single RPM spec file in build directory, checks passed.")

# Use regular expression to match the %changelog section
#    changelog_pattern = re.compile(r'%changelog.*?(\n\n|$)', re.DOTALL)
    changelog_pattern = re.compile(r'%changelog.*', re.DOTALL)
    try:
       with open(path + '/' + spec_fn[0], 'r') as spec_file:
            spec_content = spec_file.read()
            modified_spec_content = changelog_pattern.sub('', spec_content)

       with open(path + '/' + spec_fn[0], 'w') as spec_file:
            spec_file.write(modified_spec_content)

       print(f"BUILDER: %changelog section and its entries removed from {spec_fn[0]}")
    except Exception as e:
       print(f"BUILDER: Error: {e}")

def download_yml(yaml_file):
    if os.path.exists(yaml_file) and os.path.isfile(yaml_file):
        try:
            data = yaml.safe_load(open(yaml_file))
        except yaml.YAMLError as e:
            print(f"BUILDER: Error parsing .abf.yml: {e}")
            raise SystemExit(1)
        if ('sources' not in data) or len(data['sources']) == 0:
            print("BUILDER: WARNING: .abf.yml contains no or empty sources section")
        else:
            for key, value in data['sources'].items():
                print(f"BUILDER: Downloading source {key}")
                download_from_fstore(value, key)
    else:
        print("BUILDER: .abf.yml not found")

# func to remove leftovers
# from prev. build


def remove_if_exist(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            try:
                subprocess.run(['/usr/bin/sudo', '-E', 'rm', '-rf', path], check=True)
                print(f"BUILDER: Removed {path}")
            except subprocess.CalledProcessError as e:
                print(f"BUILDER: Error: {e}")
                return
        if os.path.isfile(path):
            try:
                subprocess.run(['/usr/bin/sudo', '-E', 'rm', '-f', path], check=True)
                print(f"BUILDER: Removed {path}")
            except subprocess.CalledProcessError as e:
                print(f"BUILDER: Error: {e}")
                return


def clone_repo(git_repo, project_version, max_retries=5, retry_delay=5):
    remove_if_exist(BUILD_PACKAGE)
    for attempt in range(1, max_retries + 1):
        try:
           print(f"BUILDER: Git repository cloning [{git_repo}], branch: [{project_version}] to [{BUILD_PACKAGE}]")
           # Please do not change this string ROSA really use checkout to build specific commits
           subprocess.run(['git', 'clone', git_repo, BUILD_PACKAGE], timeout=3600, env={'LC_ALL': 'C.UTF-8'}, check=True)
           subprocess.run(['git', 'checkout', project_version], cwd=BUILD_PACKAGE, env={'LC_ALL': 'C.UTF-8'}, check=True)
           print(f"BUILDER: Repository cloned successfully to {BUILD_PACKAGE}")
           break  # Break out of the loop if the clone was successful
        except subprocess.CalledProcessError as e:
           print(f"BUILDER: Error during clone attempt {attempt}: {e}")
           if attempt < max_retries:
              print(f"BUILDER: Retrying git clone in {retry_delay} seconds...")
              time.sleep(retry_delay)
           else:
              print(f"BUILDER: Max retries reached. Unable to git clone repository.")
              raise SystemExit(1)

# Generate commit_id file
    f = open(GET_HOME + '/commit_hash', "a")
    git_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=BUILD_PACKAGE, timeout=3600, env={'LC_ALL': 'C.UTF-8'}, stdout=f)

def calculate_sha1(file_path):
# This function returns the SHA-1 hash of a file
# ABF expects hashes for file to be unique
    sha1_hash = hashlib.sha1()
    with open(file_path, 'rb') as file:
        # Read the file in chunks to avoid loading the entire file into memory
        # 2^20 = 1048576 = 1Mbyte
        for chunk in iter(lambda: file.read(1048576), b''):
            sha1_hash.update(chunk)
    return sha1_hash.hexdigest()

def abf_container(max_retries=5, retry_delay=30):
# Create container data for ABF, based on on RPM files.
    multikeys = []
# Start to read build rpm files
    rpm_ts = rpm.TransactionSet()
# Initialise dnf5 setup
    dnf5_base = libdnf5.base.Base()
    try:
        dnf5_base.load_config()
    except RuntimeError as e:
      print(f"BUILDER: something went wrong with initializing dnf5 environment. {e}")
      raise SystemExit
    dnf5_base.setup()
    repo_sack = dnf5_base.get_repo_sack()
# Create repositories from system configuration files.
    repo_sack.create_repos_from_system_configuration()
    repo_sack.update_and_load_enabled_repos(False)

# Do not check src.srm
#    RPM_PACKAGES = ['/home/tpg/OpenMandriva/docker-builder-dnf5/okteta-0.26.14-1-omv2390.aarch64.rpm']
    for pkg in RPM_PACKAGES:
        whatrequires = []
        try:
           fd = os.open(pkg, os.O_RDONLY)
        except IOError:
           print(f"BUILDER: Can not open file {pkg}")
        rpm_hdr = rpm_ts.hdrFromFdno(fd)
        os.close(fd)

# Calculate sha1 of a RPM file based on its real size
        shasum = calculate_sha1(pkg)
# Get the real file size
        try:
           pkg_size = os.path.getsize(pkg)
        except FileNotFoundError:
            print(f"Error: File not found - {pkg}")
        except Exception as e:
            print(f"Error: {e}")

        for attempt in range(1, max_retries + 1):
            try:
# Intialise remote repository query
                query = libdnf5.rpm.PackageQuery(dnf5_base)
                query.filter_latest_evr(limit=1)
                query.filter_requires([rpm_hdr[rpm.RPMTAG_NAME]])
                if query:
                    print(f"Found packages requiring {pkg}:")
                    for i in query:
                        whatrequires.append(i.get_name())
                    break
                else:
                    print(f"No packages found requiring {pkg} in the repository.")
                    break  # If no packages are found, no need to retry
            except RuntimeError as e:
                print(f"Error during query attempt {attempt}: {e}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    repo_query = libdnf5.repo.RepoQuery(dnf5_base)
                    repo_query.filter_type(libdnf5.repo.Repo.Type_AVAILABLE)
                    for repo in repo_query:
                        repo_dir = repo.get_cachedir()
                        if os.path.exists(repo_dir):
                            repo_cache = libdnf5.repo.RepoCache(dnf5_base, repo_dir)
                            repo_cache.write_attribute(libdnf5.repo.RepoCache.ATTRIBUTE_EXPIRED)
                            repo.download_metadata(repo_dir)
                            repo_cache.remove_attribute(libdnf5.repo.RepoCache.ATTRIBUTE_EXPIRED)
                            repo.read_metadata_cache()
                            repo.load()

                time.sleep(retry_delay)
            else:
                print(f"Max retries reached. Unable to query the repository.")
                break
# Generate the data based on RPM headers and others
        package_info = dict([('name', rpm_hdr[rpm.RPMTAG_NAME]), ('version', rpm_hdr[rpm.RPMTAG_VERSION]), ('release', rpm_hdr[rpm.RPMTAG_RELEASE]), ('size', pkg_size), ('epoch', rpm_hdr[rpm.RPMTAG_EPOCH] or 0), ('fullname', pkg.split('/')[-1]), ('sha1', shasum), ('dependent_packages', ' '.join(whatrequires))])
        multikeys.append(package_info)
    with open(ABF_DATA, 'w') as out_json:
        json.dump(multikeys, out_json, sort_keys=True, separators=(',', ':'))
    print("BUILDER: Creating ABF continer data has finished.")


def extra_tests():
# Amout of rpm test failures should be 0
    test_failures = 0
    test_rpms = [s for s in RPM_PACKAGES if "debuginfo" not in s and "debugsource" not in s and "src.rpm" not in s]
# Initialise dnf5 setup
    dnf5_base = libdnf5.base.Base()
# Only alow rpm packages. Filter out debuginfo, debugsource and src.rpm
    print_log(f"BUILDER: Test installing {list(test_rpms)}")

    try:
      dnf5_base.load_config()
    except RuntimeError as e:
      print_log(f"BUILDER: something went wrong with initializing dnf5 environment. {e}")
      raise SystemExit

    dnf5_base.setup()
    repo_sack = dnf5_base.get_repo_sack()
# Create repositories from system configuration files.
    repo_sack.create_repos_from_system_configuration()
    repo_sack.update_and_load_enabled_repos(False)

    for pkg in test_rpms:
      try:
        fd = os.open(pkg, os.O_RDONLY)
      except IOError:
        print_log(f"BUILDER: Can not open file {pkg}")

      rpm_ts = rpm.TransactionSet()
      rpm_hdr = rpm_ts.hdrFromFdno(fd)
      os.close(fd)
      spec_evr = '{}:{}-{}'.format(rpm_hdr[rpm.RPMTAG_EPOCH] or 0, rpm_hdr[rpm.RPMTAG_VERSION], rpm_hdr[rpm.RPMTAG_RELEASE])
      print_log(f"BUILDER: Checking package {rpm_hdr[rpm.RPMTAG_NAME]} against remote repository.")
# Intialise remote repository query
      query = libdnf5.rpm.PackageQuery(dnf5_base)
      query.filter_name([rpm_hdr[rpm.RPMTAG_NAME]])
      query.filter_latest_evr(limit=1)
# Package name does not exist in remote repository
      if query.size() == 0:
        print_log(f"BUILDER: Looks like package is new as it does not exist in remote repository.")
      else:
        query.filter_evr([spec_evr], libdnf5.common.QueryCmp_LT)
        if query.size():
          print_log("BUILDER: Package is newer than in repository.")
        else:
# Error occured, register it
          print_log(f"BUILDER: Package {pkg} is either the same, older or another problem. Extra tests failed.")
          test_failures += 1

# Defne goal for rpm testing
# Somehow i do not know how to remove packages from Goal
# before running query, so lets run this here to not poduce
# fake information that package is in repository
    goal = libdnf5.base.Goal(dnf5_base)
    goal.add_rpm_distro_sync()

    for pkg in test_rpms:
      goal.add_install(pkg)

    try:
      goal.add_rpm_distro_sync()
# Resolving transaction i.e looking for missing Requires etc
      transaction = goal.resolve()
# Simulating rpm -i --test
      install_test = transaction.test()
    except RuntimeError as e:
      print_log(f"BUILDER: Can't resolve the dnf5 installation. {e}")

    if (transaction.get_problems() != libdnf5.base.GoalProblem_NO_PROBLEM) and (install_test.get_problems() != libdnf5.base.GoalProblem_NO_PROBLEM):
      print_log("BUILDER: Testing found PROBLEM:")
      print_log("\n".join(transaction.get_resolve_logs_as_strings()))
      goal.reset()
# Error occured, register it
      test_failures += 1
      raise SystemExit(5)
    else:
      print_log("BUILDER: Test resolved transaction, packages to be installed:")
      for tspkg in transaction.get_transaction_packages():
        print(tspkg.get_package().get_nevra() + ': ' + libdnf5.base.transaction.transaction_item_action_to_string(tspkg.get_action()))

    goal.reset()
    if test_failures > 0:
     print_log(f"BUILDER: Too much errors: {test_failures}, while testing packages.")
     raise SystemExit(5)

    print_log("BUILDER: Testing rpms has finished.")

def save_build_root():
    if SAVE_BUILDROOT == 'true':
        saveroot = '/var/lib/mock/{}-{}/root/'.format(PLATFORM_NAME, PLATFORM_ARCH)
        try:
            subprocess.run(['sudo', 'tar', '-czf', OUTPUT_DIR + '/buildroot.tar.gz', saveroot], check=True)
            print_log("BUILDER: Build root contents was saved to buildroot.tar.gz")
        except subprocess.CalledProcessError as e:
            print_log(f"BUILDER: Error: {e}")
            print_log("BUILDER: Failed to create buildroot.tar.gz")


def relaunch_tests():
    print("BUILDER: Re-running tests.")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    config_generator.generate_config()
    # clone repo and generate config
    clone_repo(GIT_REPO, PROJECT_VERSION)
    packages = os.getenv('PACKAGES')
    for package in packages.split():
        print(f"BUILDER: Downloading package {package} for testing")
        # download packages to /home/omv/pkg_name/
        download_from_fstore(package)
        # build package is /home/omv/pkg_name
    for r, d, f in os.walk(BUILD_PACKAGE):
        for file_name in f:
            if '.src.rpm' in file_name:
                SRC_RPM.append(BUILD_PACKAGE + '/' + file_name)
            if file_name.endswith('.rpm') and '.src.rpm' not in file_name:
                RPM_PACKAGES.append(BUILD_PACKAGE + '/' + file_name)
# Execute extra tests for rpm files
    extra_tests()


def build_rpm(max_retries=5, retry_delay=60):
# Generate cofiguration for mock
    config_generator.generate_config()

# Pattern for retry mock execution
    pattern_for_retry = '(.*)(Failed to download|Error downloading)(.*)'

    if not os.environ.get('MOCK_CACHE'):
        # /var/cache/mock/cooker-x86_64/root_cache/
        print("BUILDER: MOCK_CACHE is none, than need to clear platform cache.")
        remove_if_exist('/var/cache/mock/{}-{}/root_cache/'.format(PLATFORM_NAME, PLATFORM_ARCH))

    for attempt in range(1, max_retries + 1):
        try:
            print("BUILDER: Starting to build SRPM and RPMs.")
            subprocess.run([MOCK_BINARY, '-v', '--no-cleanup-after', '--no-clean', '--configdir', MOCK_CONFIG, '--spec=' + BUILD_PACKAGE + '/' + SPEC_NAME[0], '--sources=' + BUILD_PACKAGE] + EXTRA_BUILD_SRC_RPM_OPTIONS + EXTRA_BUILD_RPM_OPTIONS + ['--resultdir=' + OUTPUT_DIR], check=True)
        except subprocess.CalledProcessError as e:
            print(f"BUILDER: Error while running mock: {e}")
            if os.path.exists(ROOT_LOG) and os.path.getsize(ROOT_LOG) > 0:
                sz = os.path.getsize(ROOT_LOG)
                if magic.detect_from_filename(ROOT_LOG).mime_type == 'application/gzip':
                    handle = open(ROOT_LOG, "r")
                    # let's mmap piece of memory as we unpacked gzip
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
                    msgf = io.open(ROOT_LOG, "r", encoding="utf-8")
                    mm = mmap.mmap(msgf.fileno(), sz, access=mmap.ACCESS_READ)
                    error = re.search(pattern_for_retry.encode(), mm)
                    msgf.close()
                    mm.close()

                # probably metadata not ready
                if error:
                    # print(error.group().decode())
                    if attempt < max_retries -1:
                        print("BUILDER: Something went wrong with SRPM and RPMs creation, usually it is bad metadata or missed sources in .abf.yml")
                        # remove cache dir
                        remove_if_exist('/var/cache/mock/{}-{}/dnf_cache/'.format(PLATFORM_NAME, PLATFORM_ARCH))
                        time.sleep(retry_delay)
                        continue
                    if i == attemp - 1:
                        raise
                else:
                    print("BUILDER: Building SRPM and RPM failed.")
                    # /usr/bin/python /mdv/check_error.py --file "${OUTPUT_FOLDER}"/root.log >> ~/build_fail_reason.log
                    # add here check_error.py
                    check_error.known_errors(ROOT_LOG, GET_HOME + '/build_fail_reason.log')
                    # function to make tar.xz of target platform
                    save_build_root()
                    remove_if_exist(BUILD_PACKAGE)
                    raise SystemExit(1)
            else:
                raise SystemExit(1)
        break

    for r, d, f in os.walk(OUTPUT_DIR):
        for file_name in f:
            if '.src.rpm' in file_name:
                SRC_RPM.append(OUTPUT_DIR + '/' + file_name)
            if file_name.endswith('.rpm') and '.src.rpm' not in file_name:
                RPM_PACKAGES.append(OUTPUT_DIR + '/' + file_name)

# List rpm packages
    print(f"BUILDER: List of build packages:? {RPM_PACKAGES}")
    abf_container()
    save_build_root()
    if USE_EXTRA_TESTS == 'true':
        extra_tests()

def cleanup_all():
    print("BUILDER: Cleaning up the environment")
    # wipe letfovers
    # MASK me if you run the script under your user
    # it will wipe whole your /home/user dir
    for dirpath, dirnames, filenames in os.walk(GET_HOME):
        for name in dirnames:
            shutil.rmtree(os.path.join(dirpath, name))
    # files
    # clean not umounted dirs by mock
    umount_dirs = ["/root/var/cache/dnf", "/root/var/cache/yum", "/root/proc", "/root/sys", "/root/dev/pts", "/root/dev/shm"]
    for dirs in ["/var/lib/mock/{}-{}".format(PLATFORM_NAME, PLATFORM_ARCH) + s for s in umount_dirs]:
      if os.path.exists(dirs):
        try:
          subprocess.run(['sudo', 'umount', '-ql', dirs], text=True, check=True)
        except subprocess.CalledProcessError as e:
          print(f"BUILDER: Error: {e}")
          continue

    remove_if_exist('/etc/rpm/platform')
    remove_if_exist('/var/lib/mock/{}-{}/result/'.format(PLATFORM_NAME, PLATFORM_ARCH))
    remove_if_exist('/var/lib/mock/{}-{}/root/builddir/'.format(PLATFORM_NAME, PLATFORM_ARCH))
    # /home/omv/package_name
    remove_if_exist(BUILD_PACKAGE)
    remove_if_exist(GET_HOME + '/build_fail_reason.log')
    remove_if_exist(GET_HOME + '/commit_hash')
    remove_if_exist(OUTPUT_DIR)


if __name__ == '__main__':
    print("BUILDER: Starting script: build-rpm.py")
    cleanup_all()
    if is_valid_hostname(socket.gethostname()) is False:
        raise SystemExit(1)
    if RERUN_TESTS is not None:
        relaunch_tests()
    else:
        clone_repo(GIT_REPO, PROJECT_VERSION)
        validate_spec(BUILD_PACKAGE)
        download_yml(BUILD_PACKAGE + '/' + '.abf.yml')
        build_rpm()
