FROM us.icr.io/watson_assistant/production/watson-assistant-base-common-rhubi8-py311

# note docker is actually podman in rhubi8
# Commented out: the AppStream repo providing docker/podman is not reliably available in this
# base image, and docker is not needed inside the build container — it is only invoked from
# the CI runner host. See .sps/sps_debug.md for full investigation history.
#RUN microdnf install docker
#RUN microdnf install -y yum-utils
#RUN yum-config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
#RUN microdnf repoquery docker-ce-stable
#RUN microdnf -y install docker-ce docker-ce-cli
#RUN systemctl start docker
RUN pip install hatch
RUN pip install twine
