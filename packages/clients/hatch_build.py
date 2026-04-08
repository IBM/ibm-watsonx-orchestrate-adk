"""Hatchling build hook to dynamically set version and pin dependencies."""

from pathlib import Path
import re
from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    """Custom metadata hook to set version and pin core dependency."""

    def update(self, metadata: dict) -> None:
        """Update metadata with version and pinned dependencies."""
        # Load version from main __init__.py
        root = Path(__file__).resolve().parents[2]
        init_file = root / "src" / "ibm_watsonx_orchestrate" / "__init__.py"
        text = init_file.read_text()
        
        # Extract version
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
        if not m:
            raise RuntimeError("Could not determine version from __init__.py")
        
        version = m.group(1)
        
        # Set version in metadata
        metadata["version"] = version
        
        # Get base dependencies from config options
        options = self.config.get("options", {})
        base_deps = options.get("base_dependencies", [])
        
        # Build final dependencies list
        deps = []
        for dep in base_deps:
            if dep.startswith("ibm-watsonx-orchestrate-core"):
                # Pin ibm-watsonx-orchestrate-core to the same version
                deps.append(f"ibm-watsonx-orchestrate-core=={version}")
            else:
                # Keep other dependencies as-is
                deps.append(dep)
        
        metadata["dependencies"] = deps
