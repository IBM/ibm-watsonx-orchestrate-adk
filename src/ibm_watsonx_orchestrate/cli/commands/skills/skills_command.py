"""CLI commands for Skills management."""

import typer
from typing_extensions import Annotated, Optional
from rich.console import Console
from ibm_watsonx_orchestrate.cli.commands.skills.skills_controller import SkillsController
import logging

logger = logging.getLogger(__name__)
console = Console()

skills_app = typer.Typer(no_args_is_help=True)


def _validate_skill_identifier(skill_id: Optional[str], skill_name: Optional[str]) -> None:
    if not skill_id and not skill_name:
        console.print("[red]Error:[/red] Either --skill-id or --skill-name must be specified")
        raise typer.Exit(1)
    if skill_id and skill_name:
        console.print("[red]Error:[/red] Cannot specify both --skill-id and --skill-name")
        raise typer.Exit(1)


@skills_app.command(name="import", help='Import skill(s) from a file or directory')
def import_skill_cmd(
    file: Annotated[
        Optional[str],
        typer.Option("--file", "-f", help="Path to SKILL.md file"),
    ] = None,
    directory: Annotated[
        Optional[str],
        typer.Option("--dir", "-d", help="Path to directory containing SKILL.md (or subdirectories with --recursive)"),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-r", help="Search subdirectories for SKILL.md files (use with --dir)"),
    ] = False,
    workspace_id: Annotated[
        Optional[str],
        typer.Option("--workspace-id", "-w", help="Workspace ID (defaults to global)"),
    ] = None,
    upsert: Annotated[
        bool,
        typer.Option("--upsert", "-u", help="Update existing skills instead of erroring if they exist"),
    ] = False,
):
    """
    Import skill(s) from a SKILL.md file or a skill directory.

    Use --file for a single SKILL.md, --dir for a skill directory (auto-uploads
    scripts/ and references/), or --dir --recursive for bulk import of multiple
    skills in subdirectories. Add --upsert to update existing skills by name
    instead of erroring.

    Examples:
        orchestrate skills import --file skills/invoice-management/SKILL.md
        orchestrate skills import --dir skills/invoice-management/
        orchestrate skills import --dir skills/ --recursive
        orchestrate skills import --dir skills/ --recursive --upsert
    """
    if not file and not directory:
        console.print("[red]Error:[/red] Either --file or --dir must be specified")
        raise typer.Exit(1)

    if file and directory:
        console.print("[red]Error:[/red] Cannot specify both --file and --dir")
        raise typer.Exit(1)

    if recursive and not directory:
        console.print("[red]Error:[/red] --recursive can only be used with --dir")
        raise typer.Exit(1)

    skills_controller = SkillsController()

    if file:
        # Single file import (existing behavior)
        skills_controller.import_skill(file=file, workspace_id=workspace_id)
    elif directory:
        # Directory import (new behavior)
        skills_controller.import_skill_directory(
            directory=directory,
            recursive=recursive,
            workspace_id=workspace_id,
            upsert=upsert
        )


@skills_app.command(name="update", help='Update an existing skill with a new SKILL.md file')
def update_skill_cmd(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="Path to updated SKILL.md file"),
    ],
    skill_id: Annotated[
        Optional[str],
        typer.Option("--skill-id", "-s", help="ID of the skill to update"),
    ] = None,
    skill_name: Annotated[
        Optional[str],
        typer.Option("--skill-name", "-n", help="Name of the skill to update (alternative to --skill-id)"),
    ] = None,
):
    """
    Update an existing skill with a new SKILL.md file.

    You can specify the skill either by ID (--skill-id) or by name (--skill-name).
    The skill must exist before it can be updated.

    Examples:
        # Using skill ID
        orchestrate skillsupdate --skill-id abc-123 --file skills/invoice-management/SKILL.md
        orchestrate skillsupdate -s abc-123 -f skills/invoice-management/SKILL.md

        # Using skill name (easier!)
        orchestrate skills update --skill-name invoice-management --file skills/invoice-management/SKILL.md
        orchestrate skills update -n expense-tracking -f skills/expense-tracking/SKILL.md
    """
    _validate_skill_identifier(skill_id, skill_name)
    skills_controller = SkillsController()
    skills_controller.update_skill(skill_id=skill_id, skill_name=skill_name, file=file)


@skills_app.command(name="list", help='List all skills in the active env')
def list_skills_cmd(
    workspace_id: Annotated[
        Optional[str],
        typer.Option("--workspace-id", "-w", help="Filter by workspace ID"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="List full details of all skills in JSON format"),
    ] = False,
):
    """
    List all skills.

    Example:
        orchestrate skills list
        orchestrate skills list --workspace-id abc-123
        orchestrate skills list --verbose
    """
    skills_controller = SkillsController()
    skills_controller.list_skills(workspace_id=workspace_id, verbose=verbose)


@skills_app.command(name="remove", help='Remove a skill from the active env')
def remove_skill_cmd(
    skill_id: Annotated[
        Optional[str],
        typer.Option("--skill-id", "-s", help="ID of the skill to remove"),
    ] = None,
    skill_name: Annotated[
        Optional[str],
        typer.Option("--skill-name", "-n", help="Name of the skill to remove (alternative to --skill-id)"),
    ] = None,
):
    """
    Remove a skill by ID or name.

    Examples:
        orchestrate skills remove --skill-id abc-123
        orchestrate skills remove --skill-name invoice-management
    """
    _validate_skill_identifier(skill_id, skill_name)
    skills_controller = SkillsController()
    skills_controller.remove_skill(skill_id=skill_id, skill_name=skill_name)


