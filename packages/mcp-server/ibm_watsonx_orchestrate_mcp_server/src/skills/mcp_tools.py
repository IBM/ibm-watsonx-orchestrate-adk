import os
import shutil
from typing import Optional

import yaml

from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path

# Path to skills bundled within this package at build time.
# The skills/ directory is mapped here via Hatchling's force-include in pyproject.toml.
_BUNDLED_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "bundled")


def _get_bundled_skill_names() -> list[str]:
    """Return sorted list of bundled skill directory names."""
    if not os.path.isdir(_BUNDLED_SKILLS_DIR):
        return []
    return sorted(
        d for d in os.listdir(_BUNDLED_SKILLS_DIR)
        if os.path.isdir(os.path.join(_BUNDLED_SKILLS_DIR, d))
        and not d.startswith(".")
    )


def _parse_skill_metadata(skill_dir: str) -> dict[str, str]:
    """Parse YAML frontmatter from a skill's SKILL.md file."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return {}
    with open(skill_md, "r") as f:
        content = f.read()
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    frontmatter = yaml.safe_load(content[3:end])
    return frontmatter if isinstance(frontmatter, dict) else {}


def _detect_ide_skills_folder() -> Optional[str]:
    """
    Detect the coding IDE and return the appropriate skills folder path.

    Returns:
        str: The IDE-specific skills folder path, or None if IDE cannot be detected.
    """
    cwd = os.getcwd()

    ide_folders = {
        '.bob': '.bob/skills',
        '.opencode': '.opencode/skills',
        '.claude': '.claude/skills',
        '.cursor': '.cursor/skills',
        '.codex': '.codex/skills'
    }

    for ide_marker, skills_path in ide_folders.items():
        if os.path.exists(os.path.join(cwd, ide_marker)):
            return skills_path

    return None


def _resolve_output_directory(output_directory: Optional[str]) -> str:
    """Resolve the output directory from explicit parameter or IDE detection."""
    if output_directory:
        return get_working_directory_path(output_directory)

    ide_skills_folder = _detect_ide_skills_folder()
    if ide_skills_folder:
        return os.path.join(os.getcwd(), ide_skills_folder)

    raise ValueError(
        "Could not detect coding IDE. Please provide the 'output_directory' "
        "parameter to specify where to save the skill(s). "
        "For example: fetch_skill('skill_name', output_directory='./my_skills')"
    )


def fetch_skill(
    skill_name: str,
    output_directory: Optional[str] = None,
) -> str:
    """
    Fetch a skill from the bundled IBM watsonx Orchestrate ADK skills.

    Skills are bundled with this package and do not require network access.

    The output directory is automatically determined based on the detected coding IDE:
    - IBM Bob: .bob/skills
    - OpenCode: .opencode/skills
    - Claude: .claude/skills
    - Cursor: .cursor/skills
    - Codex: .codex/skills
    - Other/Unknown: User must provide output_directory parameter

    Args:
        skill_name (str): The name of the skill to fetch (e.g., 'watsonx-orchestrate-agent-builder')
        output_directory (str, optional): The directory where the skill should be saved. If not provided,
            the tool will attempt to detect the IDE and use the appropriate skills folder.

    Returns:
        str: A message indicating the success of the fetch operation and the location
            of the downloaded skill.

    Example:
        >>> fetch_skill("watsonx-orchestrate-agent-builder")
        "Successfully fetched skill 'watsonx-orchestrate-agent-builder' to .bob/skills/watsonx-orchestrate-agent-builder"

        >>> fetch_skill("watsonx-orchestrate-agent-builder", "./my_skills")
        "Successfully fetched skill 'watsonx-orchestrate-agent-builder' to /path/to/my_skills/watsonx-orchestrate-agent-builder"
    """

    # Verify skill exists in bundled data
    skill_source = os.path.join(_BUNDLED_SKILLS_DIR, skill_name)
    if not os.path.isdir(skill_source):
        available = _get_bundled_skill_names()
        raise FileNotFoundError(
            f"Skill '{skill_name}' not found in bundled skills. "
            f"Available skills: {', '.join(available)}"
        )

    base_output_dir = _resolve_output_directory(output_directory)
    os.makedirs(base_output_dir, exist_ok=True)

    skill_output_path = os.path.join(base_output_dir, skill_name)

    # Remove existing skill directory if it exists
    if os.path.exists(skill_output_path):
        shutil.rmtree(skill_output_path)

    # Copy bundled skill to output directory
    shutil.copytree(skill_source, skill_output_path)

    return f"Successfully fetched skill '{skill_name}' to {skill_output_path}"


def list_available_skills() -> str:
    """
    List all available skills bundled with this package, including their name and description metadata.

    Skills are bundled at build time and do not require network access.

    Returns:
        str: A formatted list of available skills with name and description.

    Example:
        >>> list_available_skills()
        "Available skills in the IBM watsonx Orchestrate ADK:\\n\\n  - watsonx-orchestrate-agent-builder: ..."
    """
    skill_dirs = _get_bundled_skill_names()

    if not skill_dirs:
        return "No bundled skills found."

    result = "Available skills in the IBM watsonx Orchestrate ADK:\n\n"
    for skill_dir in skill_dirs:
        metadata = _parse_skill_metadata(os.path.join(_BUNDLED_SKILLS_DIR, skill_dir))
        name = metadata.get("name", skill_dir)
        description = metadata.get("description", "")
        result += f"  - {skill_dir}\n"
        result += f"    Name: {name}\n"
        if description:
            result += f"    Description: {description}\n"
        result += "\n"

    result += (
        "View all skills at: "
        "https://github.com/IBM/ibm-watsonx-orchestrate-adk/tree/main/skills"
    )

    return result


def fetch_all_skills(
    output_directory: Optional[str] = None,
) -> str:
    """
    Fetch all available skills from the bundled IBM watsonx Orchestrate ADK skills.

    Skills are bundled with this package and do not require network access.

    The output directory is automatically determined based on the detected coding IDE:
    - IBM Bob: .bob/skills
    - OpenCode: .opencode/skills
    - Claude: .claude/skills
    - Cursor: .cursor/skills
    - Codex: .codex/skills
    - Other/Unknown: User must provide output_directory parameter

    Args:
        output_directory (str, optional): The directory where skills should be saved. If not provided,
            the tool will attempt to detect the IDE and use the appropriate skills folder.

    Returns:
        str: A message indicating the success of the fetch operation and the number
            of skills downloaded.

    Example:
        >>> fetch_all_skills()
        "Successfully fetched 6 skills to .bob/skills"

        >>> fetch_all_skills("./my_skills")
        "Successfully fetched 6 skills to /path/to/my_skills"
    """

    skills = _get_bundled_skill_names()
    if not skills:
        raise FileNotFoundError(
            "No bundled skills found."
        )

    base_output_dir = _resolve_output_directory(output_directory)
    os.makedirs(base_output_dir, exist_ok=True)

    skills_copied = []
    for skill_name in skills:
        skill_source = os.path.join(_BUNDLED_SKILLS_DIR, skill_name)
        skill_dest = os.path.join(base_output_dir, skill_name)

        if os.path.exists(skill_dest):
            shutil.rmtree(skill_dest)

        shutil.copytree(skill_source, skill_dest)
        skills_copied.append(skill_name)

    skills_list = "\n  - ".join(sorted(skills_copied))
    return (
        f"Successfully fetched {len(skills_copied)} skills to {base_output_dir}\n\n"
        f"Downloaded skills:\n  - {skills_list}"
    )


__tools__ = [fetch_skill, list_available_skills, fetch_all_skills]
