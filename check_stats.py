with open('scoring_config.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('"preseason_transfers": "true"', '"preseason_transfers": true')
content = content.replace('"preseason_transfers": "false"', '"preseason_transfers": false')

with open('scoring_config.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')

# Verify
from scoring_config import SCORING_CONFIG
print(f"preseason_transfers = {SCORING_CONFIG['preseason_transfers']} ({type(SCORING_CONFIG['preseason_transfers']).__name__})")