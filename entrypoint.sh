#!/bin/bash
abf_env(){
echo export BUILD_TOKEN="$BUILD_TOKEN"
echo export BUILD_ARCH="$BUILD_ARCH"
echo export BUILD_PLATFORM="$BUILD_PLATFORM"
echo export NATIVE_ARCH="$NATIVE_ARCH"
}

prepare_and_run() {
OUTPUT_FOLDER=${HOME}/output
if [ ! -d "$OUTPUT_FOLDER" ]; then
    mkdir -p $OUTPUT_FOLDER
else
    rm -f $OUTPUT_FOLDER/*
fi
source /etc/profile
echo "prepare ABF builder environment"

abf_env > $HOME/envfile
prepare_and_run
