import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import KnowledgeBaseController

knowledge_bases_app = typer.Typer(no_args_is_help=True)


@knowledge_bases_app.command(name="import", help="Import a knowledge-base by uploading documents, or providing an external vector index")
def knowledge_base_import(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="YAML, JSON or Python file with knowledge base definition(s)"),
    ],
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of the connection to associate with this knowledge base. A application connection represents the authentication credentials needed to connection to the external Milvus or Elasticsearch instance (for example Api Keys, Basic, Bearer or OAuth credentials).'
        )
    ] = None,
):
    controller = KnowledgeBaseController()
    controller.import_knowledge_base(file=file, app_id=app_id)

@knowledge_bases_app.command(name="patch", help="Patch a knowledge base by uploading documents, or providing an external vector index")
def knowledge_base_patch(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="YAML or JSON file with knowledge base definition"),
    ],
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the knowledge base you wish to update"),
    ]=None,
    id: Annotated[
        str,
        typer.Option("--id", "-i", help="ID of the knowledge base you wish to update"),
    ]=None
):
    controller = KnowledgeBaseController()
    controller.update_knowledge_base(id=id, name=name, file=file)


@knowledge_bases_app.command(name="list", help="List all knowledge bases")
def list_knowledge_bases(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="List full details of all knowledge bases in json format"),
    ] = False,
):  
    controller = KnowledgeBaseController()
    controller.list_knowledge_bases(verbose=verbose)

@knowledge_bases_app.command(name="remove", help="Remove a knowledge base. Note that if your knowledge base was created by uploading documents (for built-in Milvus), the ingested information from your documents will also be deleted. If your knowledge base uses an external knowledge source through an index_config definition, your index will not be deleted.")
def remove_knowledge_base(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the knowledge base you wish to remove"),
    ]=None,
    id: Annotated[
        str,
        typer.Option("--id", "-i", help="ID of the knowledge base you wish to remove"),
    ]=None
):  
    controller = KnowledgeBaseController()
    controller.remove_knowledge_base(id=id, name=name)

@knowledge_bases_app.command(name="status", help="Get the status of a knowledge base")
def knowledge_base_status(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the knowledge base you wish to get the status of"),
    ]=None,
    id: Annotated[
        str,
        typer.Option("--id", "-i", help="ID of the knowledge base you wish to get the status of"),
    ]=None
):  
    controller = KnowledgeBaseController()
    controller.knowledge_base_status(id=id, name=name)
