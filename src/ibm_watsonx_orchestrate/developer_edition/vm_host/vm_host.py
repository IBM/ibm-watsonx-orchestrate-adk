from abc import ABC, abstractmethod
from typing import List, Optional

class VMLifecycleManager(ABC):
    """Abstract base class for VM lifecycle management.

    Implementations (e.g. WSL, Lima) must provide methods
    to manage VM lifecycle, run shell commands, and execute Docker commands.
    """

    @abstractmethod
    def start_server(self) -> None:
        """Start the VM host or ensure it is running."""
        pass

    @abstractmethod
    def stop_server(self) -> None:
        """Stop the VM host."""
        pass

    @abstractmethod
    def delete_server(self) -> None:
        """Delete or unregister the VM host completely."""
        pass

    @abstractmethod
    def shell(self, command: str | List[str], capture_output: bool = False) -> Optional[str]:
        """Run a command inside the VM host environment."""
        pass

    @abstractmethod
    def run_docker_command(self, command: str | List[str], capture_output: bool = False) -> Optional[str]:
        """Run a Docker command inside the VM host environment."""
        pass

    @abstractmethod
    def get_path_in_container(self, path: str) -> str:
        """Convert a host path to the equivalent container/VM path."""
        pass

    @abstractmethod
    def edit_server(self, cpus: Optional[int] = None, memory: Optional[int] = None, disk: Optional[int] = None) -> None:
        """Edit VM resource allocation (CPU, memory, disk)."""
        pass

    @abstractmethod
    def check_and_ensure_memory_for_doc_processing(self, min_memory_gb: int=24)-> None:
        """Check if the VM has enough memory for document processing.  """
        pass 
    
    @abstractmethod
    def show_current_context(self) -> Optional[str]:
        """Show current Docker context"""
        pass

    @abstractmethod
    def attach_docker_context(self) -> bool:
        """Switch the docker context to the ibm-watsonx-orchestrate context."""
        pass

    @abstractmethod
    def release_docker_context(self) -> bool:
        """Switch the docker context to the default context."""
        pass

    @abstractmethod
    def get_container_logs(self, container_id: str, container_name: str) -> Optional[str]:
        """Get the logs of a given container in the VM"""
        pass

    @abstractmethod
    def ssh(self) -> Optional[str]:
        """SSH into VM"""
        pass

    @abstractmethod
    def is_server_running(self) -> bool:
        """Returns a boolean indicating if the server is running or not"""
        pass