FROM amazoncorretto:8-alpine3.22-jre

WORKDIR /opt/e-imzo-server

COPY e-imzo-server.jar .
COPY config.properties config/config.properties
COPY logging.properties config/logging.properties
COPY lib lib
COPY keys keys

EXPOSE 8080
EXPOSE 8081

CMD java \
 -Dfile.encoding=UTF-8 \
 -Djava.util.logging.config.file=config/logging.properties \
 -Dproperties.filename=config/config.properties \
 -jar e-imzo-server.jar
