FROM amazoncorretto:8-alpine3.22-jre
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Tashkent /etc/localtime && \
    echo "Asia/Tashkent" > /etc/timezone
RUN mkdir -p /opt/e-imzo-server
COPY /config.properties /opt/e-imzo-server/config/
COPY /logging.properties /opt/e-imzo-server/config/
COPY /e-imzo-server.jar /opt/e-imzo-server/
COPY /lib /opt/e-imzo-server/lib
COPY /keys /opt/e-imzo-server/keys
WORKDIR /opt/e-imzo-server
EXPOSE 8080
EXPOSE 8081
CMD java -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Tashkent -Djava.util.logging.config.file=config/logging.properties -Dproperties.filename=config/config.properties $JAVA_OPTS -jar e-imzo-server.jar