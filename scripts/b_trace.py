import asyncio
from playwright.async_api import async_playwright
import time
import os

SCREENSHOTS_DIR = 'docs/screenshots/evidence_fix'

async def run_e2e():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        c_context = await browser.new_context()
        c_page = await c_context.new_page()
        
        # 2. Claimant files claim
        await c_page.goto('http://localhost:5173/login')
        await c_page.click('text=CLAIMANT PORTAL')
        await c_page.click('button:has-text("Sign in")')
        
        try:
            await c_page.wait_for_selector('a[href="/claim/new"], button:has-text("Start"), button:has-text("File")', timeout=10000)
            try:
                await c_page.click('a[href="/claim/new"]')
            except:
                await c_page.click('button:has-text("Start another claim")')
        except Exception as e:
            await c_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '00_start_claim_failed.png'))
            raise e
        
        # Step 1: select policy
        await c_page.click('text=motor')
        await c_page.click('text=Continue')
        
        # Step 2: details
        await c_page.fill('textarea', 'Window broken by storm')
        await c_page.fill('input[inputmode="decimal"]', '5000')
        await c_page.fill('input[type=date]', '2026-10-04')
        await c_page.click('text=Continue')
        
        # Step 3: Verify Identity
        verify_inputs = await c_page.query_selector_all('input[type=file]')
        if len(verify_inputs) >= 2:
            await verify_inputs[0].set_input_files('web/public/samples/id_card.png')
            await verify_inputs[1].set_input_files('web/public/samples/selfie.jpg')
        await c_page.click('text=Continue')

        # Step 4: Evidence
        # Wait for file inputs
        evidence_inputs = await c_page.query_selector_all('input[type=file]')
        if len(evidence_inputs) >= 4:
            await evidence_inputs[0].set_input_files('web/public/samples/genuine_car.jpg') # full vehicle
            await evidence_inputs[1].set_input_files('web/public/samples/ai_car.jpg') # closeup
            # [2] is number_plate, skip
            await evidence_inputs[3].set_input_files('web/public/samples/tampered_invoice.jpg') # repair estimate
        
        await c_page.click('text=Continue')
        
        # Step 5: review
        checkboxes = await c_page.locator('input[type=checkbox]').all()
        for cb in checkboxes:
            await cb.check()
        
        await c_page.click('button:has-text("Submit claim")')
        
        # Wait for analysis to finish
        print('Waiting 15s for orchestrator to finish...')
        await c_page.wait_for_timeout(15000)
        
        print('PASS: Claimant submitted claim')
        
        # Investigator
        i_context = await browser.new_context()
        i_page = await i_context.new_page()
        await i_page.goto('http://localhost:5173/login')
        await i_page.click('text=INVESTIGATOR CONSOLE')
        await i_page.click('button:has-text("Sign in")')
        await i_page.wait_for_timeout(2000)
        
        async def handle_response(response):
            if '/api/v1/queue' in response.url:
                try:
                    text = await response.text()
                    print('QUEUE RESPONSE:', text[:500])
                except:
                    pass
        i_page.on('response', handle_response)
        
        await i_page.goto('http://localhost:5173/app/queue')
        
        try:
            await i_page.wait_for_selector('text=Open', timeout=15000)
            open_links = await i_page.query_selector_all('text=Open')
            if open_links:
                await open_links[0].click()
                await i_page.wait_for_timeout(4000)
                await i_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '01_result_score.png'))
                
                await i_page.click('button:has-text("Image")')
                await i_page.wait_for_timeout(1000)
                await i_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '02_result_image.png'))
                
                await i_page.click('button:has-text("Document")')
                await i_page.wait_for_timeout(1000)
                await i_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '03_result_document.png'))
                
                await i_page.click('button:has-text("Claim checks")')
                await i_page.wait_for_timeout(1000)
                await i_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '04_result_checks.png'))
                
                await i_page.click('button:has-text("Why this score")')
                await i_page.wait_for_timeout(1000)
                await i_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '05_why_this_score.png'))
                print('PASS: Investigator checked tabs')
        except Exception as e:
            text = await i_page.text_content('body')
            with open(os.path.join(SCREENSHOTS_DIR, 'page_text.txt'), 'w', encoding='utf-8') as f:
                f.write(text or '')
            await i_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, '01_queue_no_open_links.png'))
            print('FAIL: Queue or tabs issue', e)
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run_e2e())
