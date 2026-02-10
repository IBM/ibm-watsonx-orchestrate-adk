
from pathlib import Path
import re

def load_version():
    root = Path(__file__).resolve().parents[2]
    init_file = root / "src" / "ibm_watsonx_orchestrate" / "__init__.py"
    text = init_file.read_text()
    m = re.search(r'__version__\s*=\s*"\'["\']', text)
    if not m:
        raise RuntimeError("Could not determine version")
    return m.group(1)

def set_main_metadata(metadata):
    version = load_version()
    # Inject version
    metadata["version"] = version
    # Fix up dependency
    deps = metadata.get("dependencies", [])
    deps = [d for d in deps if not d.startswith("ibm-watsonx-orchestrate-core")]  # remove old
    deps.append(f"ibm-watsonx-orchestrate-core=={version}")
    metadata["dependencies"] = deps
