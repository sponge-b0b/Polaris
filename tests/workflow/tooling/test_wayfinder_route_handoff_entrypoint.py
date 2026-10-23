from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[3]
SCRIPT = ROOT / ".agents/skills/wayfinder/scripts/route_handoff.py"


def test_documented_entrypoint_runs_without_pythonpath(tmp_path: Path) -> None:
    map_json = tmp_path / "map.json"
    map_json.write_text(
        json.dumps(
            {
                "title": "Wayfinder: test map",
                "url": "https://github.com/sponge-b0b/Polaris/issues/348",
                "body": "## Route Clarity\nRoute clear.\n",
            }
        ),
        encoding="utf-8",
    )
    attention = tmp_path / "attention.txt"
    attention.write_text(
        "ATTENTION: CLEAR\n"
        "Checkpoint: $wayfinder route clarity\n"
        "Material concerns: 0\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT.relative_to(ROOT)),
            "specification",
            "--map-json",
            str(map_json),
            "--attention-result",
            str(attention),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.splitlines()[0] == "WAYFINDER HANDOFF: SPECIFICATION"
    assert "$to-specs - Wayfinder: test map" in result.stdout
