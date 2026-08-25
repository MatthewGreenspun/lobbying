"""Fetch the newest NY lobbying filings and write them to public/latest.json.

Run by the GitHub Actions workflow on a schedule; can also be run locally:
    python scripts/generate.py 50
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from core import latest  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
data = latest(n)

out = pathlib.Path(__file__).parent.parent / "public" / "latest.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(data))
print(f"wrote {out} — {len(data['filings'])} filings (frontier {data['frontier']})")
