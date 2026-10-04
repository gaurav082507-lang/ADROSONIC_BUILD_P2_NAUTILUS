with open('web/src/api/hooks/index.ts', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("\\'", "'")

with open('web/src/api/hooks/index.ts', 'w', encoding='utf-8') as f:
    f.write(text)
