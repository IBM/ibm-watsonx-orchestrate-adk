import json
import shutil
import subprocess
from importlib.resources import files
from typing import List, Optional
import os
import logging
import shutil
from pathlib import Path
import yaml
import sys
import requests
import time
import getpass

from ibm_watsonx_orchestrate.cli.config import (Config, PREVIOUS_DOCKER_CONTEXT, DOCKER_CONTEXT)

from ibm_watsonx_orchestrate.client.utils import get_linux_package_manager
from ibm_watsonx_orchestrate.developer_edition.vm_host.constants import VM_NAME, CPU_ARCH_ARM, DEFAULT_DISK_SPACE, \
    DEFAULT_CPUS, DEFAULT_MEMORY

from ibm_watsonx_orchestrate.developer_edition.vm_host.vm_host import VMLifecycleManager
from ibm_watsonx_orchestrate.utils.environment import EnvService

logger = logging.getLogger(__name__)

DEFAULT_LIMA_VERSION = "v1.2.1"

class LimaLifecycleManager(VMLifecycleManager):
    def __init__(self, ensure_installed: bool = True):
        if ensure_installed:
            _ensure_lima_installed()

    def start_server(self):
        _ensure_lima_vm_host_exists()
        _ensure_lima_vm_started()

    def stop_server(self):
        logger.info("Stopping Lima VM...")
        _ensure_lima_vm_stopped()
        logger.info("Lima VM stopped.")

    def delete_server(self):
        return _ensure_lima_vm_host_deleted()

    def shell(self, command: str | List[str], capture_output=True):
        c = ['shell', 'ibm-watsonx-orchestrate'] + _command_to_list(command)
        return limactl(command=c, capture_output=capture_output)

    def get_path_in_container(self, path: str) -> str:
        return path

    def run_docker_command(
        self,
        command: str | list,
        capture_output: bool = False,
        input: str | None = None,
        env: dict | None = None, 
        **kwargs
    ) -> subprocess.CompletedProcess:
        """
        Run a Docker command inside the Lima VM.
        """
        command_list = ["docker"] + _command_to_list(command)
        limactl_path = (
            files("ibm_watsonx_orchestrate.developer_edition.resources.lima.bin")
            / "limactl"
        )
        return subprocess.run(
            [str(limactl_path), "shell", "ibm-watsonx-orchestrate", "--"] + command_list,
            capture_output=capture_output,
            text=True,
            input=input,
            env=env,
            **kwargs
        )
        
    def edit_server(self, cpus=None, memory=None, disk=None):
        return _edit_lima_vm(cpus, memory, disk)

    def show_current_context(self):
        _get_current_docker_context()

    def attach_docker_context(self):
        return _attach_docker_context_lima()

    def release_docker_context(self):
        return _release_docker_context_lima()

    def get_container_logs(self, container_id, container_name):
        _get_container_logs(container_id, container_name)
    
    def ssh(self):
        return _ssh_into_lima()
    
    def is_server_running(self):
        _ensure_lima_installed()
        
        vm = _get_vm_state()
        if vm is None:
            logger.info('Could not find VM named ' + VM_NAME)
            return False
        status = vm['status']
        if status == 'Running':
            return True
        return False

    def check_and_ensure_memory_for_doc_processing(self, min_memory_gb: int=24)-> None:
        memory_is_sufficient = _check_and_ensure_lima_memory_for_doc_processing(min_memory_gb)

        if not memory_is_sufficient :
            vm = _get_vm_state()
            if vm is not None:
                # VM exists, we can edit it
                logger.info(f"Restarting VM to apply new memory allocation ({min_memory_gb}GB)...")
                self.edit_server(memory=min_memory_gb)
            else:
                # VM doesn't exist yet, config will be used on creation
                logger.info(f"VM will be created with {min_memory_gb}GB memory on first start.")

def _command_to_list(command: str | list) -> list:
    return [e.strip() for e in command.split(' ') if e.strip() != ''] if isinstance(command, str) else command

