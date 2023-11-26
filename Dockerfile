ARG debian:12
FROM debian:12

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install packages
RUN apt-get update
RUN apt-get install -y jq tzdata python3 python3-paho-mqtt python3-pymodbus python3-requests python3-configobj python3-apscheduler python3-yaml
RUN apt-get clean -y
RUN rm -rf /var/lib/apt/lists/*

# Copy data
COPY *.py /

RUN mkdir -p /etc/growatt/maps

COPY maps/*.yaml /etc/growatt/maps/

RUN chmod a+x /interrogator.py

ENTRYPOINT [ "/usr/bin/python3", "/interrogator.py" ]