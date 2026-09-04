from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Collection
from typing import Any, cast


def inspect_package_import(
    package_name: str,
    *,
    forbidden_roots: Collection[str],
) -> dict[str, Any]:
    """Inspect an isolated package import without contaminating the test process."""
    script = """
import importlib
import json
import sys

package_name = sys.argv[1]
forbidden_roots = set(json.loads(sys.argv[2]))
before = set(sys.modules)
package = importlib.import_module(package_name)
loaded = set(sys.modules) - before
print(json.dumps({
    "exports": list(getattr(package, "__all__", ())),
    "loaded_package_children": sorted(
        module_name
        for module_name in loaded
        if module_name.startswith(f"{package_name}.")
    ),
    "loaded_forbidden_modules": sorted(
        module_name
        for module_name in loaded
        if module_name.split(".", maxsplit=1)[0] in forbidden_roots
    ),
}))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            package_name,
            json.dumps(sorted(forbidden_roots)),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return cast(dict[str, Any], json.loads(completed.stdout))
