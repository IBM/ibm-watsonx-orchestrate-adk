import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Union
import zipfile
import sys
import re
import requests
import time
from ibm_watsonx_orchestrate.developer_edition.vm_host.constants import VM_NAME, DEFAULT_CPUS, DEFAULT_MEMORY
from ibm_watsonx_orchestrate.developer_edition.vm_host.vm_host import VMLifecycleManager
from ibm_watsonx_orchestrate.cli.config import (Config, PREVIOUS_DOCKER_CONTEXT, DOCKER_CONTEXT)

from ibm_watsonx_orchestrate.utils.environment import EnvService


logger = logging.getLogger(__name__)

DISTRO_NAME = "ibm-watsonx-orchestrate"

from rich.console import Console
console = Console()

def _safe_print(msg: str, style: str = "white"):
    """Print above any active spinner."""
    console = Console()
    console.print("\n" + msg, style=style)

class WSLLifecycleManager(VMLifecycleManager):
    def __init__(self, ensure_installed: bool = True):
        self.keyring_unlocked = False
        _ensure_wsl_installed()

    def start_server(self):
        _ensure_wsl_distro_exists()
        _ensure_wsl_distro_started()
        _ensure_docker_started()

    def stop_server(self):
        logger.info("Stopping WSL Distro...")
        _ensure_wsl_distro_stopped()
        logger.info("WSL Distro stopped.")

    def delete_server(self):
        return _ensure_wsl_distro_deleted()

    def shell(self, command: Union[str, List[str]], capture_output=False, user: str = "orchestrate", **kwags) -> subprocess.CompletedProcess:
        c = _command_to_list(command)
        # Pass the 'user' argument through to wsl_exec
        return wsl_exec(command=c, capture_output=capture_output, user=user, **kwags)
    
    def get_path_in_container(self, path: str) -> str:
        """Convert Windows path (C:\\...) into WSL path (/mnt/c/...)"""
        path = Path(path).expanduser().resolve()
        drive = path.drive.replace(":", "").lower()
        folder = str(path).replace(f"{path.drive}\\", "").replace("\\", "/")
        return f"/mnt/{drive}/{folder}"
    
    def run_docker_command(self, command: Union[str, List[str]], capture_output=False, **kwags) -> subprocess.CompletedProcess:
        if not self.keyring_unlocked:
            self.shell(["gnome-keyring-daemon", "unlock"],capture_output=True, user="orchestrate")
            self.keyring_unlocked = True
        # Docker commands should implicitly run as 'orchestrate'
        # The 'shell' method should handle passing 'user="orchestrate"' to wsl_exec
        # If there's an explicit need to run docker as root, you'd add 'user="root"' to **kwags
        return self.shell(['docker'] + _command_to_list(command), capture_output=capture_output, user="orchestrate", **kwags) # Explicitly set user for docker commands
    
    def edit_server(self, cpus=None, memory=None, disk=None):
        return _edit_wsl_vm(cpus, memory, disk)
    
    def attach_docker_context(self) -> bool:
        return _attach_docker_context_wsl()

    def release_docker_context(self) -> bool:
        return _release_docker_context_wsl()
    
    def get_container_logs(self, container_id, container_name):
        _get_container_logs_wsl(container_id, container_name)

    def ssh(self):
        _ssh_into_wsl()

    def show_current_context(self):
        _get_current_docker_context()
    
    def is_server_running(self):
        _ensure_wsl_installed()  

        state = _get_distro_state()
        if state is None:
            return False
        if state == 'Running':
            return True
        return False
    
    def check_and_ensure_memory_for_doc_processing(self, min_memory_gb: int=24)-> None:
        memory_is_sufficient = _check_and_ensure_wsl_memory_for_doc_processing(min_memory_gb)

        if not memory_is_sufficient:
            # Check if VM exists before trying to edit it
            state = _get_distro_state()
            if state is not None:
                # VM exists, we can edit it
                logger.info(f"Restarting VM to apply new memory allocation ({min_memory_gb}GB)...")
                self.edit_server(memory=min_memory_gb)
            else: 
                logger.info(f"VM will be created with {min_memory_gb}GB memory on first start.")

