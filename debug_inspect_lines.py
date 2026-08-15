from pathlib import Path
p = Path('build/build_installer.bat')
text = p.read_text()
lines = text.splitlines()
for i in range(40, 52):
    line = lines[i-1]
    print(i, repr(line), [hex(ord(c)) for c in line])
