import os
import re

def fix_uploadfile(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(r'isinstance\(([a-zA-Z0-9_]+),\s*UploadFile\)', r"hasattr(\1, 'filename')", content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed UploadFile check in {filepath}')

for root, _, files in os.walk('backend/app/api/v1'):
    for file in files:
        if file.endswith('.py'):
            fix_uploadfile(os.path.join(root, file))
