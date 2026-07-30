import sys
import json
import rich
import requests
import logging
import importlib
import inspect
import io
import yaml
import time
from pathlib import Path
from typing import List, Any, Literal, Optional
from zipfile import ZipFile
from io import BytesIO
from rich.console import Console

from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException
from ibm_watsonx_orchestrate.client.connections import get_connections_client
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.utils.docker_utils import DockerUtils
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.utils.utils import check_file_in_zip
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import FileUpload, KnowledgeBaseListEntry
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown, check_safe_mode_and_prompt
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import KnowledgeBaseKind, IndexConnection, SpecVersion, KnowledgeBaseSyncJob  # KnowledgeBaseSyncJob: DEFERRED (sync_job scheduling)
# DEFERRED: format_cron_pattern_human, format_next_occurrence_relative unused until scheduling is re-enabled
# from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.utils import format_cron_pattern_human, format_next_occurrence_relative
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection
from ibm_watsonx_orchestrate_core.utils.workspaces import is_global_workspace_active, GLOBAL_WORKSPACE_NAME, GLOBAL_WORKSPACE_ID, WorkspaceContext

logger = logging.getLogger(__name__)
console = Console()

def import_python_knowledge_base(file: str) -> List[KnowledgeBase]:
    file_path = Path(file)
    file_directory = file_path.parent
    file_name = file_path.stem
    sys.path.append(str(file_directory))
    module = importlib.import_module(file_name)
    del sys.path[-1]

    knowledge_bases = []
    for _, obj in inspect.getmembers(module):
        if isinstance(obj, KnowledgeBase):
            knowledge_bases.append(obj)
    return knowledge_bases

def parse_file(file: str) -> List[KnowledgeBase]:
    if file.endswith('.yaml') or file.endswith('.yml') or file.endswith(".json"):
        knowledge_base = KnowledgeBase.from_spec(file=file)
        return [knowledge_base]
    elif file.endswith('.py'):
        knowledge_bases = import_python_knowledge_base(file)
        return knowledge_bases
    else:
        raise ValueError("file must end in .json, .yaml, .yml or .py")

def to_column_name(col: str):
    return " ".join([word.capitalize() if not word[0].isupper() else word for word in col.split("_")])

def get_file_name(file: str | FileUpload):
    path = file.path if isinstance(file, FileUpload) else file
    # This name prettifying currently screws up file type detection on ingestion
    # return to_column_name(path.split("/")[-1].split(".")[0])
    path = Path(path)
    return path.name

def get_relative_file_path(path, dir):
    file_path = Path(path)
    
    if file_path.is_absolute():
        return file_path
    
    return dir / file_path
    
def build_file_object(file_dir: str | Path, file: str | FileUpload):
    if isinstance(file_dir, str):
        file_dir = Path(file_dir)
    if isinstance(file, FileUpload):
        return ('files', (get_file_name(file.path), safe_open(get_relative_file_path(file.path, file_dir), 'rb')))
    return ('files', (get_file_name(file), safe_open(get_relative_file_path(file, file_dir), 'rb')))

def build_connections_map(key_attr: str) -> dict:
    connections_client = get_connections_client()
    connections = connections_client.list()

    return {getattr(conn, key_attr): conn for conn in connections}

def get_index_config(kb: KnowledgeBase, index: int = 0) -> IndexConnection | None:
    if kb.conversational_search_tool is not None \
        and kb.conversational_search_tool.index_config is not None \
        and len(kb.conversational_search_tool.index_config) > index:

        return kb.conversational_search_tool.index_config[index]
    return None

def get_kb_app_id(kb: KnowledgeBase) -> str | None:
    if kb.content_source is not None:
        return kb.content_source.connection_id  # app_id stored on spec before resolution
    index_config = get_index_config(kb)
    if not index_config:
        return
    return index_config.app_id

def get_kb_connection_id(kb: KnowledgeBase) -> str | None:
    if kb.content_source is not None:
        return kb.content_source.connection_id
    index_config = get_index_config(kb)
    if not index_config:
        return
    return index_config.connection_id

_VECTOR_INDEX_FIELDS = ("milvus", "elastic_search", "open_search", "astradb", "custom_search")

def _extract_api_error_message(e: ClientAPIException) -> str:
    """Extract the human-readable detail from a ClientAPIException response body."""
    try:
        if e.response is not None and e.response.text:
            try:
                return json.loads(e.response.text).get('detail', "Unexpected server error")
            except Exception:
                return "Unexpected server error"
    except Exception:
        pass
    return str(e)

