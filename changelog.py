#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
# last days for git log
days = 181

def remove_changelog(spec):
    if os.path.isfile(spec):
        with open(spec, "r") as spec_file:
            lines = spec_file.readlines()

        with open(spec, "w") as spec_file:
            for line in lines:
                if line.startswith("%changelog"):
                    break
                spec_file.write(line)


def generate_changelog(specfile, build_package):
    # cleanup changelog if exist
    remove_changelog(specfile)
    git_log_command = f'LC_ALL=C git log --since="{days} days ago" \
        --pretty="tformat:* %cd %an <%ae> %h %d%n%s%n%b" \
        --date=format:"%a %b %e %Y" --decorate=short'
    git_log = subprocess.check_output(git_log_command, shell=True, cwd=build_package).decode('utf-8')

    git_log_lines = git_log.split('\n')
    modified_log_lines = []
    current_commit = None

    for line in git_log_lines:
        if line.startswith('*'):
            if current_commit:
                # add empty line after each commit
                modified_log_lines.append(current_commit + '\n')
            current_commit = line
        elif line.strip():
            if current_commit:
                words = line.split()
                modified_words = [word if not word.startswith('%') else '%%' + word[1:] for word in words]
                modified_line = ' '.join(modified_words)
                current_commit += f'\n- {modified_line.strip()}'

    if current_commit:
        modified_log_lines.append(current_commit)

    modified_git_log = '\n'.join(modified_log_lines)
    changelog = "%changelog\n" + modified_git_log

    # Check for specific strings and replace the whole line
    modified_changelog_lines = []
    for line in changelog.split('\n'):
        if "Automatic import for version" in line:
            modified_changelog_lines.append("- initial commit message")
        elif "Imported from SRPM" in line:
            modified_changelog_lines.append("- initial commit message")
        else:
            modified_changelog_lines.append(line.strip())

    modified_changelog = '\n'.join(modified_changelog_lines)

    with open(specfile, 'r') as file:
        content = file.read()

    if "%changelog" in content:
        content = content.split("%changelog")[0] + modified_changelog
    else:
        content += "\n" + modified_changelog

    with open(specfile, 'w') as file:
        file.write(content)


# build_package = "/home/fdrt/docker-builder/dracut/"
# specfile = "/home/fdrt/docker-builder/dracut/dracut.spec"
# generate_changelog(specfile, build_package)
