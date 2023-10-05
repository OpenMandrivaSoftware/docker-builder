ARG ARCH_REL=x86_64
FROM openmandriva/cooker:${ARCH_REL}
ENV RARCH x86_64

RUN dnf5 --no-gpgcheck --refresh --assumeyes --no-docs --setopt=install_weak_deps=False upgrade \
 && rm -f /etc/localtime \
 && ln -s /usr/share/zoneinfo/UTC /etc/localtime \
 && dnf5 --no-gpgcheck --assumeyes --setopt=install_weak_deps=False --no-docs install mock git coreutils curl sudo builder-c procps-ng tar locales-en \
 findutils util-linux wget rpmdevtools sed grep xz gnupg hostname python-yaml nosync python-magic \
 && sed -i -e "s/Defaults    requiretty.*/ #Defaults    requiretty/g" /etc/sudoers \
 && echo "%mock ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
 && usermod -a -G mock omv \
 && cp -a /etc/skel /home/omv \
 && chown -R omv:omv /home/omv \
 && chown -R omv:mock /etc/mock \
 && dnf5 --assumeyes autoremove \
 && dnf5 clean all \
 && rm -rf /var/cache/libdnf5/* \
 && rm -rf /usr/share/man/ /usr/share/cracklib /usr/share/doc /usr/share/licenses /tmp/*

RUN if [ $RARCH = "x86_64" ]; then dnf5 --no-gpgcheck --assumeyes install qemu-static-aarch64 qemu-static-arm qemu-static-riscv64; fi

RUN rm -rf /var/cache/libdnf5/* \
 && rm -rf /var/lib/rpm/__db.*

ENTRYPOINT ["/usr/bin/builder"]
