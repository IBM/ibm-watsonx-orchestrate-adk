import typer
import docker
import importlib.metadata

from rich import print
from rich.tree import Tree
from typing import Optional
from docker.errors import DockerException

__version__ = importlib.metadata.version('ibm-watsonx-orchestrate')


def version_callback(checkVersion: bool=True):
    if checkVersion:
        tree = Tree(
          f"[bold dark_olive_green1]:rocket: watsonx Orchestrate SDK [version]{__version__} :rocket:"
        )
        
        try:
          client = docker.from_env()
          containers = client.containers.list(all=True)

          for image in client.images.list(all=True):
            tag = image.tags[0]
            branch = tag.split("/")[-1].replace(":", "@")
            labels = ['architecture', 'build-date']

            branch_node = tree.add(f"[bold cyan] [branch]{branch}")
            branch_node.add(f"[magenta1] Image: [cornsilk1][image]{tag}")

            container = None
            for _container in containers:
              if _container.image.tags[0] == tag:
                container = _container

            if container:
              branch_node.add(f"[magenta1] Container: [cornsilk1][cont]{container.name}")

            for label in labels:
              if label in image.labels or (container and label in container.labels):
                val = image.labels[label] or container.labels[label]
                branch_node.add(f"[magenta1] [lb]{label.capitalize()}: [cornsilk1][val]{val}")

          print(tree)

        except DockerException as e:
            print(tree)
            print(f":x:[red]   [ERROR]   |  DockerException occurred on communication to the Docker daemon")

            errorStr = str(e)

            if (any(err in errorStr for err in ['Connection aborted', 'ConnectionRefusedError'])):
                print(f"\n:wrench:[grey93]  |  A possible resolution may be found at [u]docs/0_getting_started.md[/u] :mag:")

        raise typer.Exit()
    

def init_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
      None, 
      "--version",
      help="Check the version of package dependencies.",
      callback=version_callback
    )
):
    pass
