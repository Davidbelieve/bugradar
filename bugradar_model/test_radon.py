from radon.complexity import cc_visit
from radon.raw import analyze

with open('test_code.py', 'r') as f:
    code = f.read()

print('Code length:', len(code))
print('First 100 chars:', repr(code[:100]))

blocks = cc_visit(code)
print('Blocks found:', len(blocks))
for b in blocks:
    print(' -', b.name, 'complexity:', b.complexity, 'line:', b.lineno)