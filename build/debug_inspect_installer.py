from pathlib import Path
p = Path('build/build_installer.bat')
text = p.read_text()
lines = text.splitlines()
for i, line in enumerate(lines, start=1):
    if 'Program Files' in line or 'ISCC.exe' in line or 'if exist' in line:
        print('LINE', i, repr(line))
        print('CODES', [ord(c) for c in line])
        print('LEN', len(line))
        print('-----')