def limactl(command: List[str], capture_output=True) -> Optional[str]:
    limactl_path = files(
        'ibm_watsonx_orchestrate.developer_edition.resources.lima.bin'
    ) / 'limactl'

    try:
        out = subprocess.run(
            [str(limactl_path)] + command,
            check=True,
            capture_output=capture_output,
            text=True
        )

        if capture_output:
            return out.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"An error occured while executing the command: {[str(limactl_path)] + command}")
        if "--debug" in sys.argv:
            logger.error(f"RETURN CODE: {e.returncode}")
            logger.error(f"STDERR: {e.stderr}")
            raise e
        sys.exit(1)
    return None

def _get_unix_os():
    return subprocess.run(['uname', '-s'], text=True, check=True, capture_output=True).stdout.strip()

def _get_unix_arm_capability():
    try:
        return subprocess.run(['sysctl', '-n', 'hw.optional.arm64'], text=True, check=True, capture_output=True).stdout.strip() == "1"
    except:
        return False

def _get_unix_cpu_arch(ignore_emulation: bool = True) -> str:
    arch = subprocess.run(['uname', '-m'], text=True, check=True, capture_output=True).stdout.strip()
    os = _get_unix_os()

    # Check for Rosetta Emulation
    if ignore_emulation and arch == 'x86_64' and os == 'Darwin' and _get_unix_arm_capability():
        return "arm64"
    return arch

def _get_lima_vm_base_args() -> List[str]:
    os = _get_unix_os()
    cpu_arch = _get_unix_cpu_arch()

    vm_type = 'qemu'
    rosetta_enabled = False
    cpu_type = 'x86_64'

    if os == 'Darwin':
        vm_type = 'vz'
        if cpu_arch == CPU_ARCH_ARM:
            rosetta_enabled = True
            cpu_type = 'aarch64'

    args = [
        '--name', VM_NAME,
        '--vm-type', vm_type,
        '--arch', cpu_type,
        '--cpus', str(DEFAULT_CPUS),
        '--memory', str(DEFAULT_MEMORY),
        '--disk', str(DEFAULT_DISK_SPACE)
    ]
    if rosetta_enabled:
        args += ['--rosetta']

    if os.lower() == "linux":
        args += ['--mount-type', 'reverse-sshfs' ]

    return args

# Linux Related
def _ensure_kvm_group(user: str):
    """Ensure the user has access to /dev/kvm by adding to the kvm group."""
    if not os.path.exists("/dev/kvm"):
        logger.warning("/dev/kvm not found. Skipping kvm group configuration.")
        return

    try:
        groups = subprocess.run(['groups', user], capture_output=True, text=True, check=True).stdout
        if "kvm" in groups:
            logger.info(f"User '{user}' already in kvm group.")
            return

        logger.info(f"Adding user '{user}' to kvm group...")
        subprocess.run(['sudo', 'usermod', '-aG', 'kvm', user], check=True)
        logger.info(f"User '{user}' added to kvm group. Log out and back in for changes to take effect.")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to add user '{user}' to kvm group: {e}")

