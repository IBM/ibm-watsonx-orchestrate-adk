"""Hatchling build hook to dynamically set version and pin dependencies."""

from pathlib import Path
import re
from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    """Custom metadata hook to set version and pin synced package dependencies."""

    def update(self, metadata: dict) -> None:
        """Update metadata with version and pinned dependencies."""
        # Load version from main __init__.py
        root = Path(__file__).resolve().parent
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
        synced_packages = options.get("synced_packages", [])
        
        # Build final dependencies list
        deps = []
        for dep in base_deps:
            # Normalize dependency name for comparison (replace _ with -)
            dep_normalized = dep.replace("_", "-")
            
            # Check if this dependency should be pinned
            should_pin = False
            pkg_name = None
            for pkg in synced_packages:
                pkg_normalized = pkg.replace("_", "-")
                if dep_normalized.startswith(pkg_normalized):
                    should_pin = True
                    pkg_name = pkg
                    break
            
            if should_pin:
                # Pin to current version
                deps.append(f"{pkg_name}=={version}")
            else:
                # Keep other dependencies as-is
                deps.append(dep)
        
        metadata["dependencies"] = deps

# Made with Bob
