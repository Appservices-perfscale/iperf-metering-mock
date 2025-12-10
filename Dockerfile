# Cannot use UBI micro images because it doesn't contain a package manager. So instead use UBI minimal
# https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html-single/building_running_and_managing_containers/index#con_understanding-the-ubi-micro-images_assembly_types-of-container-images
FROM registry.access.redhat.com/ubi9-minimal:latest

LABEL description="Prometheus /query_range Mock API for SWATCH metering scale testing"

WORKDIR /home/metering

COPY requirements.txt query_range.py ./

RUN echo "Marker 2023-07-30 01:52" \
    && microdnf update -y \
    && microdnf install -y python3 \
    && python3 -m ensurepip --default-pip \
    && python3 -m pip install -r requirements.txt

EXPOSE 9090

ENTRYPOINT ["python3", "query_range.py"]


# LABEL description="Prometheus mock service for metering testing" \
#       version="1.0"

# WORKDIR /home/metering

# RUN microdnf update -y && \
#     microdnf install -y python3 python3-pip shadow-utils && \
#     useradd -m -u 1001 appuser && \
#     mkdir -p /home/metering && \
#     chown -R appuser:appuser /home/metering && \
#     microdnf clean all && \
#     rm -rf /var/cache /tmp/*

# COPY --chown=appuser:appuser query_range.py requirements.txt ./

# USER appuser

# RUN python3 -m venv venv && \
#     /home/metering/venv/bin/pip3 install --no-cache-dir -r requirements.txt

# EXPOSE 9090

# ENTRYPOINT ["/home/metering/venv/bin/python3", "query_range.py"]