# Linux Related
def _ensure_qemu_installed():
    """Ensure QEMU with 9p support is installed and accessible for Lima on RHEL 9."""

    # Step 1: Check if qemu-system-x86_64 is already in PATH
    qemu_exec = shutil.which("qemu-system-x86_64")
    if qemu_exec:
        logger.info(f"QEMU already found at {qemu_exec}")
        # Add a check here to ensure existing QEMU has 9p support
        try:
            output = subprocess.check_output([qemu_exec, "-device", "virtio-9p-pci,help"], text=True, stderr=subprocess.STDOUT)
            if "virtio-9p-pci" in output:
                logger.info("Existing QEMU has 9p (virtio) support, ready for Lima.")
                return # Exit if already found and has support
            else:
                logger.warning("Existing QEMU found, but 9p (virtio) support not detected. Attempting to install missing components.")
        except subprocess.CalledProcessError:
            logger.warning("Existing QEMU found, but unable to check virtio-9p support. Attempting to install missing components.")


    logger.info("QEMU not found or missing 9p support. Attempting to install/update packages...")

    # Install required packages, INCLUDING virtiofsd
    try:
        package_manager = get_linux_package_manager()
        subprocess.run(
            ["sudo", package_manager , "install", "-y", "qemu-kvm", "qemu-img", "libvirt-daemon-driver-qemu", "virtiofsd"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"QEMU packages (including virtio-fs) installed via {package_manager}.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install QEMU packages: {e.stderr}")
        return # Return early on failure

    # Detect actual binary location (RHEL 9 puts it in /usr/libexec/qemu-kvm)
    real_qemu = shutil.which("qemu-kvm")

    if not real_qemu:
        logger.error("Could not find QEMU binary after installation. Please install manually.")
        return

    logger.info(f"Detected QEMU binary at {real_qemu}")

    # Ensure symlink exists
    symlink_path = "/usr/local/bin/qemu-system-x86_64"
    if not shutil.which("qemu-system-x86_64"): # Check if the symlink target is in PATH
        try:
            subprocess.run(
                ["sudo", "ln", "-sf", real_qemu, symlink_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info(f"Created symlink: {symlink_path} -> {real_qemu}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create symlink: {e.stderr}")
            return
    else:
        # If it was already in PATH from previous run, ensure it's the correct real_qemu
        current_qemu_in_path = shutil.which("qemu-system-x86_64")
        if current_qemu_in_path != symlink_path and current_qemu_in_path != real_qemu:
            logger.warning(f"QEMU in PATH ({current_qemu_in_path}) is not the expected symlink target ({symlink_path}) or real binary ({real_qemu}). This might cause issues.")

    # Verify virtio-9p support again after potential installation/update
    qemu_check_path = shutil.which("qemu-system-x86_64") 
    if not qemu_check_path:
        logger.error("QEMU binary not accessible for final 9p support check.")
        return
    try:
        output = subprocess.check_output([qemu_check_path, "-device", "virtio-9p-pci,help"], text=True, stderr=subprocess.STDOUT)
        if "virtio-9p-pci" in output:
            logger.info("QEMU now has 9p (virtio) support, ready for Lima.")
        else:
            logger.error("ERROR: QEMU installed, but 9p (virtio) support still NOT detected. Lima will likely fail.")
    except subprocess.CalledProcessError:
        logger.error("ERROR: Unable to check virtio-9p support after installation. Lima may still fail.")

    # Final PATH check
    qemu_exec = shutil.which("qemu-system-x86_64")
    if qemu_exec:
        logger.info(f"QEMU is now accessible at {qemu_exec}")
    else:
        logger.error("QEMU still not found in PATH after symlink creation.")

def _ensure_lima_installed(version=DEFAULT_LIMA_VERSION):
    lima_folder = files("ibm_watsonx_orchestrate.developer_edition.resources") / "lima"
    bin_dir = os.path.join(lima_folder, 'bin')
    share_dir = os.path.join(lima_folder, 'share')
    limactl_path = os.path.join(bin_dir, 'limactl')

    # Check if Lima is already installed
    if os.path.exists(limactl_path):
        try:
            existing_version = subprocess.run(
                [limactl_path, '-v'],
                check=True,
                text=True,
                capture_output=True
            ).stdout.strip()
            existing_version = f"v{existing_version.split(' ')[-1]}"

            if version is None or existing_version == version:
                return
        except Exception as e:
            logger.warning(f"Error checking existing Lima version: {e}")

    # Get latest version if not provided
    if version is None:
        try:
            version_output = subprocess.run(
                ['curl', '-fsSL', 'https://api.github.com/repos/lima-vm/lima/releases/latest'],
                check=True,
                capture_output=True,
                text=True
            )
            version = json.loads(version_output.stdout).get('tag_name', None)
            logger.info(f"Latest Lima version detected: {version}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch latest Lima version: {e}")
            sys.exit(1)

    # Clean up old installations
    for subdir in ['bin', 'share']:
        path_to_remove = os.path.join(lima_folder, subdir)
        if os.path.exists(path_to_remove):
            try:
                shutil.rmtree(path_to_remove)
            except Exception as e:
                logger.error(f"Failed to remove {path_to_remove}: {e}")
                sys.exit(1)

    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(share_dir, exist_ok=True)

    os_name = _get_unix_os()
    cpu_arch = _get_unix_cpu_arch()

    # Handle Linux-specific dependencies (QEMU + KVM group)
    if os_name.lower() == "linux":
        current_user = getpass.getuser()

        # Prevent running as root — Lima doesn't support root
        if current_user == "root":
            logger.error("Lima cannot be run as the root user. Please switch to a non-root user.")
            sys.exit(1)

        _ensure_qemu_installed()
        _ensure_kvm_group(user=current_user)

    tar_name = f"lima-{version[1:]}-{os_name}-{cpu_arch}.tar.gz"
    url = f"https://github.com/lima-vm/lima/releases/download/{version}/{tar_name}"

    logger.info(f"Downloading Lima from {url}")
    try:
        subprocess.run(
            ['sh', '-c', f'curl -fsSL "{url}" | tar Cxzvm "{lima_folder}"'],
            check=True,
            capture_output=True
        )
        logger.info(f"Lima {version} installed successfully to {lima_folder}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download or extract Lima: {e}")
        sys.exit(1)

    lima_folder = files("ibm_watsonx_orchestrate.developer_edition.resources") / "lima"
    limactl_path = os.path.join(lima_folder, 'bin', 'limactl')

    # Check if limactl already exists and get version
    if os.path.exists(limactl_path):
        try:
            existing_version = subprocess.run(
                [limactl_path, '-v'],
                check=True,
                text=True,
                capture_output=True
            ).stdout.strip()
            existing_version = f"v{existing_version.split(' ')[-1]}"

            if version is None or existing_version == version:
                return 
        except Exception as e:
            logger.error(f"Error checking existing Lima version: {e}")
            sys.exit(1)

    # Fetch latest version if not provided
    if version is None:
        try:
            version_output = subprocess.run(
                ['curl', '-fsSL', 'https://api.github.com/repos/lima-vm/lima/releases/latest'],
                check=True,
                capture_output=True,
                text=True
            )
            version = json.loads(version_output.stdout).get('tag_name', None)
        except subprocess.CalledProcessError as e:
            raise

    # Remove old Lima directories if they exist
    for subdir in ['bin', 'share']:
        path_to_remove = os.path.join(lima_folder, subdir)
        if os.path.exists(path_to_remove):
            try:
                shutil.rmtree(path_to_remove)
            except Exception:
                logger.error(f"Failed to remove {path_to_remove}")
                sys.exit(1)

    url = f"https://github.com/lima-vm/lima/releases/download/{version}/lima-{version[1:]}-{os_name}-{cpu_arch}.tar.gz"
    subprocess.run(
        ['sh', '-c', f'curl -fsSL "{url}" | tar Cxzvm "{lima_folder}"'],
        check=True
    )

def _ensure_lima_vm_host_exists():
    output = limactl(['list', '--format', 'json'])
    lines = [l for l in output.split('\n') if l.strip()]
    existing_vms = [json.loads(l) for l in lines]
    existing_orchestrate_vm = next(filter(lambda x: x['name'] == VM_NAME, existing_vms), None)
    if existing_orchestrate_vm is not None:
        logger.info('Found existing VM named ' + VM_NAME)
        return

    template_path = files("ibm_watsonx_orchestrate.developer_edition.resources.lima.templates") / "docker.template.yaml"
    vm_args = ['create'] + _get_lima_vm_base_args() + [
        '--containerd', 'none',
        str(template_path)
    ]

    limactl(vm_args, capture_output=True)

def _ensure_lima_vm_host_deleted() -> bool:
    """Delete the Lima VM and associated local resources."""
    try:
        _ensure_lima_vm_stopped()
    except ModuleNotFoundError as e:
        logger.warning(f"Skipping stopping VM because Lima binary is missing: {e}")

    # Delete the VM if possible
    try:
        output = limactl(['list', '--format', 'json'])
        existing_vms = [json.loads(l) for l in output.split('\n') if l.strip()]
        existing_orchestrate_vm = next((x for x in existing_vms if x['name'] == VM_NAME), None)

        if existing_orchestrate_vm is None:
            logger.warning(f"Could not find existing VM named {VM_NAME}")
        else:
            limactl(['delete', VM_NAME], capture_output=True)

    except ModuleNotFoundError:
        return True
    except Exception as e:
        return True

    # Delete additional local resources
    base_path = Path(__file__).parent.parent / "resources" / "lima"
    for sub in ["bin", "share"]:
        path = base_path / sub
        if path.exists():
            try:
                shutil.rmtree(path)
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
        else:
            logger.debug(f"Resource path {path} does not exist — skipping")

    return True

def _get_vm_state():
    existing_vms = list(map(lambda l: json.loads(l), limactl(['list', '--format', 'json']).split('\n')))
    return next(filter(lambda x: x['name'] == VM_NAME, existing_vms), None)

def _ensure_lima_vm_started():
    vm = _get_vm_state()
    if vm is None:
        logger.info('Could not find VM named ' + VM_NAME)
        return
    status = vm['status']
    if status == 'Stopped':
        logger.info('VM is not running, starting...')
        limactl(['start', '--name', VM_NAME], capture_output=True)
    vm = _get_vm_state()
    if vm['status'] != 'Running':
        raise Exception(f"Could not start lima VM {VM_NAME}")

def _ensure_lima_vm_stopped():
    try:
        vm = _get_vm_state()
        if vm is None:
            logger.info(f"No VM named {VM_NAME} found — skipping stop.")
            return

        status = vm['status']
        if status != 'Stopped':
            try:
                limactl(['stop', VM_NAME], capture_output=True)
            except FileNotFoundError:
                return
            except Exception as e:
                logger.error(f"Failed to stop VM {VM_NAME}: {e}")
                return

        vm = _get_vm_state()
        if vm and vm['status'] != 'Stopped':
            logger.error(f"VM {VM_NAME} did not stop successfully.")
    except ModuleNotFoundError as e:
        return
    
def _edit_lima_vm(cpus=None, memory=None, disk=None) -> bool:
    default_env_path = EnvService.get_default_env_file()
    merged_env_dict = EnvService.merge_env(default_env_path, None)
    health_user = merged_env_dict.get("WXO_USER")
    health_pass = merged_env_dict.get("WXO_PASS")

    was_server_running = EnvService._check_dev_edition_server_health(username=health_user, password=health_pass)

    """Edit Lima VM config file directly to update resources."""
    logger.info("Stopping Lima VM...")
    _ensure_lima_vm_stopped()
    logger.info("Lima VM stopped.")

    vm_dir = Path.home() / ".lima" / VM_NAME
    config_path = vm_dir / "lima.yaml"

    if not config_path.exists():
        logger.error(f"Could not find {config_path}")
        return

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        logger.info("Editing Lima VM...")

        # Update CPU, memory, and disk
        if cpus:
            config["cpus"] = int(cpus)
        if memory:
            config["memory"] = f"{memory}GiB"
        if disk:
            config["disk"] = f"{disk}GiB"

        with open(config_path, "w") as f:
            yaml.dump(config, f)

    except Exception as e:
        logger.error(f"Failed to update {config_path}: {e}")
        return False

    # Restart VM
    limactl(["start", VM_NAME], capture_output=True)

   
    if was_server_running:
        health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else 120
        server_is_started = EnvService._wait_for_dev_edition_server_health_check(health_user, health_pass, timeout_seconds=health_check_timeout)

        if server_is_started:
            logger.info("Lima VM editted and server restarted successfully.")
        else:
            logger.error("Lima VM editted but server failed to start successfully within the expected timeframe. To start the server 'orchestrate server start'.")
    else:
        logger.info("Lima VM editted. To start the server 'orchestrate server start'.")
    

    return True

def _attach_docker_context_lima() -> bool:
    """Attach Docker CLI to Lima VM and store current context."""
    try:
        # Get current docker context
        result = subprocess.run(["docker", "context", "show"], capture_output=True, text=True)
        if result.returncode != 0:
            current_context = "default"
        else:
            current_context = result.stdout.strip()

        cfg = Config()
        if current_context != "ibm-watsonx-orchestrate":
            cfg.write(DOCKER_CONTEXT, PREVIOUS_DOCKER_CONTEXT, str(current_context))

        # Use bundled Lima binary to verify VM exists
        lima_folder = files('ibm_watsonx_orchestrate.developer_edition.resources') / "lima"
        limactl_path = os.path.join(lima_folder, 'bin', 'limactl')

        result = subprocess.run([limactl_path, "list", "--json"], capture_output=True, text=True)
        if VM_NAME not in result.stdout:
            logger.error(f"Lima VM '{VM_NAME}' not found. Please create it first.")
            return False

        lima_vm_dir = os.path.expanduser(f"~/.lima/{VM_NAME}/sock")
        docker_sock = os.path.join(lima_vm_dir, "orchestrate.docker.sock")

        if not os.path.exists(docker_sock):
            logger.error(f"Docker socket not found: {docker_sock}")
            return False

        # Create or update Lima Docker context
        subprocess.run(
            ["docker", "context", "create", VM_NAME, "--docker", f"host=unix://{docker_sock}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Switch to Lima context
        os.environ.pop("DOCKER_HOST", None)
        result = subprocess.run(["docker", "context", "use", VM_NAME], capture_output=True, text=True)
        return result.returncode == 0

    except Exception as e:
        logger.error(f"Error attaching Docker context: {e}")
        return False


def _release_docker_context_lima() -> bool:
    """Restore the previously active Docker context from orchestrate config."""
    try:
        cfg = Config()
        previous_context = cfg.read(DOCKER_CONTEXT, PREVIOUS_DOCKER_CONTEXT)

        if previous_context is None:
            previous_context = 'default'

        os.environ.pop("DOCKER_HOST", None)

        result = subprocess.run(
            ["docker", "context", "use", previous_context],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return False
        else:
            return True

    except Exception as e:
        logger.error(f"Unexpected error while releasing Docker context: {e}")
        return False

def _get_container_logs(container_id: str = None, container_name: str = None):
    """
    Fetch logs for a Docker container by its ID or name.
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
        logger.error(f"Failed to get logs for container '{target}': {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error getting container logs: {e}")
        return False
    
def _ssh_into_lima():
    """
    SSH into the underlying ibm-watsonx-orchestrate Lima VM.
    """
    try:
        lima_folder = files("ibm_watsonx_orchestrate.developer_edition.resources") / "lima"
        limactl_path = os.path.join(lima_folder, 'bin', 'limactl')

        if not os.path.exists(limactl_path):
            logger.error(f"FATAL: limactl not found at {limactl_path}")
            return False

        # Run Lima shell interactively and capture exit code manually
        result = subprocess.run(
            [limactl_path, "shell", VM_NAME],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        # Exit code 0 = normal, 130 = user exited or Ctrl+C
        if result.returncode in (0, 130):
            return True

        logger.error(f"ERROR: Lima shell exited with code {result.returncode}")
        return False

    except Exception as e:
        logger.error(f"ERROR: Unexpected error while SSH-ing into Lima VM: {e}")
        return False


def _get_current_docker_context():
    result = subprocess.run(
        ["docker", "context", "show"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def _check_and_ensure_lima_memory_for_doc_processing(min_memory_gb: int=24) -> bool:
    """Check if the Lima VM has enough memory for document processing.  """
    vm_dir = Path.home() / ".lima" / VM_NAME
    config_path = vm_dir / "lima.yaml"
    
    if not config_path.exists():
        logger.warning(f"Lima config not found at {config_path}. VM may not be created yet.")
        return True  # Will be set during VM creation
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Get current memory (format: "16GiB" or just number)
        current_memory = config.get("memory", f"{DEFAULT_MEMORY}GiB")
        
        # Parse memory value
        if isinstance(current_memory, str):
            if current_memory.upper().endswith("GIB") or current_memory.upper().endswith("GB"):
                current_memory_gb = int(''.join(filter(str.isdigit, current_memory)))
            else:
                current_memory_gb = int(current_memory)
        else:
            current_memory_gb = int(current_memory)
        
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
                f"Current Lima VM memory allocation: {current_memory_gb}GB\n"
                f"\n"
                f"Automatically increasing memory to {min_memory_gb}GB...\n"
                f"This requires restarting the VM.\n"
                f"{'='*70}\n"
            )
            # Update memory in config (preserves all other settings)
            config["memory"] = f"{min_memory_gb}GiB"
            
            # Write updated config back to file
            with open(config_path, "w") as f:
                yaml.dump(config, f)
            
            logger.info(f"Updated {config_path} with memory={min_memory_gb}GiB")
        
            return False        

    except Exception as e:
        logger.error(f"Failed to check Lima VM memory: {e}")
        return False

