FROM openmandriva/cooker
#FROM openmandriva/cooker-aarch64
#FROM openmandriva/cooker-armv7hl
# replace me with armv7hl, aarch64
ENV RARCH x86_64

RUN dnf --nogpgcheck --refresh --assumeyes upgrade \
 && rm -f /etc/localtime \
 && ln -s /usr/share/zoneinfo/UTC /etc/localtime \
 && gpg --keyserver hkp://keys.gnupg.net --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3 \
 && dnf --nogpgcheck --assumeyes install mock git curl sudo builder-c procps-ng \
 && sed -i -e "s/Defaults    requiretty.*/ #Defaults    requiretty/g" /etc/sudoers \
 && echo "%mock ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
 && adduser omv \
 && usermod -a -G mock omv \
 && chown -R omv:mock /etc/mock \
 && rm -rf /var/cache/dnf/* \
 && rm -rf /usr/share/man/ /usr/share/cracklib /usr/share/doc

RUN if [ $RARCH = "x86_64" ]; then dnf --nogpgcheck --assumeyes install qemu-static-aarch64 qemu-static-arm; fi

## put me in RUN if you have more than 16gb of RAM
# && echo "tmpfs /var/lib/mock/ tmpfs defaults,size=4096m,uid=$(id -u omv),gid=$(id -g omv),mode=0700 0 0" >> /etc/fstab \
#

ENTRYPOINT ["/usr/bin/builder"]
