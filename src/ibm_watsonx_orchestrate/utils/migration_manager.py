
from enum import Enum
import logging
import os
from pathlib import Path
import shutil
from subprocess import CalledProcessError
from typing import Optional
from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.client.utils import path_for_vm
from ibm_watsonx_orchestrate.developer_edition.vm_host.vm_manager import get_vm_manager
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.developer_edition.resources.docker.db import get_migrations_root

logger = logging.getLogger(__name__)

class MigrationType(str, Enum):
  ORCHESTRATE = "orchestrate"
  OBSERVABILITY = "observability"
  ARCHITECT = "architect"
  LANGFLOW = "langflow"
  MCPGATEWAY = "mcpgateway"

MIGRATION_FILE_MAP = {
  MigrationType.LANGFLOW : 'langflow_migrations.sh',
  MigrationType.ARCHITECT : 'architect_migrations.sh',
  MigrationType.OBSERVABILITY : 'observability_migrations.sh',
  MigrationType.ORCHESTRATE : 'orchestrate_migrations.sh',
  MigrationType.MCPGATEWAY : 'mcpgateway_migrations.sh'
}

DB_SERVICE_LABEL = "wxo-server-db"
DB_CONTAINER_LABEL = f"dev-edition-{DB_SERVICE_LABEL}-1"



class MigrationException(Exception):
  # Only used here to pass specific exception up to parent so more context can be added to BadRequest
  pass


class VmAccessibleFile:

  def __init__(self, 
      file_path: str | Path, 
      persist: Optional[bool] = False, 
      cache_sub_dir: Optional[str] = None
    ):
    self.persist = persist
    self.source_path = file_path if isinstance(file_path, Path) else Path(file_path)

    # Ensure file exists
    if not self.source_path.exists():
      raise BadRequest(f"File '{file_path}' does not exist")
    
    # Some VM hosts cannot access files outside of the user's home dir
    # In some cases we cannot be sure the ADK is installed there (eg. python installed via homebrew)
    # To ensure file is accessbile in the VM we copy the file into the orchestrate cache

    # First check if provided file is already where we expect
    if str(self.source_path).startswith( str(Path.home() / ".cache/orchestrate") ) and \
      ( cache_sub_dir is None  or  str(self.source_path.parent).endswith(cache_sub_dir) ):
      self.adk_path = self.source_path
    
    else:
      orchestrate_dir = Path.home() / ".cache/orchestrate"
      orchestrate_dir.mkdir(parents=True, exist_ok=True)

      if cache_sub_dir:
        final_dir = orchestrate_dir / cache_sub_dir
        final_dir.mkdir(parents=True, exist_ok=True)
      else:
        final_dir = orchestrate_dir

      self.adk_path = final_dir / self.source_path.name
      shutil.copy(self.source_path, self.adk_path)

    # Used for folder cleanup
    self.cache_sub_dir = self.adk_path.parent if cache_sub_dir else None

    self.vm_path = path_for_vm(self.adk_path)

  def __del__(self):
    # Ensure cleanup of temp files, called by gc if not explicitly deleted
    if not self.persist:
      try:
        os.unlink(self.adk_path)
      except:
        logger.warning(f"Could not delete temp file '{self.adk_path}'")

    # Cleanup temp folder if present and empty
    if self.cache_sub_dir and not any(self.cache_sub_dir.iterdir()):
      try:
        os.rmdir(self.cache_sub_dir)
      except:
        logger.warning(f"Could not delete temp folder '{self.cache_sub_dir}'")
    


