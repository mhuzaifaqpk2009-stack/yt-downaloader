from pathlib import Path
import re
import sys

if len(sys.argv) != 4:
    raise SystemExit("Usage: replace_installer_version.py <src> <dst> <version>")

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
version = sys.argv[3]
text = src.read_text(encoding="utf-8")
updated = re.sub(r'(#define MyAppVersion\s*\").*(\")', r'\1' + version + r'\2', text)
dst.write_text(updated, encoding="utf-8")
