from typing import Optional
from ibm_watsonx_orchestrate.cli.config import SETTINGS_HEADER, USE_NATIVE_DOCKER, Config
from ibm_watsonx_orchestrate.client.utils import get_os_type
from ibm_watsonx_orchestrate.developer_edition.vm_host.native import NativeDockerManager
from .lima import LimaLifecycleManager
from .wsl import WSLLifecycleManager

def get_vm_manager(ensure_installed: bool = True):
  # check for native config
  cfg = Config()
  use_native = cfg.read(SETTINGS_HEADER, USE_NATIVE_DOCKER)
  if use_native:
    return NativeDockerManager(ensure_installed=ensure_installed)
  
  # otherwise infer docker host from system
  system = get_os_type()
  match(system):
    case "darwin" | "linux":
      return LimaLifecycleManager(ensure_installed=ensure_installed)
    case "windows":
      return WSLLifecycleManager(ensure_installed=ensure_installed)
    case _:
      raise Exception(f"Unsupported OS: {system}. Please run 'orchestrate settings docker host --user-managed' to use the local Docker install instead.")
