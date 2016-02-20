#!/bin/bash
abf_env(){
echo export BUILD_TOKEN="$BUILD_TOKEN"
echo export BUILD_ARCH="$BUILD_ARCH"
echo export BUILD_PLATFORM="$BUILD_PLATFORM"
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
echo "git clone docker-worker code"
cd
git clone https://github.com/OpenMandrivaSoftware/docker-worker.git
pushd docker-worker
export PATH="${PATH}:/usr/local/rvm/bin"
which rvm
gem install bundler
bundle install
ENV=production CURRENT_PATH=$PWD bundle exec rake abf_worker:start
}

abf_env > $HOME/envfile
prepare_and_run
