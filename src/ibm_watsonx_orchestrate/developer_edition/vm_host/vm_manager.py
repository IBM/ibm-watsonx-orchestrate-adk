import logging
import os
from ibm_watsonx_orchestrate.client.utils import get_os_type
from .lima import LimaLifecycleManager
from .wsl import WSLLifecycleManager


logger = logging.getLogger(__name__)


def get_vm_manager(ensure_installed: bool = True):
    system = get_os_type()
    wsl_distro = os.environ.get("WSL_DISTRO_NAME")

    if system == "linux":
        if wsl_distro:
            logger.info(
                "Detected WSL distribution %s; using native Docker and skipping VM layer.",
                wsl_distro,
            )
        else:
            logger.info(
                "Detected Linux host; using native Docker and skipping VM layer."
            )
        return None

    if system == "darwin":
        logger.info("Detected macOS; initializing Lima VM manager.")
        return LimaLifecycleManager(ensure_installed)
    elif system == "windows":
        logger.info("Detected Windows; initializing WSL VM manager.")
        return WSLLifecycleManager(ensure_installed)

    logger.error("Unsupported OS: %s", system)
    raise Exception(f"Unsupported OS: {system}")
