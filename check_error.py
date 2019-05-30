#!/usr/bin/env python
import re
import mmap
import os
import sys

err_type = ['Segmentation fault', 'A fatal error has been detected by the Java Runtime Environment',
            'error:(.*)field(.*)has incomplete type', 'error:(.*)conflicting types for', 'No rule to make target(.*)',
            'failed to allocate (.*) bytes for output file: Cannot allocate memory', 'cp: cannot stat (.*):(.*)',
            'can\'t find file to patch at input line (.*)', 'No matching package to install: (.*)',
            'package (.*) requires (.*) but none of the providers can be installed$']

pattern_string = '|'.join(err_type)
pattern = re.compile(pattern_string)

got_match = False


def known_errors(logfile):
    if os.path.exists(logfile) and os.path.getsize(logfile) > 0:
        msgf = open(logfile, 'r')
        regex = 'No rule to make target(.*)'
        for line in msgf:
            #errors = re.findall(regex, line)
            errors = re.finditer(pattern, line)
            if errors:
                for error in errors:
                    print(error.group(0))
                    got_match = True
                    # exit from iteration
                    return


known_errors('no_file_topatch.log')
known_errors('no_package_to_install.log')
known_errors('no_such_package_in_repo.log')
