FROM openmandriva/cooker
#FROM openmandriva/cooker-aarch64
#FROM openmandriva/cooker-armv7hl
# replace me with armv7hl, aarch64
ENV ARCH x86_64
ENV RUBY=ruby-2.2.3

RUN urpmi --auto --auto-update --no-verify-rpm \
 && urpmi.addmedia contrib http://abf-downloads.rosalinux.ru/cooker/repository/$ARCH/contrib/release/ \
 && rm -f /etc/localtime \
 && ln -s /usr/share/zoneinfo/UTC /etc/localtime \
 && gpg2 --keyserver hkp://keys.gnupg.net --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3 \
 && urpmi --no-suggests --no-verify-rpm --auto mock-urpm git curl sudo gnutar yaml-devel gcc-c++ readline-devel openssl-devel libtool bison\
 && sed -i -e "s/Defaults    requiretty.*/ #Defaults    requiretty/g" /etc/sudoers \
 && echo "%mock-urpm ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
 && /bin/bash -l -c "curl -L get.rvm.io | bash -s stable" \
 && export PATH=$PATH:/usr/local/rvm/bin/ \
 && /bin/bash -l -c "source /usr/local/rvm/scripts/rvm" \
 && /bin/bash -l -c "rvm install $RUBY" \
 && /bin/bash -l -c "rvm use $RUBY" \
 && /bin/bash -l -c "rvm $RUBY do rvm gemset create abf-worker" \
 && /bin/bash -l -c "rvm use $RUBY@abf-worker --default" \
 && /bin/bash -l -c "rvm gemset create abf-worker" \
 && rm -rf /var/cache/urpmi/rpms/*

## put me in RUN if you have more than 16gb of RAM
# && echo "tmpfs /var/lib/mock-urpm/ tmpfs defaults,size=4096m,uid=$(id -u omv),gid=$(id -g omv),mode=0700 0 0" >> /etc/fstab \
#

ADD ./build-rpm.sh /mdv/build-rpm.sh
ADD ./config-generator.sh /mdv/config-generator.sh
ADD ./download_sources.sh /mdv/download_sources.sh

ENV HOME /root

COPY entrypoint.sh /sbin/entrypoint.sh
ENTRYPOINT ["/sbin/entrypoint.sh"]
