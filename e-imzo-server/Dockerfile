FROM amazoncorretto:8-alpine3.22-jre
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Tashkent /etc/localtime && \
    echo "Asia/Tashkent" > /etc/timezone
RUN mkdir -p /opt/e-imzo-server
COPY /config.properties /opt/e-imzo-server/config/
COPY /logging.properties /opt/e-imzo-server/config/
COPY /e-imzo-server.jar /opt/e-imzo-server/
COPY /lib /opt/e-imzo-server/lib
# Kalitlar image'ga kiritilmaydi — docker-compose volume orqali /opt/e-imzo-server/keys ga ulanadi
WORKDIR /opt/e-imzo-server
EXPOSE 8080
EXPOSE 8081
# vpn.key.password config faylida saqlanmaydi (gitda edi — audit A7): konteyner
# ishga tushganda VPN_KEY_PASSWORD muhit o'zgaruvchisidan (.env) qo'yiladi.
CMD sed -i "s|__VPN_KEY_PASSWORD__|${VPN_KEY_PASSWORD}|" config/config.properties && java -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Tashkent -Djava.util.logging.config.file=config/logging.properties -Dproperties.filename=config/config.properties $JAVA_OPTS -jar e-imzo-server.jar