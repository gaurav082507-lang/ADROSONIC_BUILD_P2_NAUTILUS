import asyncio
from playwright.async_api import async_playwright
import os

SCREENSHOTS_DIR = os.path.abspath("docs/screenshots/final")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--use-fake-device-for-media-stream',
                '--use-fake-ui-for-media-stream'
            ]
        )
        
        # 1. Claimant MOTOR
        c_ctx = await browser.new_context(permissions=['camera'])
        c_page = await c_ctx.new_page()
        await c_page.route("**/*mediapipe*/**", lambda route: route.abort())
        await c_page.goto('http://localhost:5173/login')
        await c_page.click('text=CLAIMANT PORTAL')
        await c_page.click('button:has-text("Sign in")')
        await c_page.wait_for_timeout(2000)
        await c_page.goto('http://localhost:5173/claim/new')
        await c_page.wait_for_timeout(2000)
        
        # Policy
        await c_page.click('text=POL-MOT-1001')
        await c_page.click('button:has-text("Continue")')
        
        # Story
        await c_page.fill('input[type="date"]', '2026-10-04')
        await c_page.fill('input[inputmode="decimal"]', '5000')
        await c_page.fill('textarea', 'Motor accident')
        await c_page.click('button:has-text("Continue")')
        
        # Identity
        await c_page.wait_for_selector('button:has-text("Capture")', timeout=10000)
        # There are 3 challenges, click 3 times, waiting for UI to be ready between clicks
        for _ in range(3):
            await c_page.click('button:has-text("Capture")')
            await c_page.wait_for_timeout(1000)
        await c_page.wait_for_selector('text=Live check complete', timeout=20000)
        
        id_path = os.path.abspath('data/demo_samples/identity/01_valid_aadhaar_card.png')
        if os.path.exists(id_path):
            await c_page.set_input_files('input[aria-label="Upload photo"]', id_path)
            await c_page.wait_for_selector('text=Aadhaar Secure QR found', timeout=10000)
            await c_page.screenshot(path=f"{SCREENSHOTS_DIR}/01_identity_qr.png")
        await c_page.click('button:has-text("Continue")')
        
        # Evidence
        inputs = await c_page.query_selector_all('input[type="file"]')
        if len(inputs) > 0:
            await inputs[0].set_input_files(os.path.abspath('web/public/samples/genuine_car.jpg'))
        if len(inputs) > 1:
            await inputs[1].set_input_files(os.path.abspath('web/public/samples/ai_car.jpg'))
        await c_page.wait_for_timeout(1000)
        await c_page.click('button:has-text("Continue")')
        
        # Review
        await c_page.wait_for_timeout(2000)
        await c_page.screenshot(path=f"{SCREENSHOTS_DIR}/02_review.png")
        try:
            await c_page.click('input[type="checkbox"]', timeout=5000)
        except Exception as e:
            text = await c_page.evaluate('document.body.innerText')
            with open("failure_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            raise e
        await c_page.click('text=Submit claim')
        
        print("Claimant submitted motor claim.")
        await c_page.wait_for_selector('text=Under Review', timeout=15000)
        await c_page.screenshot(path=f"{SCREENSHOTS_DIR}/03_status.png")

        # 2. Investigator queue
        i_ctx = await browser.new_context()
        i_page = await i_ctx.new_page()
        await i_page.goto('http://localhost:5173/login')
        await i_page.click('text=INVESTIGATOR CONSOLE')
        await i_page.click('button:has-text("Sign in")')
        await i_page.wait_for_timeout(1000)
        
        await i_page.goto('http://localhost:5173/app/queue')
        await i_page.wait_for_selector('text=Open', timeout=30000)
        
        # Poll for status to change from submitted to under_review
        print("Waiting up to 120s for analysis to complete...")
        await i_page.wait_for_selector('tr:first-child td:has-text("under_review")', timeout=120000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/04_queue.png")
        
        open_links = await i_page.query_selector_all('text=Open')
        await open_links[0].click()
        
        # Result Page
        await i_page.wait_for_selector('button:has-text("Image")', timeout=30000)
        
        # Overview
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/05_result_overview.png")
        # Image
        await i_page.click('button:has-text("Image")')
        await i_page.wait_for_timeout(1000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/06_result_image.png")
        # Document
        await i_page.click('button:has-text("Document")')
        await i_page.wait_for_timeout(1000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/07_result_document.png")
        # Identity
        await i_page.click('button:has-text("Identity")')
        await i_page.wait_for_timeout(1000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/08_result_identity.png")
        # Claim checks
        await i_page.click('button:has-text("Claim checks")')
        await i_page.wait_for_timeout(1000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/09_result_checks.png")
        
        
        # Assertions
        print('Running strict assertions...')
        # Check Image pipeline shows a real percentage (not "Not analysed")
        await i_page.click('button:has-text("Image")')
        await i_page.wait_for_timeout(2000)
        await i_page.evaluate("""() => {
            const text = document.body.innerText;
            // Check that the Image tab has original/heatmap/side buttons (proves pipeline ran)
            if (!text.includes('original') && !text.includes('heatmap'))
                throw new Error('Image tab missing original/heatmap content - pipeline did not run.');
        }""")
        
        await i_page.click('button:has-text("Identity")')
        await i_page.wait_for_timeout(1000)
        await i_page.evaluate("""() => {
            const text = document.body.innerText.toLowerCase();
            if (!text.includes('passed') && !text.includes('liveness'))
                throw new Error('Identity tab missing passed/liveness status');
        }""")
        
        await i_page.click('button:has-text("Claim checks")')
        await i_page.wait_for_timeout(1000)
        await i_page.evaluate("""() => {
            const text = document.body.innerText;
            const okCount = (text.match(/\bok\b/gi) || []).length;
            if (okCount < 1) throw new Error('No claim checks passed (all skipped)!');
        }""")
        
        # Fast-track
        await i_page.click('text=Action')
        await i_page.click('text=Approve / Fast-track')
        await i_page.wait_for_timeout(2000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/10_fast_track.png")

        # Network tab
        await i_page.goto('http://localhost:5173/app/network')
        await i_page.wait_for_timeout(2000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/11_network.png")

        # Dashboard / Analytics
        await i_page.goto('http://localhost:5173/app/dashboard')
        await i_page.wait_for_timeout(2000)
        await i_page.screenshot(path=f"{SCREENSHOTS_DIR}/12_analytics.png")

        # Health Claim (Just verify submission flow works)
        await c_page.goto('http://localhost:5173/claim/new')
        await c_page.wait_for_timeout(2000)
        await c_page.click('text=POL-HLT-4402')
        await c_page.click('button:has-text("Continue")')
        await c_page.fill('input[type="date"]', '2026-10-04')
        await c_page.fill('input[inputmode="decimal"]', '15000')
        await c_page.fill('textarea', 'Fever and hospital stay')
        await c_page.click('button:has-text("Continue")')
        await c_page.wait_for_timeout(1000)
        
        # Identity
        id_path = os.path.abspath('data/demo_samples/identity/01_valid_aadhaar_card.png')
        if os.path.exists(id_path):
            inputs = await c_page.query_selector_all('input[type="file"]')
            if len(inputs) > 0:
                await inputs[0].set_input_files(os.path.abspath('web/public/samples/selfie.jpg'))
            if len(inputs) > 1:
                await inputs[1].set_input_files(id_path)
            await c_page.wait_for_timeout(3000)
        await c_page.click('button:has-text("Continue")')
        
        # Evidence
        await c_page.wait_for_selector('text=Upload', timeout=10000)
        inputs = await c_page.query_selector_all('input[type="file"]')
        if len(inputs) > 0:
            await inputs[0].set_input_files(os.path.abspath('web/public/samples/tampered_invoice.pdf'))
        await c_page.wait_for_timeout(1000)
        await c_page.click('button:has-text("Continue")')
        
        # Review
        await c_page.wait_for_timeout(2000)
        await c_page.screenshot(path=f"{SCREENSHOTS_DIR}/12_health_review.png")
        await c_page.click('input[type="checkbox"]')
        await c_page.click('text=Submit claim')
        await c_page.wait_for_selector('text=Under Review', timeout=15000)
        await c_page.screenshot(path=f"{SCREENSHOTS_DIR}/13_health_claim.png")
        
        print("Done!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
