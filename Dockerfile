FROM openmandriva/cooker

RUN urpmi.update -a \
 && urpmi --auto --auto-update \
 && urpmi --no-suggests --no-verify-rpm mock-urpm git curl ruby sudo \
 && unlink /etc/localtime \
 && ln -s /usr/share/zoneinfo/Europe/Moscow /etc/localtime \
 && usermod -a -G mock-urpm omv \
 && usermod -a -G wheel omv \
 && rm -rf /var/cache/urpmi/rpms/*

COPY abf_yml.rb /usr/bin/abf_yml.rb
COPY config-x86_64.cfg /etc/mock-urpm/cooker-x86_64.cfg
RUN ln -s /etc/mock-urpm/cooker-x86_64.cfg /etc/mock-urpm/default.cfg

RUN chmod 755 /usr/bin/abf_yml.rb
RUN ln -s /usr/bin/abf_yml.rb /usr/bin/abf_yml

WORKDIR ["/home/omv"]
VOLUME ["/home/omv/output"]

ADD ./build-rpm.sh /build-rpm.sh
RUN chmod +x /build-rpm.sh

USER omv
ENV HOME /home/omv

CMD ["/build-rpm.sh"]