class WSLConfigLinesManager:
    """Manager for manipulating WSL configuration lines without file I/O."""

    def __init__(self, config_lines: list[str]):
        """Initialize with existing config lines.
        
        Args:
            config_lines: List of configuration lines from .wslconfig file
        """
        self.config_lines = config_lines.copy()  # Make a copy to avoid mutating original

    def set_or_replace(self, key: str, value: str):
        """Set or replace a configuration key, value pair.
        
        Args:
            key: Configuration key (e.g., "memory", "processors")
            value: Configuration value (e.g., "16GB", "8")
        """
        for i, line in enumerate(self.config_lines):
            if line.strip().startswith(f"{key}="):
                self.config_lines[i] = f"{key}={value}"
                return
        self.config_lines.append(f"{key}={value}")

    def get_config_lines(self) -> list[str]:
        """Get the modified configuration lines.
        
        Returns:
            List of configuration lines
        """
        return self.config_lines

def _command_to_list(command: Union[str, List[str]]) -> List[str]:
    if isinstance(command, str):
        return command.split()
    return command

def wsl_exec(command: List[str], capture_output=True, user: str = "orchestrate", check: bool = True, **kwags) -> subprocess.CompletedProcess:
    """
    Executes a command inside the WSL distribution.

    Args:
        command: The command to execute, as a list of strings.
        capture_output: Whether to capture stdout/stderr.
        user: The WSL user to run the command as. Defaults to 'orchestrate'.
        **kwags: Additional arguments to pass to subprocess.run.
    """
    cmd = ['wsl', '-d', VM_NAME, '-u', user, '--'] + command

    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            **kwags
        )
        return result
    except subprocess.CalledProcessError as e:
        # Ctrl+C while streaming logs
        if e.returncode == 130:
            return subprocess.CompletedProcess(args=e.cmd, returncode=130)

        logger.error(f"WSL command failed: {e.cmd}, return code: {e.returncode}")
        if e.stdout:
            logger.error(f"WSL command stdout: {e.stdout.strip()}")
        if e.stderr:
            logger.error(f"WSL command stderr: {e.stderr.strip()}")
        raise

