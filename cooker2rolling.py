#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import re
import requests
import time
import shutil
import os
import subprocess
import argparse

build_ids = []
tmp_names = []
blacklist = ['llvm', 'gcc', 'binutils', 'glibc', 'boost', 'mesa', 'icu', 'poppler', 'x11-server', 'kernel-release']


def request_builds():
    #    https://abf.openmandriva.org/api/v1/build_lists?filter[build_for_platform_id]=28&filter[status]=6000&filter[ownership]=everything&filter[updated_at_start]=1565540721&per_page=100&page=1
    # updated_at_start = 1565540721
    # current time minus 1 days
    threedaysago = int(time.time()) - 2 * 24 * 3600
    params = {'cooker': 28, 'status': 6000, 'time': threedaysago}
    abf_page = 1
    while True:
        abf_api = 'https://abf.openmandriva.org'
        api_link = '{}/api/v1/build_lists?filter[build_for_platform_id]={}&filter[status]={}&filter[ownership]=everything&filter[updated_at_start]={}&per_page=100&page={}'.format(
            abf_api, params['cooker'], params['status'], params['time'], abf_page)
        print(api_link)
        resp = requests.get(api_link)
        if resp.status_code == 404:
            print('requested api [{}] not found'.format(api_link))
        if resp.status_code == 200:
            page = resp.content.decode('utf-8')
            page2 = json.loads(page)
            name = page2['build_lists']
            # list is empty
            if not name:
                print('we reached last page')
                break
            for build_id in name:
                if 'url' in build_id:
                    build_ids.append('{}'.format(abf_api) + build_id['url'])
        abf_page += 1
#        print(abf_page)

#    for build_id in build_ids:
#        print(build_id)

# мы получили список всех билд листов
# а теперь нужно вытащить имена проектов типа vim и убрать повторяющиеся
# Нужно сделать словарь куда добавить все значения
# которые получатся от реквест билд ид, которые имеют хеш
# потом отфильтровать чтобы не было повторов


def abf_build(package, repo_path):
    try:
        subprocess.check_call(['abf', 'build', '--arch', 'znver1', '--arch', 'x86_64', '--arch', 'i686', '-b', 'rolling', '--no-cached-chroot',
                               '--auto-publish-status=testing', '--update-type', 'enhancement'], cwd=repo_path)
    except subprocess.CalledProcessError as e:
        print(e)
        return False


def request_build_id(page):
    # print(page)
    resp = requests.get(page)
    build_page = resp.content.decode('utf-8')
    page_json = json.loads(build_page)
    package_name = page_json['build_list']['project']['name']
    package_fullname = page_json['build_list']['project']['fullname']
    package_git_url = page_json['build_list']['project']['git_url']
    package_hash = page_json['build_list']['commit_hash']
    print('package name [{}], fullname [{}], git url [{}], hash [{}]'.format(
        package_name, package_fullname, package_git_url, package_hash))
    tmp_names.append(package_name)


def git_work(project):
    git_repo = 'git@github.com:OpenMandrivaAssociation/{}.git'.format(project)
    repo_path = '/tmp/{}'.format(project)
    if os.path.exists(repo_path) and os.path.isdir(repo_path):
        shutil.rmtree(repo_path)
    try:
        subprocess.check_output(
            ['/usr/bin/git', 'clone', '-b', 'master', git_repo, repo_path])
    except subprocess.CalledProcessError:
        print('something went wrong')
    try:
        git_checkout = subprocess.check_output(
            ['git', 'checkout', 'rolling'], cwd=repo_path)
    except subprocess.CalledProcessError:
        print('looks like no rolling branch detected')
        git_checkout = subprocess.check_output(
            ['git', 'checkout', '-b', 'rolling'], cwd=repo_path)
    try:
        git_merge = subprocess.check_output(
            ['git', 'merge', 'master'], cwd=repo_path)
    except subprocess.CalledProcessError:
        print('problems with merge master')
    try:
        git_push = subprocess.check_output(['git', 'push'], cwd=repo_path)
    except subprocess.CalledProcessError:
        print('problems with pushing')
        git_push = subprocess.check_output(
            ['git', 'push', '-u', 'origin', 'rolling'], cwd=repo_path)
    abf_build(project, repo_path)


# request_builds()
#print('{} build list scheduled for processing'.format(len(build_ids)))
# for build_id in build_ids:
#    request_build_id(build_id)
# request_build_id('https://abf.openmandriva.org/api/v1/build_lists/591808')


# print(package_names)

# for pkg in package_names:
#    git_work(pkg)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', nargs='+',help='package to merge and build into rolling')
    parser.add_argument('--file', help='file with packages list')
    parser.add_argument('--buildall', action='store_true', default=False, help='fetch from abf.openmandriva.org cooker all packages that built in last 24h and merge it to rolling')
    args = parser.parse_args()
    if args.file is not None:
        with open(args.file) as file:
            for line in file:
                print(line.strip())
                package = line.strip()
                git_work(package)
    if args.package is not None:
        packages = [i for i in args.package if i is not None]
        for package in packages:
            git_work(package)
    if args.buildall is True:
        request_builds()
        for build_id in build_ids:
            request_build_id(build_id)
        package_names = set(tmp_names) - set(blacklist)
        for pkg in package_names:
            git_work(pkg)
