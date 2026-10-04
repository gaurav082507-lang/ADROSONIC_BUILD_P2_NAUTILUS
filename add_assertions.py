import re
with open('scripts/final_e2e.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = '''
        # Assertions
        print('Running strict assertions...')
        await i_page.evaluate("""() => {
            const text = document.body.innerText;
            if (text.includes('Not analysed')) throw new Error('Found Not analysed text! Pipelines failed to run.');
        }""")
        
        await i_page.click('button:has-text("Image")')
        await i_page.wait_for_timeout(1500)
        await i_page.evaluate("""() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            const valid = imgs.filter(img => img.naturalWidth > 0);
            if (valid.length < 2) throw new Error('Image tab missing loaded images or heatmap.');
        }""")
        
        await i_page.click('button:has-text("Identity")')
        await i_page.wait_for_timeout(1000)
        await i_page.evaluate("""() => {
            const text = document.body.innerText.toLowerCase();
            if (!text.includes('passed')) throw new Error('Identity tab missing passed status');
        }""")
        
        await i_page.click('button:has-text("Claim checks")')
        await i_page.wait_for_timeout(1000)
        await i_page.evaluate("""() => {
            const text = document.body.innerText;
            const skipped = (text.match(/Skipped/g) || []).length;
            const total = document.querySelectorAll('tr').length - 1;
            if (total > 0 && skipped >= total) throw new Error('All claim checks were skipped!');
        }""")
        
'''

text = text.replace('# Fast-track', replacement + '        # Fast-track')

with open('scripts/final_e2e.py', 'w', encoding='utf-8') as fw:
    fw.write(text)
print('Assertions injected.')
