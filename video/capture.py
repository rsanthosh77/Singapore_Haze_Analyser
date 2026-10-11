import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent / 'assets'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        page = await browser.new_page(viewport={'width':1600,'height':1000}, device_scale_factor=1)
        await page.goto('http://127.0.0.1:8502', wait_until='networkidle')
        await page.get_by_role('heading',name='What the PSI indicates').wait_for()
        await page.wait_for_timeout(2000)
        async def capture(name, target=None):
            if target:
                await target.scroll_into_view_if_needed()
            await page.wait_for_timeout(700)
            await page.screenshot(path=str(OUT/f'{name}.png'))
        await capture('overview')
        await capture('trend',page.locator('[data-testid="stPlotlyChart"]:visible').first)
        await page.get_by_text('Daily averages',exact=True).click()
        await capture('daily',page.locator('[data-testid="stPlotlyChart"]:visible').first)
        await capture('regions',page.get_by_role('heading',name='Daily regional pattern'))
        await page.get_by_role('tab',name='Polyclinic association').click()
        await capture('association',page.get_by_role('heading',name='Does regional PSI move with ARI visits?'))
        charts = page.locator('[data-testid="stPlotlyChart"]:visible')
        await capture('scatter',charts.nth(1))
        await capture('audit',page.get_by_role('heading',name='Week alignment audit'))
        await page.get_by_role('tab',name='Data & methodology').click()
        await capture('method',page.get_by_role('heading',name='Coverage and provenance'))
        await browser.close()

asyncio.run(main())
