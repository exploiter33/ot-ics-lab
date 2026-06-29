FROM docker.elastic.co/logstash/logstash:8.11.0

RUN rm -f /usr/share/logstash/pipeline/*.conf

COPY pipeline/ /usr/share/logstash/pipeline/
COPY config/ /usr/share/logstash/config/

EXPOSE 5000 5000/udp