class KnowledgeBaseController:
    def __init__(self, safe_mode: bool = False):
        self.client = None
        self.connections_client = None
        self.safe_mode = safe_mode

    def get_client(self):
        if not self.client:
            self.client = instantiate_client(KnowledgeBaseClient)
        return self.client

    @staticmethod
    def get_vector_index_type(index_config: IndexConnection) -> str | None:
        """Return the vector_index_type string matching the populated connection field."""
        for field in _VECTOR_INDEX_FIELDS:
            if getattr(index_config, field, None) is not None:
                return field
        return None

    @staticmethod
    def get_url_and_port_from_index_config(index_config: IndexConnection) -> tuple[str | None, str | None]:
        """Extract the URL (or host) and port from whichever connection type is populated."""
        if index_config.elastic_search:
            return index_config.elastic_search.url, index_config.elastic_search.port
        if index_config.open_search:
            return index_config.open_search.url, index_config.open_search.port
        if index_config.custom_search:
            return index_config.custom_search.url, None
        if index_config.milvus:
            return index_config.milvus.grpc_host, index_config.milvus.grpc_port
        if index_config.astradb:
            return index_config.astradb.api_endpoint, index_config.astradb.port
        return None, None

    def _validate_connection_creds(self, index_config: IndexConnection) -> None:
        """Validate credentials for a connection-based knowledge base.

        Calls POST /knowledge-bases/validate-creds and raises an error if the
        response is non-200, aborting the create/update operation.
        """
        connection_id = index_config.connection_id
        if not connection_id:
            return

        vector_index_type = self.get_vector_index_type(index_config)
        if not vector_index_type:
            return

        url, port = self.get_url_and_port_from_index_config(index_config)

        try:
            self.get_client().validate_creds(connection_id=connection_id, vector_index_type=vector_index_type, url=url, port=port)
        except ClientAPIException as e:
            raise ValueError(f"Connection credential validation failed: {_extract_api_error_message(e)}")

    def import_knowledge_base(self, file: str, app_id: str, sync: bool = False):
        client = self.get_client()

        knowledge_bases = parse_file(file=file)

        file_path: Path = Path(file)
        
        connections_map = None
        
        existing_knowledge_bases = client.get_by_names([kb.name for kb in knowledge_bases])
        
        for kb in knowledge_bases:
            app_id = app_id if app_id else get_kb_app_id(kb)
            if app_id:
                if not connections_map:
                    connections_map = build_connections_map("app_id")
                conn = connections_map.get(app_id)
                if conn:
                    if kb.content_source is not None:
                        kb.content_source.connection_id = conn.connection_id
                    else:
                        index_config = get_index_config(kb)
                        if index_config:
                            index_config.connection_id = conn.connection_id
                else:
                    logger.error(f"No connection exists with the app-id '{app_id}'")
                    exit(1)

            # Validate connection credentials before creating/updating
            index_config = get_index_config(kb)
            if index_config:
                try:
                    self._validate_connection_creds(index_config)
                except ValueError as e:
                    logger.error(str(e))
                    continue

            # Ensure these values are None to prevent issues with datetime not being JSON serializable
            kb.updated_at = None
            kb.created_on = None
            kb.created_by = None

            try:
                file_dir = file_path.parent

                existing = list(filter(lambda ex: ex.get('name') == kb.name, existing_knowledge_bases))
                if len(existing) > 0:
                    
                    # Check for cross-workspace update
                    existing_kb_workspace_id = existing[0].get('workspace_id')
                    workspace_context = WorkspaceContext()
                    active_workspace_id = workspace_context.get_active_workspace_id()
                    
                    if existing_kb_workspace_id and active_workspace_id and existing_kb_workspace_id != active_workspace_id:
                        # Get workspace names for info message
                        kb_workspace_name = GLOBAL_WORKSPACE_NAME if existing_kb_workspace_id == GLOBAL_WORKSPACE_ID else f"workspace {existing_kb_workspace_id}"
                        active_workspace_name = workspace_context.get_active_workspace_name() or "current workspace"
                        
                        logger.info(f"Knowledge Base '{kb.name}' belongs to {kb_workspace_name}, but you are currently in {active_workspace_name}. Attempting cross-workspace update...")
                    
                    # Check safe mode and prompt for confirmation if needed
                    if not check_safe_mode_and_prompt(
                        safe_mode=self.safe_mode,
                        resource_exists=True,
                        resource_type="knowledge base",
                        resource_name=kb.name
                    ):
                        logger.info(f"Skipping knowledge base '{kb.name}'")
                        continue
                    
                    logger.info(f"Existing knowledge base '{kb.name}' found. Updating...")
                    
                    self.update_knowledge_base(existing[0].get("id"), kb=kb, file_dir=file_dir, sync=sync)
                    continue

                kb.validate_documents_or_index_exists()
                response = None
                kb_id = None
                if kb.content_source:
                    # content_source KB: POST /knowledge-bases with JSON body (no /documents multipart)
                    kb.prioritize_built_in_index = True
                    payload = kb.model_dump(exclude_none=True)
                    payload.pop('sync_job', None)

                    try:
                        response = client.create_without_files(payload=payload)
                    except ClientAPIException as e:
                        error_msg = "Unknown error"
                        try:
                            if e.response is not None and hasattr(e.response, 'text'):
                                response_text = e.response.text
                                if response_text:
                                    try:
                                        error_data = json.loads(response_text)
                                        error_msg = error_data.get('detail', response_text)
                                    except:
                                        error_msg = response_text
                                else:
                                    error_msg = str(e)
                            else:
                                error_msg = str(e)
                        except Exception:
                            error_msg = str(e)

                        logger.error(f"Failed to create knowledge base: {error_msg}")
                        continue

                    kb_id = None
                    if response:
                        kb_id = response.get('id') or response.get('knowledge_base')

                    if kb_id:
                        logger.info(f"Successfully imported knowledge base '{kb.name}'")

                        # DEFERRED: sync_job scheduling deferred to a future release.
                        # if kb.sync_job:
                        #     self._create_schedule(client, kb_id, kb.sync_job.schedule, kb.name)

                        # Trigger an initial sync so the KB is indexed immediately after creation
                        self._trigger_sync(client, kb_id, kb.name)
                    else:
                        logger.info(f"Successfully started import for knowledge base '{kb.name}'")
                elif kb.documents:
                    files = [build_file_object(file_dir, file) for file in kb.documents]
                    file_urls = { get_file_name(file): file.url for file in kb.documents if isinstance(file, FileUpload) and file.url }
                    
                    kb.prioritize_built_in_index = True
                    payload = kb.model_dump(exclude_none=True);
                    payload.pop('documents');
                    # Remove sync_job from payload as it's handled separately
                    sync_job = payload.pop('sync_job', None)

                    data = {
                        'knowledge_base': json.dumps(payload),
                        'file_urls': json.dumps(file_urls)
                    }

                    try:
                        response = client.create_built_in(payload=data, files=files)
                    except ClientAPIException as e:
                        logger.error(f"Failed to create knowledge base: {_extract_api_error_message(e)}")
                        continue
                    
                    # Poll for import completion when documents are included
                    if response and 'knowledge_base' in response:
                        kb_id = response['knowledge_base']
                        self._poll_knowledge_base_status(client, kb_id, kb.name, False)
                    else:
                        logger.info(f"Successfully started import for knowledge base '{kb.name}'")
                else:
                    if len(kb.conversational_search_tool.index_config) != 1:
                        raise ValueError(f"Must provide exactly one conversational_search_tool.index_config. Provided {len(kb.conversational_search_tool.index_config)}.")
                    
                    if (kb.conversational_search_tool.index_config[0].milvus or \
                        kb.conversational_search_tool.index_config[0].elastic_search) and \
                            not kb.conversational_search_tool.index_config[0].connection_id:
                        raise ValueError(f"Must provide credentials (via --app-id) when using milvus or elastic_search.")

                    kb.prioritize_built_in_index = False
                    payload = kb.model_dump(exclude_none=True)
                    # Remove sync_job from payload as it's handled separately
                    sync_job = payload.pop('sync_job', None)
                    data = { 'knowledge_base': json.dumps(payload) }

                    try:
                        response = client.create(payload=data)
                        if response and 'knowledge_base' in response:
                            kb_id = response['knowledge_base']
                            
                            # DEFERRED: sync_job scheduling deferred to a future release.
                            # if kb.sync_job and kb_id:
                            #     self._create_schedule(client, kb_id, kb.sync_job.schedule, kb.name)
                    except ClientAPIException as e:
                        logger.error(f"Failed to create knowledge base: {_extract_api_error_message(e)}")
                        continue
                    
                    # No polling needed when no documents are included
                    logger.info(f"Successfully imported knowledge base '{kb.name}'")
            except ClientAPIException as e:
                logger.error(f"Failed to create knowledge base: {_extract_api_error_message(e)}")
    
    def _poll_knowledge_base_status(
        self,
        client: KnowledgeBaseClient,
        kb_id: str,
        kb_name: str,
        is_update: bool = False,
        poll_interval: int = 2,
        max_wait_time: int = 1200, # 20 minutes
        use_sync_state: bool = False
    ) -> None:
        """
        Poll the knowledge base status until it reaches a terminal state.
        
        Args:
            client: The knowledge base client
            kb_id: The knowledge base ID
            kb_name: The knowledge base name (for logging)
            poll_interval: Time in seconds between status checks (default: 2)
            max_wait_time: Maximum time in seconds to wait (default: 1200)
            use_sync_state: Whether to poll connector sync_state instead of built_in_index_status
        """
        start_time = time.time()
        status_display_map = {
            'update_pending': 'Update pending',
            'rebuilding': 'Rebuilding index',
            'ready': 'Ready',
            'not_ready': 'Not Ready',
            'error': 'Error',
            'started': 'Started',
            'in_progress': 'In progress',
            'ready_for_promotion': 'Ready for promotion',
            'stable': 'Stable',
            'failed': 'Failed',
            'unknown': 'Unknown'
        }
        
        last_status = None
        prefix_action_str = "Syncing" if use_sync_state else ("Updating" if is_update else "Importing")
        action_str = "synced" if use_sync_state else ("updated" if is_update else "imported")
        dot_count = 0  # Track the number of dots for animation
        last_poll_time = 0  # Track when we last polled the API
        animation_interval = 0.5  # Update dots every 0.5 seconds
        status = None  # Initialize status
        status_msg = ''  # Initialize status_msg
        status_field = 'sync_state' if use_sync_state else 'built_in_index_status'
        status_msg_field = 'sync_state_msg' if use_sync_state else 'built_in_index_status_msg'
        success_states = {'stable'} if use_sync_state else {'ready'}
        failure_states = {'failed'} if use_sync_state else {'error', 'not_ready'}
        
        with console.status(f"[bold green]{prefix_action_str} knowledge base '{kb_name}'.", spinner="dots") as status_display:
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                if elapsed_time > max_wait_time:
                    status_display.stop()
                    logger.warning(f"Knowledge base status polling timed out after {max_wait_time} seconds. Please use \"orchestrate knowledge-bases status -n {kb_name}\" to check the status of your {'update' if is_update else 'import'}.")
                    return
                
                # Check if it's time to poll the API
                should_poll = (current_time - last_poll_time) >= poll_interval
                
                try:
                    if should_poll:
                        status_response = client.status(kb_id)
                        status = status_response.get(status_field, '').lower()
                        status_msg = status_response.get(status_msg_field, '')
                        last_poll_time = current_time
                        
                        # Update last_status if it changed
                        if status != last_status:
                            last_status = status
                        
                        # Check for terminal states
                        if status in success_states:
                            if status_msg:
                                display_msg = status_msg.removeprefix("Last sync completed. ")
                                console.print(f"[green]✓[/green] Successfully {action_str} knowledge base '{kb_name}': [bold white]{display_msg}[/bold white]")
                            else:
                                console.print(f"[green]✓[/green] Successfully {action_str} knowledge base '{kb_name}'")
                            return
                        elif status in failure_states:
                            if status_msg:
                                console.print(f"[red]✗[/red] Knowledge base [bold red]'{kb_name}'[/bold red] {action_str} failed: [bold white]{status_msg}[/bold white]", style="bold red")
                            else:
                                console.print(f"[red]✗[/red] Knowledge base [bold red]'{kb_name}'[/bold red] {action_str} failed", style="bold red")
                            return
                    
                    # Animate the dots (cycle through 1, 2, 3 dots) - happens every animation_interval
                    dot_count = (dot_count % 3) + 1
                    dots = "." * dot_count
                    
                    # Update the spinner text with current status and animated dots
                    if use_sync_state and status_msg:
                        friendly_status = status_msg
                    else:
                        friendly_status = status_display_map.get(last_status, last_status.replace('_', ' ').title()) if last_status else ""
                    
                    if friendly_status:
                        status_display.update(f"[bold green]{prefix_action_str} knowledge base '{kb_name}' - {friendly_status}{dots}", spinner="dots")
                    else:
                        status_display.update(f"[bold green]{prefix_action_str} knowledge base '{kb_name}'{dots}", spinner="dots")
                    
                    # Sleep for animation interval
                    time.sleep(animation_interval)
                    
                except ClientAPIException as e:
                    logger.error(f"Error checking status for knowledge base '{kb_name}': {e.response.text}")
                    return
                except Exception as e:
                    logger.error(f"Unexpected error checking status for knowledge base '{kb_name}': {str(e)}")
                    return
    
    def _trigger_sync(
        self,
        client: KnowledgeBaseClient,
        kb_id: str,
        kb_name: str,
    ) -> None:
        """
        Trigger an on-demand sync for a connector-backed knowledge base and poll
        until sync_state reaches a terminal status.

        Args:
            client: The knowledge base client
            kb_id: The knowledge base ID
            kb_name: The knowledge base name (for logging)
        """
        if is_local_dev() and not DockerUtils.is_docker_container_running("wdpflight-svc"):
            logger.error(
                "Sync is not available because the server was not started with "
                "--with-ingestion-from-external-sources. Restart the server with "
                "that flag to enable syncing."
            )
            return

        try:
            client.sync(kb_id)
            self._poll_knowledge_base_status(client, kb_id, kb_name, False, use_sync_state=True)
        except ClientAPIException as e:
            logger.error(f"Failed to trigger sync for knowledge base '{kb_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error triggering sync for knowledge base '{kb_name}': {str(e)}")

    def _create_schedule(
        self,
        client: KnowledgeBaseClient,
        kb_id: str,
        schedule_pattern: str,
        kb_name: str
    ) -> None:
        """
        Create a schedule for a knowledge base.
        
        Args:
            client: The knowledge base client
            kb_id: The knowledge base ID
            schedule_pattern: The cron pattern for the schedule
            kb_name: The knowledge base name (for logging)
        """
        try:
            payload = {"pattern": schedule_pattern}
            client.create_schedule(kb_id, payload)
            logger.info(f"Successfully created schedule for knowledge base '{kb_name}' with pattern '{schedule_pattern}'")
        except ClientAPIException as e:
            logger.error(f"Failed to create schedule for knowledge base '{kb_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating schedule for knowledge base '{kb_name}': {str(e)}")
    
    def _update_schedule(
        self,
        client: KnowledgeBaseClient,
        kb_id: str,
        schedule_pattern: str,
        kb_name: str
    ) -> None:
        """
        Update a schedule for a knowledge base.
        
        Args:
            client: The knowledge base client
            kb_id: The knowledge base ID
            schedule_pattern: The cron pattern for the schedule
            kb_name: The knowledge base name (for logging)
        """
        try:
            payload = {"pattern": schedule_pattern}
            client.update_schedule(kb_id, payload)
            logger.info(f"Successfully updated schedule for knowledge base '{kb_name}' with pattern '{schedule_pattern}'")
        except ClientAPIException as e:
            if e.response is not None and e.response.status_code == 404:
                logger.warning(f"Schedule endpoint not available for knowledge base '{kb_name}' (KB may not be indexed yet). Schedule was not updated.")
            else:
                logger.error(f"Failed to update schedule for knowledge base '{kb_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating schedule for knowledge base '{kb_name}': {str(e)}")

    def _upsert_schedule(
        self,
        client: KnowledgeBaseClient,
        kb_id: str,
        schedule_pattern: str,
        kb_name: str
    ) -> None:
        """
        Create or update a schedule for a knowledge base, depending on whether
        a schedule already exists.

        Args:
            client: The knowledge base client
            kb_id: The knowledge base ID
            schedule_pattern: The cron pattern for the schedule
            kb_name: The knowledge base name (for logging)
        """
        try:
            client.get_schedule(kb_id)
            # Schedule exists — update it
            self._update_schedule(client, kb_id, schedule_pattern, kb_name)
        except ClientAPIException as e:
            if e.response is not None and e.response.status_code == 404:
                # No schedule yet — create one
                self._create_schedule(client, kb_id, schedule_pattern, kb_name)
            else:
                logger.error(f"Failed to create schedule for knowledge base '{kb_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving schedule for knowledge base '{kb_name}': {str(e)}")
    
    def get_id(
        self, id: str, name: str, workspace_id: Optional[str] = None
    ) -> str:
        if id:
            return id
        
        if not name:
            logger.error("Either 'id' or 'name' is required")
            sys.exit(1)

        client = self.get_client()
        
        # Use client method directly - it handles workspace_id parameter
        response = client.get_by_name(name, workspace_id=workspace_id)

        if not response:
            logger.warning(f"No knowledge base '{name}' found")
            sys.exit(1)

        return response.get('id')


    def update_knowledge_base(
        self, knowledge_base_id: str, kb: KnowledgeBase, file_dir: str | Path, sync: bool = False
    ) -> None:
        if isinstance(file_dir, str):
            file_dir = Path(file_dir)

        # Validate connection credentials before updating
        index_config = get_index_config(kb)
        if index_config:
            try:
                self._validate_connection_creds(index_config)
            except ValueError as e:
                logger.error(str(e))
                return

        client = self.get_client()
        
        if kb.content_source:
            # content_source KB: PATCH /knowledge-bases/<id> with JSON body (no /documents multipart)
            kb.prioritize_built_in_index = True
            payload = kb.model_dump(exclude_none=True)
            payload.pop('sync_job', None)

            client.update_without_files(knowledge_base_id, payload=payload)

            logger.info(f"Successfully updated knowledge base '{kb.name}'")

            # DEFERRED: sync_job scheduling deferred to a future release.
            # if kb.sync_job:
            #     self._upsert_schedule(client, knowledge_base_id, kb.sync_job.schedule, kb.name)

            if sync:
                self._trigger_sync(client, knowledge_base_id, kb.name)
        elif kb.documents:
            status = client.status(knowledge_base_id)
            existing_docs = [doc.get("metadata", {}).get("original_file_name", "") for doc in status.get("documents", [])]
            
            removed_docs = existing_docs[:]
            for file in kb.documents:
                filename = get_file_name(file)

                if filename in existing_docs:
                    logger.warning(f'Document \"{filename}\" already exists in knowledge base. Updating...')
                    removed_docs.remove(filename)

            for filename in removed_docs:
                logger.warning(f'Document \"{filename}\" removed from knowledge base.')

            files = [build_file_object(file_dir, file) for file in kb.documents]
            file_urls = { get_file_name(file): file.url for file in kb.documents if isinstance(file, FileUpload) and file.url }
            
            kb.prioritize_built_in_index = True
            payload = kb.model_dump(exclude_none=True)
            payload.pop('documents')
            sync_job = payload.pop('sync_job', None)

            data = {
                'knowledge_base': json.dumps(payload),
                'file_urls': json.dumps(file_urls)
            }

            client.update_with_documents(knowledge_base_id, payload=data, files=files)
            
            # Poll for update completion when documents are included
            self._poll_knowledge_base_status(client, knowledge_base_id, kb.name, True)
        else:
            if kb.conversational_search_tool and kb.conversational_search_tool.index_config:
                kb.prioritize_built_in_index = False

            payload = kb.model_dump(exclude_none=True)
            # Remove sync_job from payload as it's handled separately
            sync_job = payload.pop('sync_job', None)
            data = { 'knowledge_base': json.dumps(payload) }
            client.update(knowledge_base_id, payload=data)
            
            # DEFERRED: sync_job scheduling deferred to a future release.
            # if kb.sync_job:
            #     self._upsert_schedule(client, knowledge_base_id, kb.sync_job.schedule, kb.name)
            
            # No polling needed when no documents are included
            logger.info(f"Knowledge base '{kb.name}' updated successfully")

    def knowledge_base_status(self, id: str, name: str, verbose: bool = False, format: ListFormats = None) -> dict | str | None:
        knowledge_base_id = self.get_id(id, name)
        client = self.get_client()
        response = client.status(knowledge_base_id)

        if verbose:
            rich.print(rich.json.JSON(json.dumps(response, indent=4)))
            return response

        if 'documents' in response:
            response[f"documents ({len(response['documents'])})"] = ", ".join([str(doc.get('metadata', {}).get('original_file_name', '<Unnamed File>')) for doc in response['documents']])
            response.pop('documents')

        response.pop('draft_index', None)

        # For content_source KBs (identified by sync_state), strip irrelevant fields
        if 'sync_state' in response:
            response.pop('prioritize_built_in_index', None)
            response.pop('built_in_index_status_msg', None)
            # DEFERRED: sync_job scheduling deferred to a future release.
            # try:
            #     schedule = client.get_schedule(knowledge_base_id)
            #     pattern = schedule.get('repeat_opts', {}).get('pattern')
            #     next_occurrence = schedule.get('next_occurrence')
            #     if pattern:
            #         response['sync_schedule'] = format_cron_pattern_human(pattern)
            #     if next_occurrence:
            #         response['next_sync'] = format_next_occurrence_relative(next_occurrence)
            # except ClientAPIException:
            #     pass

        table = rich.table.Table(
            show_header=True,
            header_style="bold white",
            show_lines=True
        )

        if "id" in response:
            kbID = response["id"]
            del response["id"]

            response["id"] = kbID
        
        if format == ListFormats.JSON:
            return response
        
        [table.add_column(to_column_name(col), {}) for col in response.keys()]
        table.add_row(*[str(val) for val in response.values()])
        
        if format == ListFormats.Table:
            return rich_table_to_markdown(table)

        rich.print(table)


    def list_knowledge_bases(self, verbose: bool=False, format: ListFormats=None)-> List[dict[str, Any]] | List[KnowledgeBaseListEntry] | str | None:

        if verbose and format:
            logger.error("For knowledge base list, `--verbose` and `--format` are mutually exclusive options")
            sys.exit(1)

        client = self.get_client()
        response = client.get()
        knowledge_bases = [KnowledgeBase.model_validate(knowledge_base) for knowledge_base in response]

        knowledge_base_list = []
        if verbose:
            for kb in knowledge_bases:
                knowledge_base_list.append(json.loads(kb.model_dump_json(exclude_none=True)))
            rich.print(rich.json.JSON(json.dumps(knowledge_base_list, indent=4)))
            return knowledge_base_list
        else:
            knowledge_base_details=[]
            table = rich.table.Table(
                show_header=True,
                header_style="bold white",
                show_lines=True
            )

            column_args = {
                "Name": {"overflow": "fold"},
                "Description": {},
                "App ID": {},
                "ID": {"overflow": "fold"}
            }

            is_private_workspace = not is_global_workspace_active()
            
            for column in column_args:
                table.add_column(column, **column_args[column])
            
            if is_private_workspace:
                table.add_column("Global", justify="center" )

            connections_dict = build_connections_map("connection_id")

            has_content_source = any(kb.content_source for kb in knowledge_bases)

            # DEFERRED: sync_job scheduling deferred to a future release.
            # schedule_map: dict[str, str] = {}
            # if has_content_source:
            #     for kb in knowledge_bases:
            #         if kb.content_source and kb.id:
            #             try:
            #                 schedule = client.get_schedule(str(kb.id))
            #                 pattern = schedule.get('repeat_opts', {}).get('pattern')
            #                 if pattern:
            #                     schedule_map[str(kb.id)] = pattern
            #             except ClientAPIException:
            #                 pass

            # DEFERRED: Sync Pattern column removed until scheduling is re-enabled.
            # if has_content_source:
            #     table.add_column("Sync Pattern", {})
            
            for kb in knowledge_bases:
                app_id = ""
                connection_id = get_kb_connection_id(kb)
                if connection_id is not None:
                    conn = connections_dict.get(connection_id)
                    if conn:
                        app_id = conn.app_id

                entry = KnowledgeBaseListEntry(
                    name=kb.name,
                    id=str(kb.id),
                    description=kb.description,
                    app_id=app_id,
                )
                if is_private_workspace:
                    entry.is_global = kb.workspace == GLOBAL_WORKSPACE_NAME
                if format == ListFormats.JSON:
                    knowledge_base_details.append(entry)
                else:
                    row = entry.get_row_details()
                    # DEFERRED: sync_job scheduling deferred to a future release.
                    # if has_content_source:
                    #     if not kb.content_source:
                    #         row.append("N/A")
                    #     elif raw_pattern:
                    #         row.append(format_cron_pattern_human(raw_pattern))
                    #     else:
                    #         row.append("")
                    table.add_row(*row)

            match format:
                case ListFormats.JSON:
                    return knowledge_base_details
                case ListFormats.Table:
                    return rich_table_to_markdown(table)
                case _:
                    rich.print(table)

    def sync_knowledge_base(self, id: str, name: str) -> None:
        knowledge_base_id = self.get_id(id, name)
        client = self.get_client()

        # Verify this is a content_source knowledge base
        status_response = client.status(knowledge_base_id)
        if 'sync_state' not in status_response:
            kb_name = name or id
            logger.error(
                f"Knowledge base '{kb_name}' is not a connector-backed (content_source) knowledge base. "
                "The sync command is only supported for content_source knowledge bases."
            )
            sys.exit(1)

        kb_name = status_response.get('name', name or id)
        self._trigger_sync(client, knowledge_base_id, kb_name)

    def remove_knowledge_base(self, id: str, name: str):
        knowledge_base_id = self.get_id(id, name)      
        logEnding = f"with ID '{id}'" if id else f"'{name}'"

        try:
            self.get_client().delete(knowledge_base_id=knowledge_base_id)
            logger.info(f"Successfully removed knowledge base {logEnding}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No knowledge base {logEnding} found")
            logger.error(e.response.text)
            exit(1)
    
    def get_knowledge_base(self, id) -> KnowledgeBase:
        client = self.get_client()
        try:
            return KnowledgeBase.model_validate(client.get_by_id(id))
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"No knowledge base {id} found")
            else:
                logger.error(e.response.text)
            exit(1)


    def knowledge_base_export(self,
            output_path: str,
            id: Optional[str] = None,
            name: Optional[str] = None,
            zip_file_out: Optional[ZipFile] = None,
            connections_output_path: str = "/connections",
            workspace_id: Optional[str] = None) -> None:
        
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        if not zip_file_out and output_file_extension not in  {".yaml", ".yml", ".zip"} :
            logger.error(f"Output file must end with the extension '.yaml', '.yml' or '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        
        knowledge_base_id = self.get_id(id, name, workspace_id=workspace_id)
        logEnding = f"with ID '{id}'" if id else f"'{name}'"  
        
        logger.info(f"Exporting spec for knowledge base {logEnding}'")

        knowledge_base = self.get_knowledge_base(knowledge_base_id)

        if not knowledge_base:
            logger.error(f"Knowledge base'{knowledge_base_id}' not found.'")
            return
        
        knowledge_base.tenant_id = None
        knowledge_base.id = None
        knowledge_base.updated_at = None
        knowledge_base.created_on = None
        knowledge_base.created_by = None

        knowledge_base.spec_version = SpecVersion.V1
        knowledge_base.kind = KnowledgeBaseKind.KNOWLEDGE_BASE

        # DEFERRED: sync_job scheduling deferred to a future release.
        # if knowledge_base.content_source:
        #     try:
        #         schedule = self.get_client().get_schedule(knowledge_base_id)
        #         pattern = schedule.get('repeat_opts', {}).get('pattern')
        #         if pattern:
        #             knowledge_base.sync_job = KnowledgeBaseSyncJob(schedule=pattern)
        #     except ClientAPIException:
        #         pass

        connection_id = get_kb_connection_id(knowledge_base)
        app_id = None
        if connection_id:
            connections_map = build_connections_map("connection_id")
            conn = connections_map.get(connection_id)
            if conn:
                app_id = conn.app_id
                if knowledge_base.content_source:
                    # content_source KBs store app_id in connection_id on the spec
                    # (it is resolved to the real connection_id at import time)
                    knowledge_base.content_source.connection_id = app_id
                else:
                    index_config = get_index_config(knowledge_base)
                    index_config.app_id = app_id
                    index_config.connection_id = None
            else:
                logger.warning(f"Connection '{connection_id}' not found, unable to resolve app_id for Knowledge base {logEnding}")

        knowledge_base_spec = knowledge_base.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        
        output_path = Path(output_path)
        match(output_file_extension):
            case '.zip':
                if output_path.exists():
                    zip_file_out = ZipFile(output_path, "a")
                else:
                    zip_file_out = ZipFile(output_path, "w")
                    
                kb_file_path = f"{output_path.stem}/knowledge_bases/{knowledge_base.name}.yaml"
                
                # Check if knowledge base already exists in zip
                if check_file_in_zip(file_path=kb_file_path, zip_file=zip_file_out):
                    logger.warning(f"Skipping knowledge base '{knowledge_base.name}', already exists in the output folder")
                else:
                    kb_yaml = yaml.dump(knowledge_base_spec, sort_keys=False, default_flow_style=False, allow_unicode=True)
                    kb_yaml_bytes = kb_yaml.encode("utf-8")
                    kb_yaml_file = io.BytesIO(kb_yaml_bytes)
                    zip_file_out.writestr(
                        kb_file_path,
                        kb_yaml_file.getvalue()
                    )

                if app_id:
                    export_connection(output_file=f"{output_path.stem}/{connections_output_path}", app_id=app_id, zip_file_out=zip_file_out)

                zip_file_out.close()
            case '.yaml' | '.yml':
                if app_id:
                    logger.warning(f"Connection '{app_id}' found. Connections cannot be exported when output path is not '.zip'.")
                with safe_open(output_path, 'w') as outfile:
                    yaml.dump(knowledge_base_spec, outfile, sort_keys=False, default_flow_style=False, allow_unicode=True)
            case '':
                if zip_file_out:
                    kb_file_path = f"{output_path}/{knowledge_base.name}.yaml"
                    
                    # Check if knowledge base already exists in zip
                    if check_file_in_zip(file_path=kb_file_path, zip_file=zip_file_out):
                        logger.warning(f"Skipping knowledge base '{knowledge_base.name}', already exists in the output folder")
                    else:
                        knowledge_base_spec_yaml = yaml.dump(knowledge_base_spec, sort_keys=False, default_flow_style=False, allow_unicode=True)
                        knowledge_base_spec_yaml_bytes = knowledge_base_spec_yaml.encode("utf-8")
                        knowledge_base_spec_yaml_file = BytesIO(knowledge_base_spec_yaml_bytes)
                        zip_file_out.writestr(
                            kb_file_path,
                            knowledge_base_spec_yaml_file.getvalue()
                        )

                        if app_id:
                            export_connection(output_file=connections_output_path, app_id=app_id, zip_file_out=zip_file_out)

        
        logger.info(f"Successfully exported for knowledge base {logEnding} to '{output_path}'")