def _ensure_wsl_installed():
    """
    Ensure WSL is installed and functional.
    - If the WSL optional component is missing, automatically install it.
    - Inform the user to reboot if required.
    """
    try:
        # Check WSL status
        subprocess.run(
            ['wsl', '--status'],
            check=True,
            capture_output=True,
            text=True
        )
        # logger.info("WSL is already installed and functional.")
        return True

    except FileNotFoundError:
        logger.warning("WSL executable not found. Attempting installation using 'wsl.exe --install --no-distribution'...")
        try:
            subprocess.run(
                ['wsl.exe', '--install', '--no-distribution'],
                check=True,
                capture_output=False,
                text=True
            )
            logger.info(
                "WSL installation initiated. You must RESTART your computer to complete setup.\n"
                "After reboot, re-run: orchestrate server start -e .env"
            )
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            logger.error(f"Automatic WSL installation failed: {e}")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        # WSL exists but optional component not fully enabled
        stderr = (e.stderr or "").lower()
        if "wsl_e_wsl_optional_component_required" in stderr or e.returncode == 4294967295:
            logger.warning(
                "WSL optional component not fully enabled. Installing missing components..."
            )
            try:
                subprocess.run(
                    ['wsl.exe', '--install', '--no-distribution'],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(
                    "WSL installation updated. REBOOT required to complete setup. After restart, please re-run: orchestrate server start -e .env"
                )
                sys.exit(0)
            except subprocess.CalledProcessError as install_err:
                logger.error(f"Failed to install WSL automatically: {install_err}")
                sys.exit(1)
        else:
            # Any other CalledProcessError
            logger.warning(
                "WSL installation is incomplete or encountered an unexpected error. "
                "Attempting standard installation..."
            )
            try:
                subprocess.run(
                    ['wsl.exe', '--install', '--no-distribution'],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(
                    "WSL installation updated. REBOOT required to complete setup. After restart, re-run: orchestrate server start -e .env"
                )
                sys.exit(0)
            except subprocess.CalledProcessError as install_err:
                logger.error(f"Failed to install WSL automatically: {install_err}")
                sys.exit(1)
    
def _ensure_wsl_distro_exists():
    """Ensure the WSL distro exists, create it if it doesn't."""

    # Ensure WSL itself is installed and functional first
    # Will exit if reboot required
    _ensure_wsl_installed()  

    # Check if distro already exists
    state = _get_distro_state()
    if state is not None:
        logger.info(f"Found existing WSL distro named {VM_NAME} (state={state})")
        return

    logger.info(f"No existing distro found — creating new WSL distro named {VM_NAME}...")

    with tempfile.TemporaryDirectory() as temp_dir:
        ubuntu_appx_path = _download_ubuntu_appx(temp_dir)
        rootfs_path = _extract_ubuntu_appx(ubuntu_appx_path, temp_dir)

        install_dir = os.path.join(os.environ["USERPROFILE"], ".wsl", VM_NAME)
        os.makedirs(install_dir, exist_ok=True)

        try:
            subprocess.run(
                ["wsl", "--import", VM_NAME, install_dir, rootfs_path],
                check=True,
                text=True,
                capture_output=True
            )
            logger.info(f"WSL distro {VM_NAME} created successfully.")
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").lower()
            # Known cases
            if "already exists" in stderr or "error_already_exists" in stderr:
                logger.warning(f"WSL distro {VM_NAME} already exists — skipping import.")
            elif "wsl_e_wsl_optional_component_required" in stderr:
                logger.error(
                    "\n=====================================================================\n"
                    "Cannot import WSL distro because the WSL optional component is not fully enabled.\n"
                    "Please RESTART your computer and re-run:\n"
                    "    orchestrate server start -e .env\n"
                    "=====================================================================\n"
                )
                sys.exit(1)
            else:
                logger.error(f"Failed to import WSL distro {VM_NAME}: {stderr}")
                raise

    _configure_wsl_distro()
    logger.info(f"WSL distro {VM_NAME} is ready and configured.")

def _download_ubuntu_appx(temp_dir):
    ubuntu_url = "https://aka.ms/wslubuntu2204" 
    ubuntu_appx_path = os.path.join(temp_dir, "ubuntu.appx")
    
    subprocess.run(['curl', '-L', '-o', ubuntu_appx_path, ubuntu_url], check=True, capture_output=True)
    
    return ubuntu_appx_path

def _extract_ubuntu_appx(appx_path, temp_dir):
    with zipfile.ZipFile(appx_path, "r") as zf:
        zf.extractall(temp_dir)

    # Search for nested .appx files (x64 preferred)
    candidates = [
        f for f in os.listdir(temp_dir)
        if f.lower().endswith(".appx") and "x64" in f.lower()
    ]
    if not candidates:
        # fallback to any .appx
        candidates = [f for f in os.listdir(temp_dir) if f.lower().endswith(".appx")]

    if not candidates:
        raise FileNotFoundError("No nested .appx packages found inside bundle")

    nested_appx = os.path.join(temp_dir, candidates[0])

    nested_dir = os.path.join(temp_dir, "nested_extracted")
    os.makedirs(nested_dir, exist_ok=True)

    with zipfile.ZipFile(nested_appx, "r") as zf:
        zf.extractall(nested_dir)

    tar_path = os.path.join(nested_dir, "install.tar.gz")
    if not os.path.exists(tar_path):
        raise FileNotFoundError("install.tar.gz not found in nested appx")

    return tar_path

def _ensure_wsl_resources():
    """Ensure the ibm-watsonx-orchestrate distro uses 8 CPUs / 16GB RAM."""
    wslconfig_path = Path(os.environ["USERPROFILE"]) / ".wslconfig"

    # Read existing config
    config_lines = []
    if wslconfig_path.exists():
        config_lines = wslconfig_path.read_text(encoding="utf-8").splitlines()
    
    # Ensure [wsl2] section exists
    if not any(line.strip().lower() == "[wsl2]" for line in config_lines):
        config_lines.insert(0, "[wsl2]")
    
    config_manager: WSLConfigLinesManager = WSLConfigLinesManager(config_lines)

    config_manager.set_or_replace("processors", f"{DEFAULT_CPUS}")
    config_manager.set_or_replace("memory", f"{DEFAULT_MEMORY}GB")
    config_manager.set_or_replace("idleTimeout", "0")


    wslconfig_path.write_text("\n".join(config_manager.get_config_lines()), encoding="utf-8")

def _configure_wsl_distro():
    """
    Configure the WSL distro and install Rootful Docker directly.
    """
    logger.info("Configuring the ibm-watsonx-orchestrate distro...")
    _ensure_wsl_resources()
    _ensure_wsl_idle_timeout_disabled()
    base_dir = Path(__file__).resolve().parent.parent
    user_data_path = base_dir / "resources" / "wsl" / "cloud-init" / "ibm-watsonx-orchestrate.user-data"
    if not user_data_path.exists():
        raise FileNotFoundError(f"user-data file not found: {user_data_path}")

    # Copy cloud-init user-data into WSL nocloud (run as root inside WSL)
    # logger.info("Copying cloud-init user-data into WSL nocloud seed")
    subprocess.run(
        [
            "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
            "mkdir -p /var/lib/cloud/seed/nocloud && cat > /var/lib/cloud/seed/nocloud/user-data"
        ],
        input=user_data_path.read_text(encoding="utf-8"),
        text=True,
        check=True,
    )

    # Create orchestrate user early (as root) 
    subprocess.run(
        [
            "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
            r"""
            set -e
            if ! id -u orchestrate >/dev/null 2>&1; then
                echo "Creating orchestrate user..."
                useradd -m -s /bin/bash orchestrate
                echo 'orchestrate:orchestrate' | chpasswd
            fi
            usermod -aG sudo,docker orchestrate || true
            echo 'orchestrate ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/orchestrate
            chmod 0440 /etc/sudoers.d/orchestrate
            """
        ],
        check=True,
        capture_output=True
    )

    # Direct to Rootful Docker CE with Compose as noticed issues with Rootless docker, dbus gnome etc.
    subprocess.run(
        [
            "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
            r"""
            set -eux
            apt remove -y docker.io || true
            apt update
            
            # Install core dependencies
            DEBIAN_FRONTEND=noninteractive apt install -y \
                ca-certificates curl gnupg lsb-release \
                libsecret-1-0 pkg-config gnome-keyring

            mkdir -p /home/orchestrate/.local/share/keyrings/
            echo "Default_keyring" > /home/orchestrate/.local/share/keyrings/default
            echo "[keyring]\ndisplay-name=Default keyring\nctime=0\nmtime=0\nlock-on-idle=false\nlock-after=false" > /home/orchestrate/.local/share/keyrings/Default_keyring.keyring
            
            chown orchestrate:orchestrate /home/orchestrate/.local/share/keyrings

            
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
              https://download.docker.com/linux/ubuntu \
              $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            apt update
            # Install Docker CE and plugins
            DEBIAN_FRONTEND=noninteractive apt install -y \
                docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

            # Add orchestrate user to docker group if not already done by usermod above
            usermod -aG docker orchestrate || true
            """
        ],
        check=True,
        capture_output=True
    )

    try:
        # Ensure .docker directory exists and log its state
        result = subprocess.run(
            [
                "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
                "sudo -u orchestrate mkdir -p /home/orchestrate/.docker && ls -ld /home/orchestrate/.docker"
            ],
            check=True,
            capture_output=True, 
            text=True
        )

        # Write the config.json content and verify
        subprocess.run(
            [
                "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
                "echo '{\"credsStore\": \"\"}' | sudo -u orchestrate tee /home/orchestrate/.docker/config.json > /dev/null"
            ],
            check=True,
            capture_output=True
        )

        # Set permissions (chmod 600) and verify
        result = subprocess.run(
            [
                "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
                "chmod 600 /home/orchestrate/.docker/config.json && ls -l /home/orchestrate/.docker/config.json"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        # Set ownership (chown orchestrate:orchestrate) and verify
        result = subprocess.run(
            [
                "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
                "chown orchestrate:orchestrate /home/orchestrate/.docker/config.json && ls -l /home/orchestrate/.docker/config.json"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        # Verify the content of config.json
        result = subprocess.run(
            [
                "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
                "sudo -u orchestrate cat /home/orchestrate/.docker/config.json"
            ],
            check=True,
            capture_output=True,
            text=True
        )
        
    except subprocess.CalledProcessError as e:
        logger.error(f"WSL: Failed to configure Docker config.json. Command: {e.cmd}, Return Code: {e.returncode}")
        logger.error(f"WSL: Stderr: {e.stderr}")
        raise 

def _ensure_wsl_idle_timeout_disabled():
    """Ensure WSL idleTimeout=0 is set in .wslconfig (prevents auto-shutdown)."""
    wslconfig_path = Path.home() / ".wslconfig"
    lines = []

    if wslconfig_path.exists():
        with open(wslconfig_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Remove old [wsl2] blocks if needed
    cleaned = []
    in_wsl2_block = False
    for line in lines:
        if line.strip().lower().startswith("[wsl2]"):
            in_wsl2_block = True
            continue
        if in_wsl2_block and line.strip().startswith("["):
            in_wsl2_block = False
        if not in_wsl2_block:
            cleaned.append(line)

    new_block = [
        "[wsl2]\n",
        "idleTimeout=0\n",
        "networkingMode=mirrored\n",
        "\n"
    ]
    cleaned.extend(new_block)

    with open(wslconfig_path, "w", encoding="utf-8") as f:
        f.writelines(cleaned)

def _ensure_wsl_distro_started():
    """Ensure the WSL distro is started"""
    state = _get_distro_state()
    if state is None:
        return
    
    if state != 'Running':
        subprocess.run(['wsl', '-d', VM_NAME, '--', 'echo', 'Starting WSL distro'], check=True)
    
    state = _get_distro_state()
    if state != 'Running':
        raise Exception(f"Could not start WSL distro {VM_NAME}")


def _ensure_wsl_distro_stopped():
    """Ensure the WSL distro is stopped"""
    state = _get_distro_state()
    if state is None:
        return
    
    if state != 'Stopped':
        subprocess.run(['wsl', '--terminate', VM_NAME], check=True)
    
    state = _get_distro_state()
    if state != 'Stopped' and state is not None:
        raise Exception(f"Could not stop WSL distro {VM_NAME}")
    
def _ensure_wsl_distro_deleted() -> bool:
    """Delete the WSL distro and all associated volumes and resources."""
    _ensure_wsl_distro_stopped()

    try:
        # Check if the distro exists
        result = subprocess.run(
            ["wsl", "--list", "--quiet"],
            capture_output=True,
            check=True
        )

        # Decode using UTF-16 if stdout is bytes
        stdout = result.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-16").strip()

        # Clean up and extract distro names
        distros = [line.strip() for line in stdout.splitlines() if line.strip()]
        if DISTRO_NAME not in distros:
            # logger.error(f"WSL distribution '{DISTRO_NAME}' not found.")
            _safe_print(f"[red][ERROR][/red] - WSL distribution '{DISTRO_NAME}' not found. Nothing to purge.")
            return False

        # Delete the distro
        subprocess.run(["wsl", "--unregister", VM_NAME], check=True)

        # Clean up any lingering WSL data
        # Normally WSL --unregister removes it, but some leftover files may persist in %LOCALAPPDATA%\Packages
        possible_paths = [
            Path.home() / "AppData" / "Local" / "Packages",
            Path.home() / "AppData" / "Local" / "lxss" / VM_NAME
        ]

        for path in possible_paths:
            if path.exists() and VM_NAME.lower() in str(path).lower():
                try:
                    logger.info(f"Cleaning leftover WSL data at: {path}")
                    shutil.rmtree(path)
                except Exception as e:
                    logger.warning(f"Failed to remove leftover path {path}: {e}")

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to delete WSL distro {VM_NAME}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting WSL distro {VM_NAME}: {e}")
        return False
    
def _ensure_docker_started():
    subprocess.run(
        [
            "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
            r"""
            # Start Docker daemon
            if ! pgrep -x dockerd >/dev/null 2>&1; then
                nohup dockerd --host=unix:///var/run/docker.sock --host=tcp://0.0.0.0:2375 > /tmp/dockerd.log 2>&1 &
                sleep 15
            fi
            """
        ],
        check=True,
        capture_output=True
    )

def _get_distro_state():
    """Return the current state ('Running', 'Stopped', etc.) of the WSL distro, or None if not found."""
    try:
        result = subprocess.run(
            ['wsl', '-l', '-v'],
            capture_output=True,
            text=False,
            check=False
        )

        # Try to decode properly
        try:
            output = result.stdout.decode("utf-8", errors="ignore")
            if "\x00" in output:
                output = result.stdout.decode("utf-16", errors="ignore")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decoding failed, falling back to UTF-16.")
            output = result.stdout.decode("utf-16", errors="ignore")

        output = output.strip()

        lines = [line.strip() for line in output.splitlines() if line.strip()]

        if len(lines) <= 1:
            logger.warning("No WSL distros found (only header or empty output).")
            return None

        # Regex for parsing each line
        distro_pattern = re.compile(
            r"^\*?\s*(?P<name>[A-Za-z0-9._\- ]+)\s+(?P<state>Stopped|Running|Starting|Stopping|Updating|Uninstalling)\s+(?P<version>\d+)$",
            re.IGNORECASE
        )

        for i, line in enumerate(lines):
            if i == 0:
                continue

            match = distro_pattern.match(line)
            if match:
                name = match.group("name").strip()
                state = match.group("state").strip()

                if VM_NAME.lower() == name.lower():
                    return state
            else:
                pass

        return None

    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Unexpected error while getting WSL distro state: {e}")
        logger.exception("An unexpected error occurred in _get_distro_state:")
        return None

def _ensure_docker_started():
    subprocess.run(
        [
            "wsl", "-d", VM_NAME, "-u", "root", "--", "sh", "-c",
            r"""
            # Start Docker daemon
            if ! pgrep -x dockerd >/dev/null 2>&1; then
                nohup dockerd --host=unix:///var/run/docker.sock --host=tcp://0.0.0.0:2375 > /tmp/dockerd.log 2>&1 &
                sleep 15
            fi
            """
        ],
        check=True,
        capture_output=True
    )

def _edit_wsl_vm(cpus=None, memory=None, disk=None, distro_name="ibm-watsonx-orchestrate") -> bool:
    """
    Edit WSL VM settings (CPU, memory, disk) by modifying ~/.wslconfig,
    restart WSL, and ensure Docker listens on TCP 2375 and UNIX socket.
    Containers and data remain intact.
    """
    try:
        default_env_path = EnvService.get_default_env_file()
        merged_env_dict = EnvService.merge_env(default_env_path, None)
        health_user = merged_env_dict.get("WXO_USER")
        health_pass = merged_env_dict.get("WXO_PASS")

        was_server_running = EnvService._check_dev_edition_server_health(username=health_user, password=health_pass)

        wslconfig_path = Path(os.environ["USERPROFILE"]) / ".wslconfig"
        
        # Read existing config
        config_lines = []
        if wslconfig_path.exists():
            config_lines = wslconfig_path.read_text(encoding="utf-8").splitlines()

        # Ensure [wsl2] section exists
        if not any(line.strip().lower() == "[wsl2]" for line in config_lines):
            config_lines.insert(0, "[wsl2]")
        
        config_manager: WSLConfigLinesManager = WSLConfigLinesManager(config_lines)
        
        if cpus:
            config_manager.set_or_replace("processors", f"{cpus}")
        if memory:
            memory_value = f"{memory}GB" if str(memory).isdigit() else str(memory)
            config_manager.set_or_replace("memory", f"{memory_value}")

        wslconfig_path.write_text("\n".join(config_manager.get_config_lines()) + "\n", encoding="utf-8")

        logger.info("Restarting WSL for configuration changes to take effect...")
        subprocess.run(["wsl", "--terminate", distro_name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["wsl", "--shutdown"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

        # Start distro
        logger.info(f"Starting WSL distro '{distro_name}'...")
        subprocess.run(["wsl", "-d", distro_name, "--", "true"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        # Ensure Docker config allows TCP
        docker_config_cmd = """set -e
mkdir -p /etc/docker
cat <<'EOF' > /etc/docker/daemon.json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
EOF
"""
        subprocess.run(
            ["wsl", "-d", distro_name, "-u", "root", "--", "bash", "-c", docker_config_cmd],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Start Docker daemon if not running
        logger.info("Starting Docker daemon manually...")
        start_docker_cmd = (
            "set -e;"
            "if ! pgrep dockerd >/dev/null 2>&1; then "
            "  nohup dockerd > /tmp/dockerd.log 2>&1 & "
            "  sleep 5;"
            "fi;"
            "docker version >/dev/null 2>&1 || true"
        )
        subprocess.run(
            ["wsl", "-d", distro_name, "-u", "root", "--", "bash", "-c", start_docker_cmd],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Wait for Docker to become responsive
        logger.info("Waiting for Docker to become responsive...")
        while True:
            result = subprocess.run(
                ["wsl", "-d", distro_name, "--", "docker", "info"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                logger.info("Docker is running and responsive.")
                break
            time.sleep(2)

        # Keep distro alive quietly
        subprocess.Popen(
            ["wsl", "-d", distro_name, "--", "bash", "-c", "while true; do sleep 60; done"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        logger.info("WSL distro kept running in background.")

        logger.info("WSL VM configuration and Docker restart completed successfully.")

        if was_server_running:
            logger.info("Waiting for API to be reachable...")
            health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else 120
            server_is_started = EnvService._wait_for_dev_edition_server_health_check(health_user, health_pass, timeout_seconds=health_check_timeout)

            if server_is_started:
                logger.info("WSL VM editted and server restarted successfully.")
            else:
                logger.error("WSL VM editted but server failed to start successfully within the expected timeframe. To start the server 'orchestrate server start'.")
        else:
            logger.info("WSL VM editted. To start the server 'orchestrate server start'.")

        logger.info("API reachable.")
        return True

    except Exception as e:
        logger.error(f"Failed to edit WSL VM settings: {e}")
        return False

def _get_current_docker_context():
    result = subprocess.run(
        ["docker", "context", "show"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def _attach_docker_context_wsl() -> bool:
    DOCKER_HOST_TCP = f"tcp://localhost:2375"

    # Get current docker context
    result = subprocess.run(["docker", "context", "show"], capture_output=True, text=True)
    if result.returncode != 0:
        current_context = "default"
    else:
        current_context = result.stdout.strip()

    cfg = Config()
    if current_context != "ibm-watsonx-orchestrate":
            cfg.write(DOCKER_CONTEXT, PREVIOUS_DOCKER_CONTEXT, str(current_context))

    if shutil.which("docker") is None:
        logger.error(
            "\n=====================================================================\n"
            "Docker CLI not found on your system.\n\n"
            "This command requires Docker to be installed and available in your PATH.\n\n"
            "Please install Docker Desktop or Docker Engine, then re-run:\n"
            "       orchestrate server attach-docker\n"
            "=====================================================================\n"
        )
        sys.exit(1)

    try:
        logger.info(f"Attaching Docker context to {VM_NAME} via UNIX socket...")

        # Remove existing context if exists
        subprocess.run(
            ["docker", "context", "rm", "-f", VM_NAME],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Create new context pointing to the WSL Docker socket
        subprocess.run(
            ["docker", "context", "create", VM_NAME, "--docker", f"host={DOCKER_HOST_TCP}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        subprocess.run(
            ["docker", "context", "use", VM_NAME],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        logger.info(f"Docker context switched to {VM_NAME}")

        # Verify connection quietly
        result = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return True
        else:
            logger.error(f"Docker context verification failed: {result.stderr.strip()}")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed during attach-docker: {e}")
        return False

    except FileNotFoundError:
        logger.error(
            "\n=====================================================================\n"
            "Docker command not found.\n\n"
            "Please ensure Docker is installed and accessible in your PATH.\n"
            "If you have Docker Desktop installed, make sure it's running.\n"
            "=====================================================================\n"
        )
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Unexpected error attaching Docker context: {e}")
        return False

def _release_docker_context_wsl() -> bool:
    """
    Switch Docker context back to the default on WSL.
    This actually changes the active Docker context, not just printing.
    """
    cfg = Config()
    previous_context = cfg.read(DOCKER_CONTEXT, PREVIOUS_DOCKER_CONTEXT)

    if previous_context is None:
        previous_context = 'default'

    try:
        # Unset DOCKER_HOST in case it overrides the context
        os.environ.pop("DOCKER_HOST", None)

        # Switch context
        result = subprocess.run(
            ["docker", "context", "use", previous_context],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Failed to switch Docker context back to '{previous_context}'.")
            return False
        return True

    except Exception as e:
        logger.error(f"Unexpected error while releasing Docker context: {e}")
        return False

def _get_container_logs_wsl(container_id: str = None, container_name: str = None):
    """
    Fetch logs for a Docker container by its ID or name (inside WSL).
    At least one of container_id or container_name must be provided.
    """

    target = container_id or container_name

    try:
        result = subprocess.run(
            ["docker", "logs", target],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"ERROR: Failed to get logs for container '{target}': {e.stderr}", file=sys.stderr)
        return False

    except FileNotFoundError:
        logger.error(
            "ERROR: Docker command not found. Ensure Docker Desktop is running and accessible from WSL.",
            file=sys.stderr
        )
        return False

    except Exception as e:
        logger.error(f"ERROR: Unexpected error getting container logs (WSL): {e}", file=sys.stderr)
        return False
    


def _ssh_into_wsl():
    """
    Open an interactive shell into the underlying ibm-watsonx-orchestrate WSL distribution.
    """
    try:
        # Run 'wsl --list --quiet' and decode as UTF-16
        result = subprocess.run(
            ["wsl", "--list", "--quiet"],
            capture_output=True,
            check=True
        )

        # Decode using UTF-16 if stdout is bytes
        stdout = result.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-16").strip()

        # Clean up and extract distro names
        distros = [line.strip() for line in stdout.splitlines() if line.strip()]
        if DISTRO_NAME not in distros:
            logger.error(f"ERROR: WSL distribution '{DISTRO_NAME}' not found. Available: {distros}")
            return False

        logger.info(f"Opening shell into WSL distribution '{DISTRO_NAME}'...")
        
        user = os.environ.get("WXO_SSH_USER", "orchestrate")

        # Attach user to WSL shell interactively
        subprocess.run(
            ["wsl", "-d", DISTRO_NAME, "-u", user],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        # Exit code 0 = normal, 130 = user exited or Ctrl+C
        if result.returncode in (0, 130):
            return True

    except subprocess.CalledProcessError as e:
        logger.error(f"ERROR: Failed to SSH into WSL distro '{DISTRO_NAME}': {e}")
        return False

    except FileNotFoundError:
        logger.error("ERROR: 'wsl' command not found. Ensure you are on Windows with WSL installed.")
        return False

    except Exception as e:
        logger.error(f"ERROR: Unexpected error while connecting to WSL: {e}")
        return False
    
def _check_and_ensure_wsl_memory_for_doc_processing(min_memory_gb: int=24) -> bool:
    """Check if the WSL distro has enough memory for document processing.  """
    
    wslconfig_path = Path(os.environ["USERPROFILE"]) / ".wslconfig"
    
    # Read existing config
    config_lines = []
    current_memory_gb = None
    
    if wslconfig_path.exists():
        config_lines = wslconfig_path.read_text(encoding="utf-8").splitlines()
        
        # Find current memory setting
        for line in config_lines:
            if line.strip().startswith("memory="):
                memory_value = line.split("=", 1)[1].strip()
                
                # Parse memory value (supports "16GB", "16384MB", or just "16")
                if memory_value.upper().endswith("GB"):
                    current_memory_gb = int(re.sub(r'[^\d]', '', memory_value))
                elif memory_value.upper().endswith("MB"):
                    current_memory_gb = int(re.sub(r'[^\d]', '', memory_value)) // 1024
                elif memory_value.isdigit():
                    current_memory_gb = int(memory_value)
                break
    
    # If no memory setting found, assume default (16GB)
    if current_memory_gb is None:
        current_memory_gb = DEFAULT_MEMORY
    
    # Check if memory is sufficient
    if current_memory_gb >= min_memory_gb:
        return True
    else:
        # Memory is insufficient - warn and increase
        logger.warning(
            f"\n{'='*70}\n"
            f"MEMORY REQUIREMENT WARNING\n"
            f"{'='*70}\n"
            f"Document Processing requires at least {min_memory_gb}GB of memory.\n"
            f"Current WSL memory allocation: {current_memory_gb}GB\n"
            f"\n"
            f"Automatically increasing memory to {min_memory_gb}GB...\n"
            f"{'='*70}\n"
        )
    # Ensure [wsl2] section exists
    if not any(line.strip().lower() == "[wsl2]" for line in config_lines):
        config_lines.insert(0, "[wsl2]")
    
    config_manager: WSLConfigLinesManager = WSLConfigLinesManager(config_lines)
    config_manager.set_or_replace("memory", f"{min_memory_gb}GB")
    
    # Write back all config lines (preserves everything else)
    wslconfig_path.write_text("\n".join(config_manager.get_config_lines()), encoding="utf-8")
    
    logger.info(f"Updated {wslconfig_path} with memory={min_memory_gb}GB")

    return False
    

