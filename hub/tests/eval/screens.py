import asyncio, json, sys
from playwright.async_api import async_playwright
OUT = sys.argv[1]; HUBS = {"samuel": "http://127.0.0.1:7821", "dylan": "http://127.0.0.1:7822"}
R = []
def rec(cid, name, ok, detail=""):
    R.append({"id": cid, "name": name, "ok": bool(ok), "detail": str(detail)[:300]}); print(("PASS " if ok else "FAIL ") + cid, name, "" if ok else detail, flush=True)
OVER = "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth"
async def page(b, url, w=1440, h=900, scheme="light", motion="no-preference"):
    ctx = await b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, reduced_motion=motion, accept_downloads=True)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    await pg.goto(url); await pg.wait_for_timeout(2500); return pg, errs, ctx
async def shot(pg, name): await pg.screenshot(path=f"{OUT}/{name}.png")
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        for who, base in HUBS.items():
            u = f"{base}/#{who}"
            pg, errs, ctx = await page(b, u)
            await shot(pg, f"{who}-01-board")
            rec("Q1", f"{who}: board, no sideways scroll at 1440", await pg.evaluate(OVER) <= 1, await pg.evaluate(OVER))
            rec("Q2", f"{who}: Agents drawer hidden by default", not await pg.locator(".drawer.open, #panel.open").count())
            n_stage = await pg.locator(".stage").count(); rec("N1", f"{who}: board grouped into stages", n_stage >= 1, n_stage)
            # bell
            await pg.click("#bell"); await pg.wait_for_timeout(500); await shot(pg, f"{who}-02-bell")
            await pg.keyboard.press("Escape"); await pg.mouse.click(700, 500); await pg.wait_for_timeout(300)
            # live menu
            if await pg.locator("#liveT").count():
                await pg.click("#liveT"); await pg.wait_for_timeout(500); await shot(pg, f"{who}-03-live")
                rows = await pg.locator("#liveMenu [data-dlbot]").count()
                rec("L1", f"{who}: Live menu lists bots", rows >= 1, rows)
                names = await pg.locator("#liveMenu").inner_text()
                rec("L1n", f"{who}: bot rows are names only (no descriptions)", "eval bot" not in names, names[:200])
                if rows:
                    async with pg.expect_download(timeout=20000) as dl:
                        await pg.locator("#liveMenu [data-dlbot]").first.click()
                    d = await dl.value
                    rec("L2v", f"{who}: clicking a bot downloads its zip", (d.suggested_filename or "").endswith(".zip"), d.suggested_filename)
                await pg.keyboard.press("Escape"); await pg.mouse.click(700, 600); await pg.wait_for_timeout(300)
            else:
                rec("L1", f"{who}: Live menu button exists", False)
            # chat
            if not await pg.locator("#ovTa").count():
                await pg.click("#ovT"); await pg.wait_for_timeout(600)
            await shot(pg, f"{who}-04-chat")
            ff = await pg.evaluate("() => { const e = document.querySelector('#ovBody') || document.body; return getComputedStyle(e).fontFamily }")
            rec("H6", f"{who}: Chat text keeps its own font", "Inter" in ff or "Newsreader" in ff, ff)
            other = "dylan" if who == "samuel" else "samuel"
            chip = pg.locator(f'[data-ovwho="{other}"]')
            if await chip.count():
                await chip.first.click(); await pg.wait_for_timeout(800); await shot(pg, f"{who}-05-other-chat")
                txt = await pg.locator("#ovBody").inner_text() if await pg.locator("#ovBody").count() else ""
                rec("H1v", f"{who}: can open {other}'s Chat", True)
                if who == "samuel":
                    rec("H1w", "samuel sees the line written into Dylan's Chat", "eval ping 42" in txt, txt[-200:])
                await pg.locator(f'[data-ovwho="{who}"]').first.click(); await pg.wait_for_timeout(400)
            else:
                rec("H1v", f"{who}: other person's Chat chip exists", False)
            # staged attachment
            if await pg.locator("#ovFile").count():
                await pg.set_input_files("#ovFile", files=[{"name": "screen.png", "mimeType": "image/png", "buffer": bytes.fromhex("89504e470d0a1a0a") + b"0" * 500}])
                await pg.wait_for_timeout(1500); await shot(pg, f"{who}-06-staged")
                staged = await pg.locator("[data-unstage]").count()
                rec("F1v", f"{who}: chosen file is staged, not sent", staged >= 1, staged)
                if staged:
                    await pg.locator("[data-unstage]").first.click(); await pg.wait_for_timeout(300)
                    rec("F2", f"{who}: staged file can be removed", await pg.locator("[data-unstage]").count() == staged - 1)
            # quick chips
            rec("H3", f"{who}: quick-question chips shown", await pg.locator("[data-q], [data-chip]").count() >= 1)
            # open a note, Esc closes
            note = pg.locator(".note[data-open]").first
            if await note.count():
                await note.focus(); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(900); await shot(pg, f"{who}-07-note")
                opened = await pg.locator("#cvBack").count() > 0
                rec("Q5", f"{who}: Enter opens a focused note", opened)
                rec("Q1n", f"{who}: open note, no sideways scroll", await pg.evaluate(OVER) <= 1, await pg.evaluate(OVER))
                await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
                rec("Q5b", f"{who}: Esc closes the note", await pg.locator("#cvBack").count() == 0)
            # new idea
            if await pg.locator("#ideaOpen").count():
                await pg.click("#ideaOpen"); await pg.wait_for_timeout(300)
                rec("N5v", f"{who}: New idea is one text box", await pg.locator("#ideaBody").count() == 1 and await pg.locator(".newnote input").count() == 0)
                await shot(pg, f"{who}-08-idea"); await pg.click("#ideaX")
            # agents drawer and other side
            if await pg.locator("#sideT").count():
                await pg.click("#sideT"); await pg.wait_for_timeout(600); await shot(pg, f"{who}-09-agents"); await pg.click("#sideT"); await pg.wait_for_timeout(300)
            if await pg.locator("#otherT").count():
                await pg.click("#otherT"); await pg.wait_for_timeout(600); await shot(pg, f"{who}-10-other-side"); await pg.click("#otherT")
            rec("Q1e", f"{who}: no page errors in the main views", not errs, errs[:3])
            await ctx.close()
            # sizes, dark mode, reduced motion
            for w, h, tag in ((1024, 768, "1024"), (390, 844, "390")):
                pg, errs, ctx = await page(b, u, w, h); await shot(pg, f"{who}-11-w{tag}")
                rec("Q1w", f"{who}: no sideways scroll at {tag}px", await pg.evaluate(OVER) <= 1, await pg.evaluate(OVER))
                rec("Q1x", f"{who}: no page errors at {tag}px", not errs, errs[:2]); await ctx.close()
            pg, errs, ctx = await page(b, u, scheme="dark")
            bg = await pg.evaluate("() => getComputedStyle(document.body).backgroundColor"); await shot(pg, f"{who}-12-darkOS")
            rec("Q3", f"{who}: light palette even in OS dark mode", bg not in ("rgb(0, 0, 0)",) and sum(map(int, bg[bg.index('(')+1:bg.index(')')].split(',')[:3])) > 600, bg); await ctx.close()
            pg, errs, ctx = await page(b, u, motion="reduce")
            anim = await pg.evaluate("() => [...document.querySelectorAll('*')].filter(e => { const s = getComputedStyle(e); return s.animationName !== 'none' && s.animationIterationCount === 'infinite' && parseFloat(s.animationDuration) > 0.02 }).length")
            rec("Q4", f"{who}: no endless animations with reduced motion", anim == 0, anim); await ctx.close()
        # demo mode
        pg, errs, ctx = await page(b, HUBS["samuel"] + "/?demo=1#samuel")
        await shot(pg, "demo-01")
        btn = pg.locator("[data-pa], button:has-text('Greenlight')").first
        if await btn.count():
            await btn.click(); await pg.wait_for_timeout(800); await shot(pg, "demo-02-after-greenlight")
        rec("Q6", "demo mode runs without page errors", not errs, errs[:3]); await ctx.close()
        await b.close()
    json.dump(R, open(f"{OUT}/results.json", "w"), indent=1)
    print(f"{sum(r['ok'] for r in R)}/{len(R)} passed")
asyncio.run(main())
