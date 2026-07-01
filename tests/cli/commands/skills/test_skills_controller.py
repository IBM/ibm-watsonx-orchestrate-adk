import pytest
from unittest.mock import patch, MagicMock

from ibm_watsonx_orchestrate.cli.commands.skills.skills_controller import (
    SkillsController,
    _extract_skill_name_from_md,
    _find_wxo_yaml,
)
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


MOCK_BASE_URL = "http://localhost:4321"

MOCK_SKILL = {
    "id": "skill-abc-123",
    "name": "order-submit",
    "description": "Place and track customer orders.",
    "mode": "inline",
    "tools": ["create_order"],
    "script_specs": [],
}


@pytest.fixture
def controller():
    with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_controller.instantiate_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.base_url = MOCK_BASE_URL
        mock_client.verify = True
        mock_client._get_headers.return_value = {"Authorization": "Bearer test"}
        mock_factory.return_value = mock_client
        yield SkillsController()


# ── helpers ───────────────────────────────────────────────────────────────────

class TestExtractSkillNameFromMd:
    def test_extracts_name_from_frontmatter(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n# Body\n")
        assert _extract_skill_name_from_md(str(skill_md)) == "order-submit"

    def test_returns_none_when_no_frontmatter(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# No frontmatter\n")
        assert _extract_skill_name_from_md(str(skill_md)) is None

    def test_returns_none_on_nonexistent_file(self):
        assert _extract_skill_name_from_md("/nonexistent/SKILL.md") is None


class TestFindWxoYaml:
    def test_found(self, tmp_path):
        wxo = tmp_path / "WXO.yaml"
        wxo.write_text("mode: inline")
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("")
        assert _find_wxo_yaml(str(skill_md)) == str(wxo)

    def test_not_found(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("")
        assert _find_wxo_yaml(str(skill_md)) is None


# ── _resolve_skill_id_by_name ─────────────────────────────────────────────────

class TestResolveSkillIdByName:
    def test_resolves_id(self, controller):
        resp = MagicMock(status_code=200)
        resp.json.return_value = [MOCK_SKILL]
        with patch("requests.get", return_value=resp):
            assert controller._resolve_skill_id_by_name("order-submit") == MOCK_SKILL["id"]

    def test_not_found_raises(self, controller):
        resp = MagicMock(status_code=200)
        resp.json.return_value = []
        with patch("requests.get", return_value=resp):
            with pytest.raises(BadRequest, match="not found"):
                controller._resolve_skill_id_by_name("nonexistent")

    def test_api_error_raises(self, controller):
        resp = MagicMock(status_code=500)
        resp.json.return_value = {"detail": "Internal error"}
        with patch("requests.get", return_value=resp):
            with pytest.raises(BadRequest):
                controller._resolve_skill_id_by_name("order-submit")

    def test_multiple_matches_uses_first(self, controller, caplog):
        duplicate = dict(MOCK_SKILL, id="skill-xyz-456")
        resp = MagicMock(status_code=200)
        resp.json.return_value = [MOCK_SKILL, duplicate]
        with patch("requests.get", return_value=resp):
            result = controller._resolve_skill_id_by_name("order-submit")
        assert result == MOCK_SKILL["id"]
        assert "Multiple" in caplog.text


# ── _find_existing_skill_by_name ─────────────────────────────────────────────

class TestFindExistingSkillByName:
    def test_returns_id_when_found(self, controller):
        resp = MagicMock(status_code=200)
        resp.json.return_value = [MOCK_SKILL]
        with patch("requests.get", return_value=resp):
            assert controller._find_existing_skill_by_name("order-submit") == MOCK_SKILL["id"]

    def test_returns_none_when_not_found(self, controller):
        resp = MagicMock(status_code=200)
        resp.json.return_value = []
        with patch("requests.get", return_value=resp):
            assert controller._find_existing_skill_by_name("no-such-skill") is None

    def test_returns_none_on_api_exception(self, controller):
        with patch("requests.get", side_effect=Exception("network error")):
            assert controller._find_existing_skill_by_name("order-submit") is None


# ── get_skill ─────────────────────────────────────────────────────────────────

class TestGetSkill:
    def test_returns_skill_on_200(self, controller):
        resp = MagicMock(status_code=200)
        resp.json.return_value = MOCK_SKILL
        with patch("requests.get", return_value=resp):
            assert controller.get_skill(MOCK_SKILL["id"]) == MOCK_SKILL

    def test_404_raises_bad_request(self, controller):
        resp = MagicMock(status_code=404)
        with patch("requests.get", return_value=resp):
            with pytest.raises(BadRequest, match="not found"):
                controller.get_skill("bad-id")

    def test_other_error_raises_bad_request(self, controller):
        resp = MagicMock(status_code=500)
        resp.json.return_value = {"detail": "Server error"}
        with patch("requests.get", return_value=resp):
            with pytest.raises(BadRequest):
                controller.get_skill("bad-id")


# ── import_skill ──────────────────────────────────────────────────────────────

class TestImportSkill:
    def test_import_new_skill(self, controller, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n")

        list_resp = MagicMock(status_code=200)
        list_resp.json.return_value = []
        post_resp = MagicMock(status_code=201)
        post_resp.json.return_value = MOCK_SKILL

        with patch("requests.get", return_value=list_resp), \
             patch("requests.post", return_value=post_resp):
            result = controller.import_skill(file=str(skill_md))
        assert result["id"] == MOCK_SKILL["id"]

    def test_import_existing_skill_updates(self, controller, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n")

        list_resp = MagicMock(status_code=200)
        list_resp.json.return_value = [MOCK_SKILL]
        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        patch_resp = MagicMock(status_code=200)
        patch_resp.json.return_value = MOCK_SKILL

        with patch("requests.get", side_effect=[list_resp, get_resp]), \
             patch("requests.patch", return_value=patch_resp):
            result = controller.import_skill(file=str(skill_md))
        assert result["name"] == MOCK_SKILL["name"]

    def test_file_not_found_raises(self, controller):
        with pytest.raises(FileNotFoundError):
            controller.import_skill(file="/nonexistent/SKILL.md")

    def test_non_md_file_raises(self, controller, tmp_path):
        bad = tmp_path / "skill.yaml"
        bad.write_text("name: test")
        with pytest.raises(ValueError, match=".md"):
            controller.import_skill(file=str(bad))

    def test_server_error_raises(self, controller, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n")

        list_resp = MagicMock(status_code=200)
        list_resp.json.return_value = []
        post_resp = MagicMock(status_code=400)
        post_resp.json.return_value = {"detail": "Invalid skill name"}

        with patch("requests.get", return_value=list_resp), \
             patch("requests.post", return_value=post_resp):
            with pytest.raises(BadRequest, match="Invalid skill name"):
                controller.import_skill(file=str(skill_md))


# ── update_skill ──────────────────────────────────────────────────────────────

class TestUpdateSkill:
    def test_update_by_id_success(self, controller, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        patch_resp = MagicMock(status_code=200)
        patch_resp.json.return_value = MOCK_SKILL

        with patch("requests.get", return_value=get_resp), \
             patch("requests.patch", return_value=patch_resp):
            result = controller.update_skill(file=str(skill_md), skill_id=MOCK_SKILL["id"])
        assert result["id"] == MOCK_SKILL["id"]

    def test_skill_not_found_raises(self, controller, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n")

        get_resp = MagicMock(status_code=404)
        with patch("requests.get", return_value=get_resp):
            with pytest.raises(BadRequest):
                controller.update_skill(file=str(skill_md), skill_id="bad-id")

    def test_no_skill_id_raises(self, controller, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: order-submit\ndescription: Test\n---\n")
        with pytest.raises(BadRequest, match="required"):
            controller.update_skill(file=str(skill_md))


# ── remove_skill ──────────────────────────────────────────────────────────────

class TestRemoveSkill:
    def test_remove_success(self, controller, caplog):
        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        del_resp = MagicMock(status_code=204)

        with patch("requests.get", return_value=get_resp), \
             patch("requests.delete", return_value=del_resp):
            controller.remove_skill(skill_id=MOCK_SKILL["id"])
        assert "removed" in caplog.text.lower()

    def test_skill_not_found_raises(self, controller):
        get_resp = MagicMock(status_code=404)
        with patch("requests.get", return_value=get_resp):
            with pytest.raises(BadRequest):
                controller.remove_skill(skill_id="bad-id")

    def test_no_skill_id_raises(self, controller):
        with pytest.raises(BadRequest, match="required"):
            controller.remove_skill()

    def test_delete_error_raises(self, controller):
        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        del_resp = MagicMock(status_code=500)
        del_resp.json.return_value = {"detail": "Server error"}

        with patch("requests.get", return_value=get_resp), \
             patch("requests.delete", return_value=del_resp):
            with pytest.raises(BadRequest):
                controller.remove_skill(skill_id=MOCK_SKILL["id"])


# ── upload_script ─────────────────────────────────────────────────────────────

class TestUploadScript:
    def test_upload_success(self, controller, tmp_path):
        script = tmp_path / "validate.py"
        script.write_text("pass")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        post_resp = MagicMock(status_code=201)
        post_resp.json.return_value = {"storage_path": "scripts/validate.py"}

        with patch("requests.get", return_value=get_resp), \
             patch("requests.post", return_value=post_resp):
            controller.upload_script(
                script_file=str(script),
                skill_id=MOCK_SKILL["id"],
                script_path="scripts/validate.py",
            )

    def test_path_traversal_rejected(self, controller, tmp_path):
        script = tmp_path / "evil.py"
        script.write_text("pass")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        with patch("requests.get", return_value=get_resp):
            with pytest.raises(ValueError, match="Invalid script path"):
                controller.upload_script(
                    script_file=str(script),
                    skill_id=MOCK_SKILL["id"],
                    script_path="../../etc/passwd",
                )

    def test_absolute_path_rejected(self, controller, tmp_path):
        script = tmp_path / "evil.py"
        script.write_text("pass")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        with patch("requests.get", return_value=get_resp):
            with pytest.raises(ValueError, match="Invalid script path"):
                controller.upload_script(
                    script_file=str(script),
                    skill_id=MOCK_SKILL["id"],
                    script_path="/etc/passwd",
                )

    def test_file_not_found_raises(self, controller):
        with pytest.raises(FileNotFoundError):
            controller.upload_script(
                script_file="/nonexistent/validate.py",
                skill_id=MOCK_SKILL["id"],
            )

    def test_non_py_file_raises(self, controller, tmp_path):
        bad = tmp_path / "script.sh"
        bad.write_text("#!/bin/bash")
        with pytest.raises(ValueError, match=".py"):
            controller.upload_script(
                script_file=str(bad),
                skill_id=MOCK_SKILL["id"],
            )

    def test_auto_derives_script_path_from_scripts_dir(self, controller, tmp_path):
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "validate.py"
        script.write_text("pass")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        post_resp = MagicMock(status_code=201)
        post_resp.json.return_value = {"storage_path": "scripts/validate.py"}

        with patch("requests.get", return_value=get_resp), \
             patch("requests.post", return_value=post_resp) as post_mock:
            controller.upload_script(
                script_file=str(script),
                skill_id=MOCK_SKILL["id"],
            )
        _, kwargs = post_mock.call_args
        assert kwargs["data"]["script_path"].startswith("scripts/")


# ── upload_reference ──────────────────────────────────────────────────────────

class TestUploadReference:
    def test_upload_success(self, controller, tmp_path):
        ref = tmp_path / "REFERENCE.md"
        ref.write_text("content")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        post_resp = MagicMock(status_code=201)
        post_resp.json.return_value = {"storage_path": "references/REFERENCE.md"}

        with patch("requests.get", return_value=get_resp), \
             patch("requests.post", return_value=post_resp):
            controller.upload_reference(
                reference_file=str(ref),
                skill_id=MOCK_SKILL["id"],
                reference_path="references/REFERENCE.md",
            )

    def test_path_traversal_rejected(self, controller, tmp_path):
        ref = tmp_path / "ref.md"
        ref.write_text("content")

        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = MOCK_SKILL
        with patch("requests.get", return_value=get_resp):
            with pytest.raises(ValueError, match="Invalid reference path"):
                controller.upload_reference(
                    reference_file=str(ref),
                    skill_id=MOCK_SKILL["id"],
                    reference_path="../../../etc/shadow",
                )

    def test_file_not_found_raises(self, controller):
        with pytest.raises(FileNotFoundError):
            controller.upload_reference(
                reference_file="/nonexistent/ref.md",
                skill_id=MOCK_SKILL["id"],
            )


# ── discover_skill_directories ────────────────────────────────────────────────

class TestDiscoverSkillDirectories:
    def test_finds_skill_in_base_dir(self, controller, tmp_path):
        (tmp_path / "SKILL.md").write_text("---\nname: test\n---\n")
        result = controller._discover_skill_directories(str(tmp_path))
        assert tmp_path in result

    def test_no_skill_md_raises(self, controller, tmp_path):
        with pytest.raises(FileNotFoundError):
            controller._discover_skill_directories(str(tmp_path))

    def test_recursive_finds_nested(self, controller, tmp_path):
        skill_a = tmp_path / "skill-a"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text("---\nname: skill-a\n---\n")
        skill_b = tmp_path / "skill-b"
        skill_b.mkdir()
        (skill_b / "SKILL.md").write_text("---\nname: skill-b\n---\n")

        result = controller._discover_skill_directories(str(tmp_path), recursive=True)
        assert skill_a in result
        assert skill_b in result

    def test_nonexistent_dir_raises(self, controller):
        with pytest.raises(FileNotFoundError):
            controller._discover_skill_directories("/nonexistent/path")
