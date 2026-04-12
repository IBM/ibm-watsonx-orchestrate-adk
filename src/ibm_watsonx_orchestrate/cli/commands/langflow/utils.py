import logging
import sys

from ibm_watsonx_orchestrate.utils.docker_utils import DockerUtils

logger = logging.getLogger(__name__)

def requires_langflow(command):
  def confirm_langflow_running(*args,**kwargs):
    if is_langflow_container_running():
      return command(*args,**kwargs)
    else:
      logger.error(f"Langflow container is not running, to start langflow with orchestrate use 'orchestrate server start --with-langflow'")
      sys.exit(1)

  return confirm_langflow_running

def is_langflow_container_running():
  return DockerUtils.is_docker_container_running("dev-edition-langflow-1")