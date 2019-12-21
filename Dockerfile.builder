FROM openmandriva/cooker:ARCH_REL
ENV RARCH ARCH_TARGET

RUN dnf --nogpgcheck --refresh --assumeyes --nodocs --setopt=install_weak_deps=False upgrade \
 && rm -f /etc/localtime \
 && ln -s /usr/share/zoneinfo/UTC /etc/localtime \
 && dnf --nogpgcheck --assumeyes --setopt=install_weak_deps=False --nodocs install mock git coreutils curl sudo builder-c procps-ng tar \
 findutils util-linux wget rpmdevtools sed grep xz gnupg hostname python-yaml nosync \
 && sed -i -e "s/Defaults    requiretty.*/ #Defaults    requiretty/g" /etc/sudoers \
 && echo "%mock ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
 && adduser omv \
 && usermod -a -G mock omv \
 && chown -R omv:mock /etc/mock \
 && dnf reinstall -y locales-en \
 && dnf --assumeyes autoremove \
 && dnf clean all \
 && rm -rf /var/cache/dnf/* \
 && rm -rf /var/lib/dnf/yumdb/* \
 && rm -rf /var/lib/dnf/history/* \
 && rm -rf /usr/share/man/ /usr/share/cracklib /usr/share/doc /usr/share/licenses /tmp/*

RUN if [ $RARCH = "x86_64" ]; then dnf --nogpgcheck --assumeyes install qemu-static-aarch64 qemu-static-arm qemu-static-riscv64; fi

RUN rm -rf /var/lib/dnf/yumdb/* \
 && rm -rf /var/cache/dnf/* \
 && rm -rf /var/lib/rpm/__db.*

ENTRYPOINT ["/usr/bin/builder"]
