import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True); pg = await b.new_page(viewport={"width": 1440, "height": 900})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto("http://127.0.0.1:7831/?demo=1#samuel"); await pg.wait_for_timeout(2500)
        r = await pg.evaluate("""() => {
          const now = Date.now()/1000, stages = ["Build","Practice 1","Practice 2","Practice 3","Practice 4","Round 1","Round 1.5","Round 2","Round 2.5","Round 3","Round 3.5","Round 4","Round 4.5","Round 5","Round 5.5","Round 6"];
          S.st.tiles = []; for (let i = 0; i < 300; i++) S.st.tiles.push({id: "t"+i, label: "Item "+i, state: ["in progress","done","failed","testing"][i%4], owner: "s-data", stage: stages[i%16], created: now-i, updated: now-i});
          S.st.props = []; for (let i = 0; i < 200; i++) S.st.props.push({id: "P"+i, kind: "bot", title: "Which bot? v"+i, status: i < 3 ? "needs_call" : "done", decider: "both", bot: "releases/v"+i+".zip", created: now, updated: now, thread: Array.from({length: 60}, (_, j) => ({who: "Hub", at: now, text: "line "+j}))});
          const ov = S.st.overviews["s-overview"] = []; for (let i = 0; i < 40; i++) ov.push({who: i%2 ? "Chat" : "Samuel", at: now, text: "message ".repeat(80)});
          S.openStages = {}; stages.forEach((s) => S.openStages[s] = true);
          const t = []; for (let k = 0; k < 10; k++) { const a = performance.now(); render(); t.push(performance.now() - a); }
          S.page = "chat"; S.ovWho = "samuel"; const c = []; for (let k = 0; k < 10; k++) { const a = performance.now(); render(); c.push(performance.now() - a); }
          t.sort((a,b)=>a-b); c.sort((a,b)=>a-b);
          return {board_median_ms: t[5].toFixed(1), board_max_ms: t[9].toFixed(1), chat_median_ms: c[5].toFixed(1), chat_max_ms: c[9].toFixed(1), tiles_drawn: document.querySelectorAll('.tile').length, json_kb: Math.round(JSON.stringify(S.st).length/1024)};
        }""")
        print(r, "| errors:", errs[:3]); await b.close()
asyncio.run(main())
