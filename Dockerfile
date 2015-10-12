FROM openmandriva/cooker

RUN urpmi.update -a \
 && urpmi --auto --auto-update --no-verify-rpm \
 && urpmi --no-suggests --no-verify-rpm mock-urpm git curl ruby sudo \
 && unlink /etc/localtime \
 && ln -s /usr/share/zoneinfo/Europe/Moscow /etc/localtime \
 && usermod -a -G mock-urpm omv \
 && chown -R omv:mock-urpm /etc/mock-urpm \
 && usermod -a -G wheel omv \
 && rm -rf /var/cache/urpmi/rpms/*

COPY abf_yml.rb /usr/bin/abf_yml.rb

RUN chmod 755 /usr/bin/abf_yml.rb
RUN ln -s /usr/bin/abf_yml.rb /usr/bin/abf_yml

WORKDIR ["/home/omv"]
VOLUME ["/home/omv/output"]

ADD ./build-rpm.sh /build-rpm.sh
ADD ./config-generator.sh /config-generator.sh
RUN chmod +x /build-rpm.sh /config-generator.sh

USER omv
ENV HOME /home/omv

CMD ["/build-rpm.sh"]
