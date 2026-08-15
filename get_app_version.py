from pathlib import Path
import re

path = Path(__file__).resolve().parent.parent / "main.py"
text = path.read_text(encoding="utf-8")
match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
print(match.group(1) if match else "2.2.0")
