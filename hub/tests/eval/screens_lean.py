import asyncio, sys
from playwright.async_api import async_playwright
OUT = sys.argv[1]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        errs = []
        async def page(url, w=1440, h=900):
            pg = await b.new_page(viewport={"width": w, "height": h}); pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(url); await pg.wait_for_timeout(2500); return pg
        pg = await page("http://127.0.0.1:7831/#samuel")
        await pg.screenshot(path=f"{OUT}/lean-board.png")
        print("tiles:", await pg.locator(".tile").count(), "| chat button in header:", await pg.locator("#ovT").count(), "| new idea:", await pg.locator("#ideaOpen").count(),
              "| notes:", await pg.locator(".note[data-open]").count(), "| sidebar Chat:", await pg.locator('.side [data-sel="s-overview"]').count())
        await pg.locator('.side [data-sel="s-overview"]').click(); await pg.wait_for_timeout(800); await pg.screenshot(path=f"{OUT}/lean-chat.png")
        print("chat page:", await pg.locator(".chatpage").count(), "| input:", await pg.locator("#ovTa").count())
        await pg.locator('.side [data-sel="s-data"]').click(); await pg.wait_for_timeout(800); await pg.screenshot(path=f"{OUT}/lean-agent.png")
        print("agent page input:", await pg.locator("#ta").count())
        await pg.locator('[data-go="board"]').first.click(); await pg.wait_for_timeout(500)
        t = pg.locator(".tile").first
        if await t.count():
            await t.click(); await pg.wait_for_timeout(800); print("tile opens:", await pg.locator(".ptop h1, .chatpage").first.inner_text())
        await pg.close()
        pg = await page("http://127.0.0.1:7831/?demo=1#samuel"); await pg.wait_for_timeout(6000)
        await pg.screenshot(path=f"{OUT}/lean-demo-board.png")
        if await pg.locator("[data-gochat]").count():
            await pg.locator("[data-gochat]").first.click(); await pg.wait_for_timeout(800); await pg.screenshot(path=f"{OUT}/lean-demo-decision.png")
            print("decision box in chat:", await pg.locator(".decision").count())
        await pg.close()
        pg = await page("http://127.0.0.1:7831/#samuel", 390, 844); await pg.screenshot(path=f"{OUT}/lean-390.png")
        print("sideways scroll at 390:", await pg.evaluate("() => document.documentElement.scrollWidth - innerWidth"))
        print("errors:", errs[:5]); await b.close()
asyncio.run(main())