@skills_app.command(name="export", help='Export a skill to a zip file or directory')
def export_skill_cmd(
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output path: .zip file to save as zip, or directory path to extract contents",
        ),
    ],
    skill_id: Annotated[
        Optional[str],
        typer.Option("--skill-id", "-s", help="ID of the skill to export"),
    ] = None,
    skill_name: Annotated[
        Optional[str],
        typer.Option("--skill-name", "-n", help="Name of the skill to export (alternative to --skill-id)"),
    ] = None,
):
    """
    Export a skill (by ID or name) to a zip file or directory.

    If output path ends with .zip, the skill is exported as a zip file containing
    SKILL.md, WXO.yaml (if applicable), all scripts, and all references.

    If output path is a directory, the contents are extracted to that directory.

    Examples:
        # Export as zip file (includes SKILL.md, WXO.yaml, scripts/, references/)
        orchestrate skills export --skill-name invoice-management -o ./exported/invoice-management.zip

        # Export to directory (extracts all files)
        orchestrate skills export --skill-id abc-123 --output ./exported/invoice-management/
    """
    _validate_skill_identifier(skill_id, skill_name)
    skills_controller = SkillsController()
    skills_controller.export_skill(output_path=output, skill_id=skill_id, skill_name=skill_name)


@skills_app.command(name="get", help='Show full details of one skill')
def get_skill_cmd(
    skill_id: Annotated[
        Optional[str],
        typer.Option("--skill-id", "-s", help="ID of the skill"),
    ] = None,
    skill_name: Annotated[
        Optional[str],
        typer.Option("--skill-name", "-n", help="Name of the skill (alternative to --skill-id)"),
    ] = None,
):
    """
    Show one skill's full details (including instructions body) as JSON.

    Examples:
        orchestrate skills get --skill-id abc-123
        orchestrate skills get --skill-name invoice-management
    """
    _validate_skill_identifier(skill_id, skill_name)
    skills_controller = SkillsController()
    skills_controller.show_skill(skill_id=skill_id, skill_name=skill_name)


@skills_app.command(name="upload-script", help='Upload a script file for a skill')
def upload_script_cmd(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="Path to the Python script file"),
    ],
    skill_id: Annotated[
        Optional[str],
        typer.Option("--skill-id", "-s", help="ID of the skill"),
    ] = None,
    skill_name: Annotated[
        Optional[str],
        typer.Option("--skill-name", "-n", help="Name of the skill (alternative to --skill-id)"),
    ] = None,
    script_path: Annotated[
        Optional[str],
        typer.Option(
            "--script-path",
            "-p",
            help="Relative path in skill (e.g., 'scripts/validate.py'). If not provided, auto-derived from file path.",
        ),
    ] = None,
):
    """
    Upload a script file for a skill.

    You can specify the skill either by ID (--skill-id) or by name (--skill-name).
    The script must be declared in the skill's SKILL.md frontmatter.
    The script-path will be auto-derived from the file path if not provided.

    Examples:
        # Using skill ID
        orchestrate skills upload-script --skill-id abc-123 --file /path/to/scripts/validate.py
        orchestrate skills upload-script -s abc-123 -f validate.py -p scripts/validate.py

        # Using skill name (easier!)
        orchestrate skills upload-script --skill-name invoice-management --file scripts/validate.py
        orchestrate skills upload-script -n expense-tracking -f scripts/validate_expense.py
    """
    _validate_skill_identifier(skill_id, skill_name)
    skills_controller = SkillsController()
    skills_controller.upload_script(
        skill_id=skill_id,
        skill_name=skill_name,
        script_file=file,
        script_path=script_path
    )


@skills_app.command(name="upload-reference", help='Upload a reference doc for a skill')
def upload_reference_cmd(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="Path to the reference file (any name/extension)"),
    ],
    skill_id: Annotated[
        Optional[str],
        typer.Option("--skill-id", "-s", help="ID of the skill"),
    ] = None,
    skill_name: Annotated[
        Optional[str],
        typer.Option("--skill-name", "-n", help="Name of the skill (alternative to --skill-id)"),
    ] = None,
    reference_path: Annotated[
        Optional[str],
        typer.Option(
            "--reference-path",
            "-p",
            help="Relative path in skill (e.g., 'references/REFERENCE.md'). If not provided, auto-derived from file path.",
        ),
    ] = None,
):
    """
    Upload a reference doc for a skill (agentskills.io references/).

    You can specify the skill either by ID (--skill-id) or by name (--skill-name).
    Unlike scripts, references may have any name or extension (REFERENCE.md,
    finance.txt, lookup.json …); they are not declared in SKILL.md — the runtime
    auto-discovers them and reads them on demand. The reference-path is
    auto-derived from the file path if not provided.

    Examples:
        # Using skill ID
        orchestrate skillsupload-reference --skill-id abc-123 --file /path/to/references/REFERENCE.md
        orchestrate skillsupload-reference -s abc-123 -f finance.txt -p references/finance.txt

        # Using skill name (easier!)
        orchestrate skills upload-reference --skill-name invoice-management --file references/REFERENCE.md
        orchestrate skills upload-reference -n expense-tracking -f references/policy.md
    """
    _validate_skill_identifier(skill_id, skill_name)
    skills_controller = SkillsController()
    skills_controller.upload_reference(
        skill_id=skill_id,
        skill_name=skill_name,
        reference_file=file,
        reference_path=reference_path
    )
