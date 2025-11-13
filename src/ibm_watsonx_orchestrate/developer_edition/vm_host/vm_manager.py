from ibm_watsonx_orchestrate.client.utils import get_os_type
from .lima import LimaLifecycleManager
from .wsl import WSLLifecycleManager

def get_vm_manager(ensure_installed: bool = True):
    system = get_os_type()
    if system in ("darwin", "linux"):
        return LimaLifecycleManager(ensure_installed)
    elif system == "windows":
        return WSLLifecycleManager(ensure_installed)
    else:
        raise Exception(f"Unsupported OS: {system}")

