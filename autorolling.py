#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import redis
import requests
import shutil
import os
import subprocess

blacklist = ['llvm', 'gcc',
             'binutils', 'glibc',
             'boost', 'mesa',
             'icu', 'poppler',
             'x11-server', 'kernel-release']


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


def abf_build(package, repo_path, arch):
    try:
        subprocess.check_call(['abf', 'build', '--arch', arch, '-b', 'rolling', '--testing', '--no-cached-chroot', '--auto-publish-status=testing', '--update-type', 'enhancement'], cwd=repo_path)
    except subprocess.CalledProcessError as e:
        print(e)
        return False


def git_work(pkg_name, arch, package_hash):
    git_repo = 'git@github.com:OpenMandrivaAssociation/{}.git'.format(pkg_name)
    repo_path = '/tmp/{}'.format(pkg_name)
    if os.path.exists(repo_path) and os.path.isdir(repo_path):
        shutil.rmtree(repo_path)
    try:
        subprocess.check_output(['/usr/bin/git', 'clone', '-b', 'master', git_repo, repo_path])
    except subprocess.CalledProcessError:
        print('something went wrong')
    try:
        master_branch_hash = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'master'], cwd=repo_path)
        if master_branch_hash.decode('utf-8').strip() != package_hash:
            print('hash from build list not equal for master branch hash')
            return False
    except subprocess.CalledProcessError:
        print('error with git rev-parse')
    try:
        # checkout to rolling without -b
        subprocess.check_output(
            ['git', 'checkout', 'rolling'], cwd=repo_path)
    except subprocess.CalledProcessError:
        print('looks like no rolling branch detected')
        # git checkout to rolling
        subprocess.check_output(['git', 'checkout', '-b', 'rolling'], cwd=repo_path)
    try:
        # git merge
        subprocess.check_output(['git', 'merge', 'master'], cwd=repo_path)
    except subprocess.CalledProcessError:
        print('problems with merge master')
    try:
        subprocess.check_output(['git', 'push'], cwd=repo_path)
    except subprocess.CalledProcessError:
        print('problems with pushing')
        subprocess.check_output(['git', 'push', '-u', 'origin', 'rolling'], cwd=repo_path)
    abf_build(pkg_name, repo_path, arch)
    shutil.rmtree(repo_path)


def redis_request():
    redis_request = redis.Redis(host='abf.openmandriva.org', password='')
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
