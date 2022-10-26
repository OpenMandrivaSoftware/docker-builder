#!/usr/bin/env python3
import re
import mmap
import os
import sys
import io
import argparse
import magic
import gzip
import struct

err_type = ['Segmentation fault',
            'A fatal error has been detected by the Java Runtime Environment',
            'error:(.*)field(.*)has incomplete type',
            'error:(.*)conflicting types for',
            'No rule to make target (.*)',
            'failed to allocate (.*) bytes for output file: Cannot allocate memory',
            'cp: cannot stat (.*):(.*)',
            'can\'t find file to patch at input line (.*)',
            'No matching package to install: (.*)',
            'package (.*) requires (.*) but none of the providers can be installed$',
            'unable to execute command: (.*)',
            '(.*) is a protected member of (.*)',
            'undefined reference to (.*)',
            'no matching function for call to (.*)',
            'bytecode stream in file (.*) generated with (.*)',
            'Could not find a configuration file for package (.*)',
            'variable has incomplete type (.*)',
            'File must begin with (.*)', 'Bad source: (.*)',
            'File not found: (.*)', 'Installed \(but unpackaged\) file\(s\) found',
            'cannot find -l(.*)', 'implicit declaration of function (.*)',
            '\'(.*)\' file not found', 'use of undeclared identifier (.*)',
            'function cannot return function type (.*)',
            'unknown type name (.*)', 'incomplete definition of type (.*)',
            'Problem encountered: Man pages cannot be built: (.*)',
            'format string is not a string literal (.*)']


def write_log(message, fail_log):
    try:
        logger = open(fail_log, 'a')
        logger.write(message + '\n')
        logger.close()
    except IOError:
        print("Can't write to log file: " + fail_log)
    print(message)


def known_errors(logfile, fail_log):
    sz = os.path.getsize(logfile)
    if os.path.exists(logfile) and sz > 0:
        if magic.detect_from_filename(logfile).mime_type == 'application/gzip':
            handle = open(logfile, "r")
            # let's mmap piece of memory
            # as we unpacked gzip
            tmp_mm = mmap.mmap(handle.fileno(), sz, access=mmap.ACCESS_READ)
            real_sz = struct.unpack("@I", tmp_mm[-4:])[0]
            mm = mmap.mmap(-1, real_sz, prot=mmap.PROT_READ | mmap.PROT_WRITE)
            gz = gzip.GzipFile(fileobj=tmp_mm)
            for line in gz:
                mm.write(line)
            tmp_mm.close()
            gz.close()
            handle.close
        else:
            msgf = io.open(logfile, "r", encoding="utf-8")
            mm = mmap.mmap(msgf.fileno(), sz, access=mmap.ACCESS_READ)
            msgf.close()
        for pat in err_type:
            error = re.search(pat.encode("utf-8"), mm)
            if error:
                print(error.group(0).decode('utf-8'))
                write_log(error.group(0).decode('utf-8'), fail_log)
                break
            else:
                common_pattern = 'error: (.*)'
                error = re.search(common_pattern.encode("utf-8"), mm)
                if error:
                    print(error.group(0).decode('utf-8'))
                    write_log(error.group(0).decode('utf-8'), fail_log)
                    break
                else:
                    common_pattern = '(.*)Stop.'
                    error = re.search(common_pattern.encode("utf-8"), mm)
                    if error:
                        print(error.group(0).decode('utf-8'))
                        write_log(error.group(0).decode('utf-8'), fail_log)
                        break
        mm.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run me over the buildlog')
    parser.add_argument('-f', '--file', help='build.log requires', required=True)
    args = vars(parser.parse_args())
    if args['file']:
        try:
            known_errors(args['file'], 'fail.log')
        except OSError as o:
            print('Sorry the file you asked does not exists!')
            print(str(o))

# known_errors('build.log.gz', 'fail.log')
# known_errors('build.log', 'fail.log')
# known_errors('no_file_topatch.log')
# known_errors('no_package_to_install.log')
# known_errors('no_such_package_in_repo.log')
# known_errors('unable_to_execute.log')
# known_errors('protected_member.log')
# known_errors('undef_reference_to.log')
# known_errors('no_matching_func_to_call.log')
# known_errors('bytecode_generated_with_lto.log')
# known_errors('config_cmake_not_found.log')
# known_errors('variable_incompl_type.log')
# known_errors('file_must_begin.log')
# known_errors('file_not_found.log')
# known_errors('cannot_find_lib.log')
# known_errors('header_not_found.log')
# known_errors('func_cant_return_some_shit.log')
# known_errors('unknown_type_name.log')
# known_errors('installed_but_unpkgd.log')
