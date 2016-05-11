#!/bin/bash
do_restore() {
abfyml=.abf.yml

local file sha
if [ -e "${abfyml}" ]; then
  echo "parsing file '${abfyml}'"
  sed -ne '/^[Ss]ources\:.*$/,$p' ${abfyml} | \
  sed -rn '$G;s/^[\"'\''[:space:]]*([^[:space:]:\"'\'']+)[\"'\''[:space:]]*.*[\"'\''[:space:]]*([0-9a-fA-F]{40})[\"'\''[:space:]]*$/\1 \2/p' | \
  while read file sha; do
    echo -n "found entry: file=${file} ... "
    if [ -e ${file} ]; then
      if echo "${sha}  ${file}" | sha1sum -c --status; then
        echo "ok"
      else
        echo "sha1sum INCORRECT! skipping..."
      fi
    else
      echo -n "try to download... "
      if curl -L "http://file-store.openmandriva.org/download/${sha}" -o "${file}"; then
        echo "ok"
        echo -n "check sum... "
        if echo "${sha}  ${file}" | sha1sum -c --status; then
          echo "ok"
        else
          echo "sha1sum INCORRECT! skipping..."
	  echo "remove file ${file}"
	  rm -f ${file}
        fi
      else
        echo "filed! skipping..."
      fi
    fi
  done
fi
}
do_restore
