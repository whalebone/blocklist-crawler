FROM ubuntu:20.04
MAINTAINER Václav Brůžek <vaclav.bruzek@whalebone.io>
ENV TZ=Europe/Prague
RUN apt-get update -y && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get install -y python3-pip openjdk-8-jre nano cron && \
    apt-get clean  && \ 
    rm -rf /var/lib/apt/lists/ /tmp/ /var/tmp/*

RUN pip3 --no-cache-dir install apscheduler tabula-py requests beautifulsoup4 urlextract

RUN mkdir -p /opt/crawler/logs/ && mkdir /opt/crawler/exports/
WORKDIR /opt/crawler/
COPY . .

CMD ["python3","main.py"]