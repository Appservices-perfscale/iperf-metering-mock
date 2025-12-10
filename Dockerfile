FROM registry.access.redhat.com/ubi9-minimal:latest

LABEL description="Prometheus mock service for metering testing" \
      version="1.0"

WORKDIR /home/metering

RUN microdnf update -y && \
    microdnf install -y python3 python3-pip shadow-utils && \
    useradd -m -u 1001 appuser && \
    mkdir -p /home/metering && \
    chown -R appuser:appuser /home/metering && \
    microdnf clean all && \
    rm -rf /var/cache /tmp/*

COPY --chown=appuser:appuser query_range.py requirements.txt ./

USER appuser

RUN python3 -m venv venv && \
    /home/metering/venv/bin/pip3 install --no-cache-dir -r requirements.txt && \
    rm -rf ~/.cache/pip

EXPOSE 9090

ENTRYPOINT ["/home/metering/venv/bin/python3", "query_range.py"]
