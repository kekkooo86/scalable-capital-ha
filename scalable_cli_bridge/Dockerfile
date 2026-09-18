FROM ghcr.io/home-assistant/base-debian:trixie

ARG BUILD_ARCH
ARG SC_VERSION=1.0.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        ca-certificates \
        curl \
        tar \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${BUILD_ARCH}" in \
        amd64) SC_ARCH="x86_64" ;; \
        aarch64) SC_ARCH="aarch64" ;; \
        *) echo "unsupported arch: ${BUILD_ARCH}"; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/sc.tgz \
        "https://github.com/ScalableCapital/scalable-cli/releases/download/v${SC_VERSION}/sc-v${SC_VERSION}-linux-${SC_ARCH}-gnu.tar.gz"; \
    tar -xzf /tmp/sc.tgz -C /tmp; \
    install -m 0755 "/tmp/sc-v${SC_VERSION}-linux-${SC_ARCH}-gnu/sc" /usr/local/bin/sc; \
    rm -rf /tmp/sc.tgz "/tmp/sc-v${SC_VERSION}-linux-${SC_ARCH}-gnu"; \
    /usr/local/bin/sc --version

COPY server.py /app/server.py
COPY www /app/www
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8788
CMD ["/run.sh"]
