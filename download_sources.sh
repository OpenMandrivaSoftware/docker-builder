#!/bin/sh
do_restore() {
abfyml=.abf.yml

local file sha
if [ -e "${abfyml}" ]; then
    printf "%s\\n" "parsing file '${abfyml}'"
    sed -ne '/^[Ss]ources\:.*$/,$p' ${abfyml} | \
    sed -rn '$G;s/^[\"'\''[:space:]]*([^[:space:]:\"'\'']+)[\"'\''[:space:]]*.*[\"'\''[:space:]]*([0-9a-fA-F]{40})[\"'\''[:space:]]*$/\1 \2/p' | \

    while read -r file sha; do
	printf "%s\\n" "found entry: file=${file} ... "
	if [ -e "${file}" ]; then
	    if echo "${sha}  ${file}" | sha1sum -c --status; then
		printf '%s\n' 'File sha1sum correct.'
	    else
		printf '%s\n' 'sha1sum INCORRECT! skipping...'
	    fi
	else
	    printf '%s\n' 'Trying to download file... '
	    if curl -L "http://file-store.openmandriva.org/download/${sha}" -o "${file}"; then
		printf '%s\n' 'Download finished.'
		printf '%s\n' 'Checking file sha1sum'
		if echo "${sha}  ${file}" | sha1sum -c --status; then
		    printf '%s\n' 'sha1sum is correct'
		else
		    printf '%s\n' "sha1sum INCORRECT! Removing file ${file}"
		    rm -f "${file}"
    		fi
    	    else
    		printf '%s\n' 'Download failed.'
    	    fi
	fi
    done
fi
}

do_restore
