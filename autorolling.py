#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import redis
import requests
import shutil
import os
import subprocess

blacklist = [line.rstrip('\n') for line in open('blacklist.txt')]
print(blacklist)


def request_build_id(page):
    # print(page)
    resp = requests.get(page)
    build_page = resp.content.decode('utf-8')
    page_json = json.loads(build_page)
    package_name = page_json['build_list']['project']['name']
    package_fullname = page_json['build_list']['project']['fullname']
    package_git_url = page_json['build_list']['project']['git_url']
    package_hash = page_json['build_list']['commit_hash']
    print('package name [{}], fullname [{}], git url [{}], hash [{}]'.format(package_name, package_fullname, package_git_url, package_hash))
    return package_name, package_hash


def abf_build(package, arch):
    try:
        subprocess.check_call(['abf', 'build', '--arch', arch, '-b', 'rolling', '--testing', '--no-cached-chroot', '--auto-publish-status=testing', '--update-type', 'enhancement', '-p', 'openmandriva/%s' % package])
    except subprocess.CalledProcessError as e:
        print(e)
        return False


def git_work(pkg_name, arch, package_hash):
    git_repo = 'git@github.com:OpenMandrivaAssociation/{}.git'.format(pkg_name)
    repo_path = '/tmp/{}'.format(pkg_name)
    if os.path.exists(repo_path) and os.path.isdir(repo_path):
        shutil.rmtree(repo_path)
    # git ls-remote git://github.com/OpenMandrivaAssociation/dos2unix.git refs/heads/master
    master_hash = subprocess.check_output(['/usr/bin/git', 'ls-remote', git_repo, 'refs/heads/master']).decode().split()
    # issue here if no rolling branch no hash to return
    rolling_hash = subprocess.check_output(['/usr/bin/git', 'ls-remote', git_repo, 'refs/heads/rolling']).decode().split()
    if not rolling_hash:
        print('looks like no rolling branch in the repo')
        # git checkout to rolling with -b
        subprocess.check_output(['/usr/bin/git', 'clone', git_repo, repo_path], stderr=subprocess.DEVNULL)
        subprocess.check_output(['git', 'checkout', '-b', 'rolling'], cwd=repo_path)
        subprocess.check_output(['git', 'push', '-u', 'origin', 'rolling'], cwd=repo_path)
    if master_hash[0] != package_hash:
        print('hash from build list not equal for master branch hash')
        return False
    if rolling_hash[0] == master_hash[0]:
        print('rolling branch already synced with master')
        return False
    elif rolling_hash[0] != master_hash[0]:
        print('just skip')
        subprocess.check_output(['/usr/bin/git', 'clone', git_repo, repo_path], stderr=subprocess.DEVNULL)
        subprocess.check_output(['git', 'checkout', 'rolling'], cwd=repo_path)
        try:
            # git merge
            print('just skip')
            #subprocess.check_output(['git', 'merge', 'master'], cwd=repo_path, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print('problems with merge master')
        try:
            print('do not push')
#            subprocess.check_output(['git', 'push'], cwd=repo_path)
        except subprocess.CalledProcessError:
            print('problems with pushing, let me push it with -u origin rolling')
#            subprocess.check_output(['git', 'push', '-u', 'origin', 'rolling'], cwd=repo_path, stderr=subprocess.DEVNULL)

    #abf_build(pkg_name, arch)
    if os.path.exists(repo_path) and os.path.isdir(repo_path):
        shutil.rmtree(repo_path)
    print('======================================================================')


def redis_request():
    redis_request = redis.Redis(host='abf.openmandriva.org', password='newpassword')
#    data = redis_request.lrange('cooker_published', 0, -1)
#    print(data)
    to_do = redis_request.blpop(["cooker_published"])
#    print(to_do)
    obtained_json = json.loads(to_do[1])
    build_id = obtained_json['id']
    build_arch = obtained_json['arch']
    print('obtained build id: {}, build arch: {}'.format(build_id, build_arch))
    api_page = 'https://abf.openmandriva.org/api/v1/build_lists/{}'.format(build_id)
    package_name, package_hash = request_build_id(api_page)
    if package_name in blacklist:
        print('package {} is blacklisted'.format(package_name))
        return True
    if git_work(package_name, build_arch, package_hash) is False:
        # probably need to remove it
        push_me_back = '{{"id":{}, "arch":"{}"}}'.format(build_id, build_arch)
        print("not pushing {} back to the redis".format(push_me_back))
#        torpush = ['cooker_published', push_me_back]
#        redis_request.rpush(*torpush)


def run_daemon():
    while True:
        try:
            redis_request()
        except Exception as e:
            print(e)


run_daemon()
