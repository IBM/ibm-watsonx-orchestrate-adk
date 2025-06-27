FROM docker-na-public.artifactory.swg-devops.com/hyc-odm-dockerhub-docker-remote/docker:dind

RUN apk add --no-cache python3 py3-pip \
    && python3 --version

RUN apk add --no-cache util-linux

# ARG PYTHON_VERSION=3.13.2

# RUN apk add --no-cache \
#     build-base \
#     libffi-dev \
#     openssl-dev \
#     bzip2-dev \
#     zlib-dev \
#     xz-dev \
#     wget

# ENV PYTHON_VERSION=3.13.2

# RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz && \
#     tar xzf Python-${PYTHON_VERSION}.tgz && \
#     cd Python-${PYTHON_VERSION} && \
#     ./configure --enable-optimizations && \
#     make altinstall && \
#     pip3.13 install --upgrade pip

# RUN python3 --version
# RUN pip --version