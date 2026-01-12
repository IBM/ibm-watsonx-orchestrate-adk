import sys
import json
import rich
import requests
import logging
import importlib
import inspect
import io
import yaml
from pathlib import Path
from typing import List, Any, Optional
from zipfile import ZipFile
from io import BytesIO

from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.client.connections import get_connections_client
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import FileUpload, KnowledgeBaseListEntry
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import KnowledgeBaseKind, IndexConnection, SpecVersion
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection

logger = logging.getLogger(__name__)

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
    index_config = get_index_config(kb)
    if not index_config:
        return
    return index_config.app_id

def get_kb_connection_id(kb: KnowledgeBase) -> str | None:
    index_config = get_index_config(kb)
    if not index_config:
        return
    return index_config.connection_id

class KnowledgeBaseController:
    def __init__(self):
        self.client = None
        self.connections_client = None

    def get_client(self):
        if not self.client:
            self.client = instantiate_client(KnowledgeBaseClient)
        return self.client
    
    def import_knowledge_base(self, file: str, app_id: str):
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
                    index_config = get_index_config(kb)
                    if index_config:
                        index_config.connection_id = conn.connection_id
                else:
                    logger.error(f"No connection exists with the app-id '{app_id}'")
                    exit(1)

            # Ensure these values are None to prevent issues with datetime not being JSON serializable
            kb.updated_at = None
            kb.created_on = None
            kb.created_by = None

            try:
                file_dir = file_path.parent

                existing = list(filter(lambda ex: ex.get('name') == kb.name, existing_knowledge_bases))
                if len(existing) > 0:
                    logger.info(f"Existing knowledge base '{kb.name}' found. Updating...")
                    self.update_knowledge_base(existing[0].get("id"), kb=kb, file_dir=file_dir)
                    continue

                kb.validate_documents_or_index_exists()
                if kb.documents:
                    files = [build_file_object(file_dir, file) for file in kb.documents]
                    file_urls = { get_file_name(file): file.url for file in kb.documents if isinstance(file, FileUpload) and file.url }
                    
                    kb.prioritize_built_in_index = True
                    payload = kb.model_dump(exclude_none=True);
                    payload.pop('documents');

                    data = {
                        'knowledge_base': json.dumps(payload),
                        'file_urls': json.dumps(file_urls)
                    }

                    client.create_built_in(payload=data, files=files)
                else:
                    if len(kb.conversational_search_tool.index_config) != 1:
                        raise ValueError(f"Must provide exactly one conversational_search_tool.index_config. Provided {len(kb.conversational_search_tool.index_config)}.")
                    
                    if (kb.conversational_search_tool.index_config[0].milvus or \
                        kb.conversational_search_tool.index_config[0].elastic_search) and \
                            not kb.conversational_search_tool.index_config[0].connection_id:
                        raise ValueError(f"Must provide credentials (via --app-id) when using milvus or elastic_search.")

                    kb.prioritize_built_in_index = False
                    data = { 'knowledge_base': json.dumps(kb.model_dump(exclude_none=True)) }

                    client.create(payload=data)
                
                logger.info(f"Successfully imported knowledge base '{kb.name}'")
            except ClientAPIException as e:
                logger.error(f"Error importing knowledge base '{kb.name}\n' {e.response.text}")
    
    def get_id(
        self, id: str, name: str
    ) -> str:
        if id:
            return id
        
        if not name:
            logger.error("Either 'id' or 'name' is required")
            sys.exit(1)

        response = self.get_client().get_by_name(name)

        if not response:
            logger.warning(f"No knowledge base '{name}' found")
            sys.exit(1)

        return response.get('id')


    def update_knowledge_base(
        self, knowledge_base_id: str, kb: KnowledgeBase, file_dir: str | Path
    ) -> None:
        if isinstance(file_dir, str):
            file_dir = Path(file_dir)
        if kb.documents:
            status = self.get_client().status(knowledge_base_id)
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

            data = {
                'knowledge_base': json.dumps(payload),
                'file_urls': json.dumps(file_urls)
            }

            self.get_client().update_with_documents(knowledge_base_id, payload=data, files=files)
        else:
            if kb.conversational_search_tool and kb.conversational_search_tool.index_config:
                kb.prioritize_built_in_index = False

            data = { 'knowledge_base': json.dumps(kb.model_dump(exclude_none=True)) }
            self.get_client().update(knowledge_base_id, payload=data)

        logger.info(f"Knowledge base '{kb.name}' updated successfully")

    def knowledge_base_status( self, id: str, name: str, format: ListFormats = None) ->  dict | str | None:
        knowledge_base_id = self.get_id(id, name)
        response = self.get_client().status(knowledge_base_id)

        if 'documents' in response:
            response[f"documents ({len(response['documents'])})"] = ", ".join([str(doc.get('metadata', {}).get('original_file_name', '<Unnamed File>')) for doc in response['documents']])
            response.pop('documents')

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

        response = self.get_client().get()
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
            
            for column in column_args:
                table.add_column(column, **column_args[column])
            
            connections_dict = build_connections_map("connection_id")
            
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
                    app_id=app_id
                )
                if format == ListFormats.JSON:
                    knowledge_base_details.append(entry)
                else:
                    table.add_row(*entry.get_row_details())

            match format:
                case ListFormats.JSON:
                    return knowledge_base_details
                case ListFormats.Table:
                    return rich_table_to_markdown(table)
                case _:
                    rich.print(table)   

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
            connections_output_path: str = "/connections") -> None:
        
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        if not zip_file_out and output_file_extension not in  {".yaml", ".yml", ".zip"} :
            logger.error(f"Output file must end with the extension '.yaml', '.yml' or '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        
        knowledge_base_id = self.get_id(id, name)
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
        
        connection_id = get_kb_connection_id(knowledge_base)
        app_id = None
        if connection_id:
            connections_map = build_connections_map("connection_id")
            conn = connections_map.get(connection_id)
            if conn:
                app_id = conn.app_id
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
                    
                kb_yaml = yaml.dump(knowledge_base_spec, sort_keys=False, default_flow_style=False, allow_unicode=True)
                kb_yaml_bytes = kb_yaml.encode("utf-8")
                kb_yaml_file = io.BytesIO(kb_yaml_bytes)
                zip_file_out.writestr(
                    f"{output_path.stem}/{knowledge_base.name}.yaml",
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
                    knowledge_base_spec_yaml = yaml.dump(knowledge_base_spec, sort_keys=False, default_flow_style=False, allow_unicode=True)
                    knowledge_base_spec_yaml_bytes = knowledge_base_spec_yaml.encode("utf-8")
                    knowledge_base_spec_yaml_file = BytesIO(knowledge_base_spec_yaml_bytes)
                    zip_file_out.writestr(
                        f"{output_path}/{knowledge_base.name}.yaml",
                        knowledge_base_spec_yaml_file.getvalue()
                    )

                    if app_id:
                        export_connection(output_file=connections_output_path, app_id=app_id, zip_file_out=zip_file_out)

        
        logger.info(f"Successfully exported for knowledge base {logEnding} to '{output_path}'")
