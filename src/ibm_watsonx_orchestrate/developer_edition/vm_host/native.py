import logging
import shutil
import subprocess
from typing import List, Optional
from ibm_watsonx_orchestrate.client.utils import command_to_list, get_os_type
from ibm_watsonx_orchestrate.developer_edition.vm_host.vm_host import VMLifecycleManager
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest, VMLifecycleException
from ibm_watsonx_orchestrate.utils.utils import singleton

logger = logging.getLogger(__name__)

@singleton
class NativeDockerManager(VMLifecycleManager):
  """
  VMLifecycleManager based class for interacting with the native docker environment.
  """

  def __init__(self, ensure_installed: bool = True):
    """Ensures docker engine has been installed"""
    docker_executable_path = shutil.which("docker")
    if ensure_installed and not docker_executable_path:
      raise VMLifecycleException(f"Docker must be installed locally to use native docker")
    logger.warning(f"Using user managed docker installation, this configuration is not officially supported")
    self.docker_path = docker_executable_path
    self.os_type = get_os_type()

  def get_path_in_container(self, path: str) -> str:
    """VMLifecycleManager utility function, not required for Native install but maintained for compatibility"""
    return path

  def start_server(self):
    """Ensures docker daemon has started"""
    if not _check_docker_status(docker_path=self.docker_path):
      match (self.os_type):
        case "wsl" | "linux" | "darwin":
          _bash_docker_startup()
        case _:
          raise VMLifecycleException(f"Docker daemon is not running, please ensure docker is running before starting orchestrate")

  def stop_server(self):
    """Ensures shutdown of docker containers"""
    try:
      docker_ps = subprocess.run(
        [self.docker_path, "ps", "--format", "'{{.Names}}'"],
        capture_output=True,
        text=True
      )
      docker_containers = [name for name in docker_ps.split() if name.startswith("dev-edition-")]
      if docker_containers:
        subprocess.run(
          [self.docker_path, "stop"] + docker_containers,
          check=True
        )
    except:
      return
  
  def shell(
      self,
      command: str | List[str],
      capture_output: bool = False,
      check: bool = False,
      text: bool = True
  ) -> Optional[str]:
    """Run a shell command in the local environment"""
    try:
      return subprocess.run(command_to_list(command), capture_output=capture_output, check=check, text=text)
    except:
      raise VMLifecycleException(f"Shell command '{command}' failed to run")

  def run_docker_command(self, command: str | List[str], input: str | None = None, **kwargs) -> Optional[str]:
    """Run a Docker command in the local environment"""
    return subprocess.run(
      [self.docker_path] + command_to_list(command),
      input=input,
      text=True,
      **kwargs
    )

  def show_current_context(self) -> Optional[str]:
    """Show current Docker context"""
    return subprocess.run(
      [self.docker_path, "context", "show"]
    )

  def get_container_logs(self, container_id: str, container_name: str) -> Optional[str]:
    """
    Fetch logs for a Docker container by its ID or name.
    At least one of container_id or container_name must be provided.
    """

    target = container_id or container_name

    return subprocess.run(
        [self.docker_path, "logs", target],
        text=True,
        check=True
    )


  ## Invalid Commands for Native environment

  def delete_server(self):
    raise VMLifecycleException(f"Cannot delete VM host when using user managed docker")

  def edit_server(self, *args, **kwargs) -> None:
    raise VMLifecycleException(f"Cannot edit VM host configs when using user managed docker")

  def attach_docker_context(self):
    raise VMLifecycleException(f"Cannot switch docker context when using user managed docker")

  def release_docker_context(self):
    raise VMLifecycleException(f"Cannot switch docker context when using user managed docker")

  def ssh(self):
    raise VMLifecycleException(f"Cannot ssh into VM when using user managed docker")
  
  def is_server_running(self):
    return _check_docker_status(docker_path=self.docker_path)
  
  def check_and_ensure_memory_for_doc_processing(self, min_memory_gb: int = 24) -> None:
    """ Native Docker doesn't use a VM, so memory management is handled by the host system. """
    pass



def _check_docker_status(docker_path: str = "docker"):
  try:
    subprocess.run(
      [docker_path, "stats", "--no-stream"],
      check=True,
      capture_output=True
    )
    return True
  except:
    return False

def _bash_docker_startup():
  try:
    subprocess.run(
      [
        "bash", "-c",
        r"""
        sudo dockerd >&/dev/null &
        """
      ],
      check=True
    )
    logger.info("Docker daemon started sucessfully")
  except:
    raise VMLifecycleException(f"Unable to start docker daemon, please ensure docker is running before starting orchestrate")


  

