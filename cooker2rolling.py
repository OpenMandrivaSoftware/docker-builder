#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import re
import requests
import time


def request_builds():
    #    https://abf.openmandriva.org/api/v1/build_lists?filter[build_for_platform_id]=28&filter[status]=6000&filter[ownership]=everything&filter[updated_at_start]=1565540721&per_page=100&page=1
    # updated_at_start = 1565540721
    # current time minus 1 days
    build_ids = []
    threedaysago = int(time.time()) - 24 * 3600
    params = {'cooker': 28, 'status': 6000, 'time': threedaysago}

    abf_api = 'https://abf.openmandriva.org'
    page = 1
    api_link = '{}/api/v1/build_lists?filter[build_for_platform_id]={}&filter[status]={}&filter[ownership]=everything&filter[updated_at_start]={}&per_page=100&page={}'.format(
        abf_api, params['cooker'], params['status'], params['time'], page)
    print(api_link)
    resp = requests.get(api_link)
    if resp.status_code == 404:
        print('requested api [{}] not found'.format(api_link))
    if resp.status_code == 200:
        page = resp.content.decode('utf-8')
        page2 = json.loads(page)
        name = page2['build_lists']
        print(name)
        # list is empty
        if not name:
            print('we reached last page')
        for build_id in name:
            if 'url' in build_id:
                build_ids.append('{}'.format(abf_api) + build_id['url'])

    for build_id in build_ids:
        print(build_id)


request_builds()
