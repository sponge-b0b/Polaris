#!/usr/bin/env python3
import base64, zlib
from pathlib import Path

here = Path(__file__).resolve().parent
payload = "".join(
    (here / f"chatgpt_cd_hardening.part{i}").read_text(encoding="utf-8").strip()
    for i in range(5)
)
source = zlib.decompress(base64.b64decode(payload)).decode("utf-8")
exec(compile(source, "chatgpt_cd_hardening.py", "exec"))
