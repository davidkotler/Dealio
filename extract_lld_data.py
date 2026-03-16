import json
import sys

src = r'C:/Users/david_k/.claude/projects/C--work-projects-Dealio/d871bb19-9565-483f-bcb2-35c80c225b53/tool-results/toolu_019rd24cidYfi5MEHjLUbhTw.txt'
dst = r'C:/work_projects/Dealio/docs/designs/2026/001-price-drop-tracker/lld-data.md'

arrow = '\u2192'

with open(src, 'r', encoding='utf-8') as f:
    raw = f.read()

# Strip line-number prefixes (only at line start: whitespace + digits + arrow)
import re
lines = raw.split('\n')
stripped = []
for line in lines:
    # Only strip if the arrow appears after only digits+whitespace at line start
    m = re.match(r'^\s*\d+' + arrow + r'(.*)', line)
    if m:
        stripped.append(m.group(1))
    else:
        stripped.append(line)

json_text = '\n'.join(stripped)

try:
    data = json.loads(json_text)
except json.JSONDecodeError as e:
    if 'Extra data' in str(e):
        sys.stderr.write(f'Truncating at pos {e.pos} to remove extra data\n')
        data = json.loads(json_text[:e.pos])
    else:
        raise

text = data[0]['text']

if text.startswith('```markdown\n'):
    text = text[len('```markdown\n'):]
if text.endswith('\n```'):
    text = text[:-len('\n```')]

with open(dst, 'w', encoding='utf-8') as f:
    f.write(text)

sys.stderr.write(f'Written {len(text)} chars to lld-data.md\n')