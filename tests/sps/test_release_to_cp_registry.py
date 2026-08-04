"""
Tests that every image tag variable defined in default.env is referenced
in .sps/utils/release-to-cp-registry.sh, so newly added images can't be
silently omitted from the release copy step.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
ENV_FILE = REPO_ROOT / "src/ibm_watsonx_orchestrate/developer_edition/resources/docker/default.env"
SCRIPT_FILE = REPO_ROOT / ".sps/utils/release-to-cp-registry.sh"

# These TAG variables exist in default.env but intentionally have no
# corresponding image entry in the script (duplicates, empty, or non-image vars).
IGNORED_TAGS = {
    "AMDDBTAG",       # duplicate of DBTAG, amd64-only build artifact
    "ARM64DBTAG",     # duplicate of DBTAG, arm64-only build artifact
    "LANGFLOW_TAG",   # third-party image, not copied to cp registry
    "ETCD_TAG",       # empty in default.env — not used
    "ELASTICSEARCH_TAG",  # empty in default.env — not used
    "OPENSEARCH_TAG",     # empty in default.env — not used
}


def _get_tag_vars_from_env(env_file: Path) -> dict[str, str]:
    """Return a mapping of TAG_VAR_NAME -> value for all non-empty *_TAG lines."""
    tags = {}
    pattern = re.compile(r'^([A-Z0-9_]+TAG)\s*=\s*(.+)$')
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith('#'):
            continue
        m = pattern.match(line)
        if m:
            name, value = m.group(1), m.group(2).strip()
            if value:  # skip empty tags
                tags[name] = value
    return tags


def _get_tag_refs_from_script(script_file: Path) -> set[str]:
    """Return the set of TAG variable names referenced in the image list heredoc."""
    # Extract the heredoc block between "cat <<EOF" and the closing "EOF"
    script = script_file.read_text()
    heredoc_match = re.search(r'cat\s*<<EOF\n(.*?)\nEOF', script, re.DOTALL)
    assert heredoc_match, "Could not find the image list heredoc in the script"
    heredoc = heredoc_match.group(1)

    # Find all ${SOME_TAG} references inside the heredoc
    return set(re.findall(r'\$\{([A-Z0-9_]+TAG)\}', heredoc))


def test_all_env_tags_are_referenced_in_script():
    """Every non-empty *_TAG in default.env must appear in the script's image list."""
    env_tags = _get_tag_vars_from_env(ENV_FILE)
    script_refs = _get_tag_refs_from_script(SCRIPT_FILE)

    missing = {
        name for name in env_tags
        if name not in IGNORED_TAGS and name not in script_refs
    }

    assert not missing, (
        f"The following image tag variable(s) are defined in default.env but "
        f"not referenced in release-to-cp-registry.sh:\n"
        + "\n".join(f"  {name}={env_tags[name]}" for name in sorted(missing))
        + "\n\nAdd the corresponding image entry to the script's image list."
    )


def test_no_script_tags_reference_undefined_env_vars():
    """Every TAG variable referenced in the script must be defined in default.env."""
    env_tags = _get_tag_vars_from_env(ENV_FILE)
    # Also include empty-value tags so we can detect references to truly undefined vars
    all_env_tag_names = set()
    pattern = re.compile(r'^([A-Z0-9_]+TAG)\s*=')
    for line in ENV_FILE.read_text().splitlines():
        m = pattern.match(line.strip())
        if m:
            all_env_tag_names.add(m.group(1))

    script_refs = _get_tag_refs_from_script(SCRIPT_FILE)
    undefined = script_refs - all_env_tag_names

    assert not undefined, (
        f"The following TAG variable(s) are referenced in release-to-cp-registry.sh "
        f"but not defined in default.env:\n"
        + "\n".join(f"  ${{{name}}}" for name in sorted(undefined))
    )
