"""Controller for Skills CLI commands."""

import io
import logging
import mimetypes
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
import rich
import rich.table
import yaml
from rich.console import Console

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

_WXO_YAML = "WXO.yaml"

MAX_DESCRIPTION_LENGTH = 50
MAX_TOOLS_DISPLAY_LENGTH = 30


def _find_wxo_yaml(skill_md_path: str) -> Optional[str]:
    """Return the WXO.yaml path next to a SKILL.md, or None if absent."""
    wxo = Path(skill_md_path).parent / _WXO_YAML
    return str(wxo) if wxo.exists() else None


def _error_detail(response) -> str:
    """Extract the error detail from a server response, JSON or not."""
    try:
        return response.json().get('detail', 'Unknown error')
    except ValueError:
        return (response.text or '').strip()[:200] or f"HTTP {response.status_code}"


def _extract_skill_name_from_md(skill_md_path: str) -> Optional[str]:
    """Extract the skill name from SKILL.md frontmatter."""
    try:
        with safe_open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            return frontmatter.get('name')
    except (OSError, ValueError, yaml.YAMLError) as e:
        logger.warning(f"Could not extract skill name from {skill_md_path}: {e}")
    return None


class SkillsController:
    """Controller for managing skills via CLI."""

    def __init__(self):
        self.client = instantiate_client(BaseWXOClient)
        self.base_url = f"{self.client.base_url}/skills"

    def get_all_skills(self, workspace_id: Optional[str] = None) -> list:
        """Fetch all skills from the server, optionally scoped to a workspace."""
        params = {"workspace_id": workspace_id} if workspace_id else {}
        response = requests.get(
            self.base_url,
            params=params,
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )
        if response.status_code != 200:
            detail = _error_detail(response)
            logger.error(f"Failed to list skills: {detail}")
            sys.exit(1)
        return response.json()

    def _resolve_skill_id_by_name(
        self,
        skill_name: str,
        workspace_id: Optional[str] = None,
    ) -> str:
        """Look up a skill's ID by its name via GET /skills."""
        response = requests.get(
            self.base_url,
            params={'workspace_id': workspace_id} if workspace_id else {},
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code != 200:
            detail = _error_detail(response)
            logger.error(f"Error listing skills: {detail}")
            raise BadRequest(detail)

        matching = [s for s in response.json() if s['name'] == skill_name]

        if not matching:
            logger.error(f"Skill with name '{skill_name}' not found")
            raise BadRequest(f"Skill '{skill_name}' not found")

        if len(matching) > 1:
            logger.warning(f"Multiple skills found with name '{skill_name}', using the first one")

        skill_id = matching[0]['id']
        logger.info(f"Resolved skill '{skill_name}' to ID: {skill_id}")
        return skill_id

    def _find_existing_skill_by_name(
        self,
        skill_name: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[str]:
        """Find existing skill ID by name, returns None if not found."""
        try:
            response = requests.get(
                self.base_url,
                params={'workspace_id': workspace_id} if workspace_id else {},
                headers=self.client._get_headers(),
                verify=self.client.verify,
            )
            if response.status_code == 200:
                matching = [s for s in response.json() if s['name'] == skill_name]
                if matching:
                    if len(matching) > 1:
                        logger.warning(
                            f"Multiple skills found with name '{skill_name}', "
                            f"using the first one (ID: {matching[0]['id']})"
                        )
                    return matching[0]['id']
        except Exception as e:
            logger.warning(f"Could not check for existing skill '{skill_name}': {e}")
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Import
    # ──────────────────────────────────────────────────────────────────────────

    def import_skill(
        self,
        file: str,
        workspace_id: Optional[str] = None,
    ) -> dict:
        """
        Import a SKILL.md file. Updates an existing skill if one with the same
        name already exists. A WXO.yaml in the same directory is sent alongside
        automatically.
        """
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        if not file.endswith('.md'):
            raise ValueError("File must be a .md (markdown) file")

        skill_name = _extract_skill_name_from_md(file)

        # Check if skill already exists and update instead of creating
        existing_skill_id = None
        if skill_name:
            existing_skill_id = self._find_existing_skill_by_name(skill_name, workspace_id)
            if existing_skill_id:
                logger.info(f"Skill '{skill_name}' already exists (ID: {existing_skill_id}), updating")

        if existing_skill_id:
            return self.update_skill(file=file, skill_id=existing_skill_id)

        wxo_yaml_path = _find_wxo_yaml(file)
        files: dict = {}
        data: dict = {}

        with safe_open(file, 'rb') as f:
            files['file'] = (os.path.basename(file), f.read(), 'text/markdown')

        if wxo_yaml_path:
            with safe_open(wxo_yaml_path, 'rb') as wf:
                files['wxo_file'] = (_WXO_YAML, wf.read(), 'application/x-yaml')
            logger.info(f"Including WXO.yaml from {wxo_yaml_path}")

        if workspace_id:
            data['workspace_id'] = workspace_id

        logger.info(f"Importing skill from '{file}'...")
        response = requests.post(
            self.base_url,
            files=files,
            data=data,
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code in (200, 201):
            skill_data = response.json()
            logger.info(
                f"Skill '{skill_data['name']}' imported successfully"
                f"{' (+ WXO.yaml)' if wxo_yaml_path else ''} (ID: {skill_data['id']})"
            )
            return skill_data
        else:
            error_detail = _error_detail(response)
            logger.error(f"Error importing skill: {error_detail}")
            raise BadRequest(error_detail)

    def update_skill(
        self,
        file: str,
        skill_id: Optional[str] = None,
        skill_name: Optional[str] = None,
    ) -> dict:
        """
        Update an existing skill with a new SKILL.md file.
        A WXO.yaml in the same directory is sent alongside if present.
        """
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        if not file.endswith('.md'):
            raise ValueError("File must be a .md (markdown) file")

        if skill_name and not skill_id:
            skill_id = self._resolve_skill_id_by_name(skill_name)

        if not skill_id:
            logger.error("Could not determine skill ID")
            raise BadRequest("Skill ID is required")

        skill = self.get_skill(skill_id)

        wxo_yaml_path = _find_wxo_yaml(file)
        files: dict = {}

        with safe_open(file, 'rb') as f:
            files['file'] = (os.path.basename(file), f.read(), 'text/markdown')

        if wxo_yaml_path:
            with safe_open(wxo_yaml_path, 'rb') as wf:
                files['wxo_file'] = (_WXO_YAML, wf.read(), 'application/x-yaml')
            logger.info(f"Including WXO.yaml from {wxo_yaml_path}")

        logger.info(f"Updating skill '{skill['name']}'...")
        response = requests.patch(
            f"{self.base_url}/{skill_id}",
            files=files,
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code == 200:
            skill_data = response.json()
            logger.info(
                f"Skill '{skill_data['name']}' updated successfully"
                f"{' (+ WXO.yaml)' if wxo_yaml_path else ''} (ID: {skill_data['id']})"
            )
            return skill_data
        else:
            error_detail = _error_detail(response)
            logger.error(f"Error updating skill: {error_detail}")
            raise BadRequest(error_detail)

    # ──────────────────────────────────────────────────────────────────────────
    # List / Get / Remove
    # ──────────────────────────────────────────────────────────────────────────

    def list_skills(
        self,
        workspace_id: Optional[str] = None,
        verbose: bool = False,
    ):
        """List all skills."""
        params = {}
        if workspace_id:
            params['workspace_id'] = workspace_id

        response = requests.get(
            self.base_url,
            params=params,
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code != 200:
            error_detail = _error_detail(response)
            logger.error(f"Error listing skills: {error_detail}")
            raise BadRequest(error_detail)

        skills = response.json()

        if not skills:
            logger.info("No skills found")
            return

        if verbose:
            Console().print_json(data=skills)
            return

        table = rich.table.Table(
            show_header=True,
            header_style="bold white",
            title="Skills",
            show_lines=True,
        )
        table.add_column("Name", overflow="fold")
        table.add_column("Description")
        table.add_column("Mode")
        table.add_column("Tools")
        table.add_column("Scripts")
        table.add_column("ID", overflow="fold")

        for skill in skills:
            tools_str = ", ".join(skill.get('tools', [])) or "-"
            scripts_count = str(len(skill.get('script_specs', [])))
            description = skill['description']
            if len(description) > MAX_DESCRIPTION_LENGTH:
                description = description[:MAX_DESCRIPTION_LENGTH] + "..."

            table.add_row(
                skill['name'],
                description,
                skill.get('mode', 'inline'),
                tools_str[:MAX_TOOLS_DISPLAY_LENGTH] + "..." if len(tools_str) > MAX_TOOLS_DISPLAY_LENGTH else tools_str,
                scripts_count,
                skill['id'],
            )

        rich.print(table)

    def get_skill(self, skill_id: str) -> dict:
        """Get a specific skill by ID."""
        response = requests.get(
            f"{self.base_url}/{skill_id}",
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.error(f"Skill not found: {skill_id}")
            raise BadRequest("Skill not found")
        else:
            error_detail = _error_detail(response)
            logger.error(f"Error getting skill: {error_detail}")
            raise BadRequest(error_detail)

    def show_skill(self, skill_id: Optional[str] = None, skill_name: Optional[str] = None):
        """Print one skill's full details (by ID or name) as JSON."""
        if skill_name and not skill_id:
            skill_id = self._resolve_skill_id_by_name(skill_name)

        if not skill_id:
            logger.error("Could not determine skill ID")
            raise BadRequest("Skill ID is required")

        skill = self.get_skill(skill_id)
        Console().print_json(data=skill)

    def remove_skill(self, skill_id: Optional[str] = None, skill_name: Optional[str] = None):
        """Remove a skill by ID or name."""
        if skill_name and not skill_id:
            skill_id = self._resolve_skill_id_by_name(skill_name)

        if not skill_id:
            logger.error("Could not determine skill ID")
            raise BadRequest("Skill ID is required")

        skill = self.get_skill(skill_id)

        logger.info(f"Removing skill '{skill['name']}'...")
        response = requests.delete(
            f"{self.base_url}/{skill_id}",
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code == 204:
            logger.info(f"Successfully removed skill '{skill['name']}'")
        else:
            error_detail = _error_detail(response)
            logger.error(f"Error removing skill: {error_detail}")
            raise BadRequest(error_detail)

    # ──────────────────────────────────────────────────────────────────────────
    # Export
    # ──────────────────────────────────────────────────────────────────────────

    def export_skill(
        self,
        output_path: str,
        skill_id: Optional[str] = None,
        skill_name: Optional[str] = None,
    ):
        """Export a skill (by ID or name) to a zip file or directory."""
        if skill_name and not skill_id:
            skill_id = self._resolve_skill_id_by_name(skill_name)

        if not skill_id:
            logger.error("Could not determine skill ID")
            raise BadRequest("Skill ID is required")

        skill = self.get_skill(skill_id)

        logger.info(f"Exporting skill '{skill['name']}'...")
        response = requests.get(
            f"{self.base_url}/{skill_id}/download",
            headers=self.client._get_headers(),
            verify=self.client.verify,
        )

        if response.status_code != 200:
            error_detail = _error_detail(response)
            logger.error(f"Error exporting skill: {error_detail}")
            raise BadRequest(error_detail)

        output_file = Path(output_path)

        if output_file.suffix == '.zip':
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(response.content)
            logger.info(f"Exported skill '{skill['name']}' to '{output_path}'")
        else:
            out_dir = output_file
            out_dir.mkdir(parents=True, exist_ok=True)

            content_type = response.headers.get('content-type', '')
            if 'zip' in content_type:
                extracted = []
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    for member in zf.namelist():
                        dest = out_dir / member
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(member))
                        extracted.append(member)
                logger.info(f"Exported skill '{skill['name']}' to '{output_path}': {', '.join(extracted)}")
            else:
                (out_dir / 'SKILL.md').write_bytes(response.content)
                logger.info(f"Exported skill '{skill['name']}' to '{output_path}/SKILL.md'")

    # ──────────────────────────────────────────────────────────────────────────
    # Script upload
    # ──────────────────────────────────────────────────────────────────────────

    def upload_script(
        self,
        script_file: str,
        skill_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        script_path: Optional[str] = None,
    ):
        """Upload a script file for a skill."""
        if not os.path.exists(script_file):
            raise FileNotFoundError(f"Script file not found: {script_file}")

        if not script_file.endswith('.py'):
            raise ValueError("Script file must be a .py (Python) file")

        if skill_name and not skill_id:
            skill_id = self._resolve_skill_id_by_name(skill_name)

        if script_path is None:
            file_parts = script_file.replace('\\', '/').split('/')
            if 'scripts' in file_parts:
                scripts_idx = file_parts.index('scripts')
                script_path = '/'.join(file_parts[scripts_idx:])
            else:
                script_path = f"scripts/{os.path.basename(script_file)}"
            logger.info(f"Auto-derived script path: {script_path}")

        _path = Path(script_path)
        if _path.is_absolute() or '..' in _path.parts:
            raise ValueError(
                f"Invalid script path '{script_path}': path must not contain '..' or be absolute"
            )

        if not skill_id:
            logger.error("Could not determine skill ID")
            raise BadRequest("Skill ID is required")

        skill = self.get_skill(skill_id)

        logger.info(f"Uploading script '{script_path}' to skill '{skill['name']}'...")
        with safe_open(script_file, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/{skill_id}/scripts",
                files={'file': (os.path.basename(script_file), f, 'text/x-python')},
                data={'script_path': script_path},
                headers=self.client._get_headers(),
                verify=self.client.verify,
            )

        if response.status_code in (200, 201):
            result = response.json()
            logger.info(
                f"Script uploaded successfully to skill '{skill['name']}': "
                f"{script_path} → {result.get('storage_path', 'N/A')}"
            )
        else:
            error_detail = _error_detail(response)
            logger.error(f"Error uploading script: {error_detail}")
            raise BadRequest(error_detail)

    # ──────────────────────────────────────────────────────────────────────────
    # Reference upload
    # ──────────────────────────────────────────────────────────────────────────

    def upload_reference(
        self,
        reference_file: str,
        skill_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        reference_path: Optional[str] = None,
    ):
        """Upload a reference doc for a skill.

        Unlike scripts, references may have any name/extension (REFERENCE.md,
        finance.txt, lookup.json …) and are not validated or declared in
        metadata — the server stores them and the runtime auto-discovers them.
        """
        if not os.path.exists(reference_file):
            raise FileNotFoundError(f"Reference file not found: {reference_file}")

        if skill_name and not skill_id:
            skill_id = self._resolve_skill_id_by_name(skill_name)

        if reference_path is None:
            file_parts = reference_file.replace('\\', '/').split('/')
            if 'references' in file_parts:
                refs_idx = file_parts.index('references')
                reference_path = '/'.join(file_parts[refs_idx:])
            else:
                reference_path = f"references/{os.path.basename(reference_file)}"
            logger.info(f"Auto-derived reference path: {reference_path}")

        _path = Path(reference_path)
        if _path.is_absolute() or '..' in _path.parts:
            raise ValueError(
                f"Invalid reference path '{reference_path}': path must not contain '..' or be absolute"
            )

        if not skill_id:
            logger.error("Could not determine skill ID")
            raise BadRequest("Skill ID is required")

        skill = self.get_skill(skill_id)

        content_type = mimetypes.guess_type(reference_file)[0] or 'application/octet-stream'

        logger.info(f"Uploading reference '{reference_path}' to skill '{skill['name']}'...")
        with safe_open(reference_file, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/{skill_id}/references",
                files={'file': (os.path.basename(reference_file), f, content_type)},
                data={'reference_path': reference_path},
                headers=self.client._get_headers(),
                verify=self.client.verify,
            )

        if response.status_code in (200, 201):
            result = response.json()
            logger.info(
                f"Reference uploaded successfully to skill '{skill['name']}': "
                f"{reference_path} → {result.get('storage_path', 'N/A')}"
            )
        else:
            error_detail = _error_detail(response)
            logger.error(f"Error uploading reference: {error_detail}")
            raise BadRequest(error_detail)

    # ──────────────────────────────────────────────────────────────────────────
    # Directory import
    # ──────────────────────────────────────────────────────────────────────────

    def _discover_skill_directories(self, base_dir: str, recursive: bool = False) -> List[Path]:
        """Discover directories containing SKILL.md files."""
        base_path = Path(base_dir).resolve()

        if not base_path.exists():
            raise FileNotFoundError(f"Directory not found: {base_dir}")

        if not base_path.is_dir():
            raise ValueError(f"Path is not a directory: {base_dir}")

        skill_dirs = []

        if recursive:
            for root, dirs, files in os.walk(base_path):
                if 'SKILL.md' in files:
                    skill_dirs.append(Path(root))
        else:
            skill_md = base_path / 'SKILL.md'
            if skill_md.exists():
                skill_dirs.append(base_path)
            else:
                raise FileNotFoundError(
                    f"No SKILL.md found in {base_dir}. "
                    f"Use --recursive to search subdirectories."
                )

        return skill_dirs

    def _get_scripts_in_directory(self, skill_dir: Path) -> List[Path]:
        """Get all Python scripts in the scripts/ subdirectory of a skill (recursively)."""
        scripts_dir = skill_dir / 'scripts'
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return []
        return list(scripts_dir.rglob('*.py'))

    def _get_references_in_directory(self, skill_dir: Path) -> List[Path]:
        """Get all reference files in the references/ subdirectory of a skill.

        Any name/extension is allowed (REFERENCE.md, finance.txt, lookup.json …),
        so this returns every file under references/ (recursively).
        """
        references_dir = skill_dir / 'references'
        if not references_dir.exists() or not references_dir.is_dir():
            return []
        return [p for p in references_dir.rglob('*') if p.is_file()]

    def import_skill_directory(
        self,
        directory: str,
        recursive: bool = False,
        workspace_id: Optional[str] = None,
        upsert: bool = False,
    ) -> Dict[str, Any]:
        """Import skill(s) from a directory or directory tree."""
        try:
            skill_dirs = self._discover_skill_directories(directory, recursive)
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            raise

        if not skill_dirs:
            logger.info(f"No SKILL.md files found in {directory}")
            return {"imported": [], "failed": [], "total": 0}

        logger.info(f"Found {len(skill_dirs)} skill(s) to import")

        # Fetch all existing skills once before the loop to avoid O(n) API calls
        existing_skills: dict = {}
        if upsert:
            try:
                response = requests.get(
                    self.base_url,
                    params={'workspace_id': workspace_id} if workspace_id else {},
                    headers=self.client._get_headers(),
                    verify=self.client.verify,
                )
                if response.status_code == 200:
                    existing_skills = {s['name']: s['id'] for s in response.json()}
                    logger.debug(f"Found {len(existing_skills)} existing skills for upsert check")
            except Exception as e:
                logger.warning(f"Could not fetch existing skills for upsert: {e}")

        imported = []
        failed = []

        for skill_dir in skill_dirs:
            skill_md = skill_dir / 'SKILL.md'
            wxo_yaml = skill_dir / _WXO_YAML
            skill_name = _extract_skill_name_from_md(str(skill_md)) or skill_dir.name

            try:
                skill_data = None

                if upsert and skill_name in existing_skills:
                    skill_data = self.update_skill(
                        file=str(skill_md),
                        skill_id=existing_skills[skill_name],
                    )

                if skill_data is None:
                    skill_data = self.import_skill(
                        file=str(skill_md),
                        workspace_id=workspace_id,
                    )

                # Upload scripts
                scripts = self._get_scripts_in_directory(skill_dir)
                scripts_uploaded = 0

                for script in scripts:
                    try:
                        script_rel_path = str(script.relative_to(skill_dir)).replace('\\', '/')
                        with safe_open(str(script), 'rb') as f:
                            response = requests.post(
                                f"{self.base_url}/{skill_data['id']}/scripts",
                                files={'file': (script.name, f, 'text/x-python')},
                                data={'script_path': script_rel_path},
                                headers=self.client._get_headers(),
                                verify=self.client.verify,
                            )
                            if response.status_code in (200, 201):
                                scripts_uploaded += 1
                                logger.info(f"Uploaded script {script.name} for skill {skill_name}")
                            else:
                                logger.warning(
                                    f"Failed to upload script {script.name} for skill {skill_name}: "
                                    f"{_error_detail(response)}"
                                )
                    except Exception as e:
                        logger.warning(f"Error uploading script {script.name}: {e}")

                # Upload references (any name/extension under references/)
                references = self._get_references_in_directory(skill_dir)
                references_uploaded = 0

                for ref in references:
                    try:
                        ref_rel_path = str(ref.relative_to(skill_dir)).replace('\\', '/')
                        ref_ct = mimetypes.guess_type(str(ref))[0] or 'application/octet-stream'
                        with safe_open(str(ref), 'rb') as f:
                            response = requests.post(
                                f"{self.base_url}/{skill_data['id']}/references",
                                files={'file': (ref.name, f, ref_ct)},
                                data={'reference_path': ref_rel_path},
                                headers=self.client._get_headers(),
                                verify=self.client.verify,
                            )
                            if response.status_code in (200, 201):
                                references_uploaded += 1
                                logger.info(f"Uploaded reference {ref.name} for skill {skill_name}")
                            else:
                                logger.warning(
                                    f"Failed to upload reference {ref.name} for skill {skill_name}: "
                                    f"{_error_detail(response)}"
                                )
                    except Exception as e:
                        logger.warning(f"Error uploading reference {ref.name}: {e}")

                imported.append({
                    'name': skill_data['name'],
                    'id': skill_data['id'],
                    'scripts': scripts_uploaded,
                    'references': references_uploaded,
                    'wxo_yaml': wxo_yaml.exists(),
                    'directory': str(skill_dir),
                })

            except Exception as e:
                failed.append({'name': skill_name, 'directory': str(skill_dir), 'error': str(e)})
                logger.error(f"  ✗ Failed to import skill from {skill_dir}: {e}")

        if imported:
            logger.info(f"Successfully imported {len(imported)} skill(s):")
            for skill in imported:
                wxo_note = " (+ WXO.yaml)" if skill.get('wxo_yaml') else ""
                logger.info(
                    f"  {skill['name']}{wxo_note}  "
                    f"({skill['scripts']} script(s), {skill.get('references', 0)} reference(s))"
                )

        if failed:
            logger.error(f"Failed to import {len(failed)} skill(s):")
            for skill in failed:
                logger.error(f"  {skill['name']}: {skill['error']}")

        return {'imported': imported, 'failed': failed, 'total': len(skill_dirs)}
