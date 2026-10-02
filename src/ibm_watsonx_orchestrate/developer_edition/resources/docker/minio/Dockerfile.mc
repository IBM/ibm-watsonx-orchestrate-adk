FROM --platform=linux/amd64 alpine:3.20

ARG MC_VERSION=RELEASE.2025-08-13T08-35-41Z

RUN addgroup -S mc && adduser -S mc -G mc

RUN wget -q -O /usr/bin/mc \
      "https://github.com/minio/mc/releases/download/${MC_VERSION}/mc.linux-amd64.${MC_VERSION}" \
    && chmod +x /usr/bin/mc

USER mc

ENTRYPOINT ["/usr/bin/mc"]