class MigrationsManager:

  def __init__(self, env_path: str, context: Optional[dict] = None):
    
    compose_path = EnvService(Config()).get_compose_file()

    self.vm_manager = get_vm_manager()
    self.env_file = VmAccessibleFile(env_path)
    self.compose_file = VmAccessibleFile(compose_path)
    self._context_vars = context or {}
    
    # copy files if mount is unsuccessful
    if not self._check_for_migration_files():
      self._copy_migration_files()


  def migrations_source_path(self):
    return f"{get_migrations_root()}/migrations/"
  
  def migrations_adk_path(self):
    return str( Path.home() / ".cache/orchestrate/migrations/" )

  def container_mount_path(self):
    return "/migrations"
  

  def run_orchestrate_migrations(self):
    self.run_migration(type=MigrationType.ORCHESTRATE)
    

  def run_langflow_migrations(self):
    self.run_migration(
      type=MigrationType.LANGFLOW, 
      additional_env={
        'PG_TIMEOUT': self._context_vars.get('PG_TIMEOUT', 10)
      }
    )
    

  def run_observability_migrations(self):
    self.run_migration(type=MigrationType.OBSERVABILITY)
    

  def run_architect_migrations(self):
    self.run_migration(type=MigrationType.ARCHITECT)
  

  def run_mcp_gateway_migrations(self):
    self.run_migration(type=MigrationType.MCPGATEWAY)

    
  def run_migration(self, type: MigrationType, additional_env: Optional[dict] = None):    
    script_path = f"{self.container_mount_path()}/{MIGRATION_FILE_MAP[type]}"
    env = {
        'PG_USER': self._context_vars.get('PG_USER','postgres')
      }
    if additional_env:
      env.update(additional_env)
    try:
      self._run_migration_script(
        script_path=script_path,
        required_env=env
      )
    except MigrationException:
      raise BadRequest(f"Failed to apply '{type.value}' migration")
    
    

  def _run_migration_script(self,
    script_path: str, 
    required_env: Optional[dict] = None, 
    retry_attempts: Optional[int] = 3
  ):
    
    command = script_path

    if required_env:
      env_args = " && ".join([f"export {k}={v}" for k,v in required_env.items()] + [""])
      command = env_args + command
    
    compose_command = [
        "compose",
        "-f", str(self.compose_file.vm_path),
        "--env-file", str(self.env_file.vm_path),
        "exec",
        "-u", "root",
        DB_SERVICE_LABEL,
        "bash",
        "-c",
        command
    ]

    while retry_attempts > 0:
      try:
        self.vm_manager.run_docker_command(compose_command, check=True)
      except CalledProcessError:
        retry_attempts -= 1
      else:
        return
    
    raise MigrationException
  
  
  def _check_for_migration_files(self):

    command = f"test -d {self.container_mount_path()}"

    compose_command = [
        "compose",
        "-f", str(self.compose_file.vm_path),
        "--env-file", str(self.env_file.vm_path),
        "exec",
        "-u", "root",
        DB_SERVICE_LABEL,
        "bash",
        "-c",
        command
    ]

    result = self.vm_manager.run_docker_command(compose_command, check=False)

    if result.returncode == 0:
      logger.info(f"Migration files found in db container")
      return True
    else:
      logger.warning(f"Migration files not found in db container")
      return False

  
  def _cache_migration_files(self):
    files = []
    for file_path in Path(self.migrations_source_path()).iterdir():
      files.append(VmAccessibleFile(file_path, cache_sub_dir="migrations"))
    
    return files

  
  def _copy_migration_files(self):

    files = self._cache_migration_files()

    logger.info(f"Copying migrations to {DB_CONTAINER_LABEL}:{self.container_mount_path()}")
    
    command = f"cp {path_for_vm(self.migrations_adk_path())} {DB_CONTAINER_LABEL}:{self.container_mount_path()}"

    result = self.vm_manager.run_docker_command(command)

    # manually cleanup
    del files

    if result.returncode == 0:
      command = f"chmod 755 -R {self.container_mount_path()}"

      compose_command = [
        "compose",
        "-f", str(self.compose_file.vm_path),
        "--env-file", str(self.env_file.vm_path),
        "exec",
        "-u", "root",
        DB_SERVICE_LABEL,
        "bash",
        "-c",
        command
      ]

      self.vm_manager.run_docker_command(compose_command)
    else:
      raise BadRequest(f"Failed to copy migration files to VM")
