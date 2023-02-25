FROM python:3.7.0-alpine3.8
MAINTAINER William Digan william.digan@aphp.fr
WORKDIR /home
RUN pip3 install -I intervaltree==3.1.0
RUN apk update \
  && apk add --no-cache  --virtual build-deps gcc python3-dev musl-dev \
  && apk add postgresql-dev \
  && pip install psycopg2 \
  && apk del build-deps

#important for nextflow compatibility
#https://github.com/bgruening/docker-busybox-bash/pull/1
RUN apk add --no-cache procps bash


RUN apk add --no-cache graphviz
RUN pip3 install --upgrade pip
RUN pip3 install gprof2dot

ENV DOCKYARD_SRC=duplication
#Directory in container for all project files
ENV DOCKYARD_SRVHOME=/srv
#Directory in container for project source files
ENV DOCKYARD_SRVPROJ=/srv/hegpdup
#Update the default application repository sources list

# Create application subdirectories
# RUN mkdir $DOCKYARD_SRVHOME
ADD . /srv/hegpdup
# Install Python Source
WORKDIR $DOCKYARD_SRVPROJ
RUN pip3 install .

#to start the server uncomment this
RUN touch /home/logs.txt
# CMD ["tail -f /ho;e/logs.txt"]
SHELL ["/bin/bash", "-c"]

CMD ["tail", "-f", "/home/logs.txt"]
