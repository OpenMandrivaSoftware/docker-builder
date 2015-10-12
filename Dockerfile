FROM openmandriva/cooker

RUN urpmi --auto --auto-update --no-verify-rpm \
 && urpmi --no-suggests --no-verify-rpm --auto mock-urpm git curl ruby sudo \
 && rm -f /etc/localtime \
 && ln -s /usr/share/zoneinfo/Europe/Moscow /etc/localtime \
 && usermod -a -G mock-urpm omv \
 && chown -R omv:mock-urpm /etc/mock-urpm \
 && usermod -a -G wheel omv \
 && rm -rf /var/cache/urpmi/rpms/*

WORKDIR ["/home/omv"]
VOLUME ["/home/omv/output"]

ADD ./build-rpm.sh /build-rpm.sh
ADD ./config-generator.sh /config-generator.sh
ADD ./download_sources.sh /download_sources.sh

USER omv
ENV HOME /home/omv

CMD ["/build-rpm.sh"]
