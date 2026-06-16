"""Probe: does the live sharedModel.addCell + context.save() path actually work?"""
from playwright.sync_api import expect, sync_playwright
import httpx, json

PORTAL = "http://localhost:5180"
JUP = "http://localhost:8888/jupyter"
HDR = {"Authorization": "token dataplatform"}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1600, "height": 900}).new_page()
    page.on("console", lambda m: m.type == "error" and print("console-error:", m.text[:300]))
    page.goto(f"{PORTAL}/analyst/", wait_until="commit", timeout=90_000)
    expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(timeout=60_000)
    jupyter = page.frame_locator("iframe[title='JupyterLab']")
    expect(jupyter.locator("#jp-MainLogo, .jp-NotebookPanel-toolbar").first).to_be_visible(timeout=90_000)
    page.wait_for_timeout(4000)

    lab = page.locator("iframe[title='JupyterLab']").element_handle().content_frame()
    info = lab.evaluate("""async () => {
        const app = window.jupyterapp;
        if (!app) return {err: 'no app'};
        const out = {cur: app.shell.currentWidget?.context?.path ?? null, widgets: []};
        let panel = null;
        for (const w of app.shell.widgets('main')) {
            out.widgets.push({path: w?.context?.path ?? w?.id, visible: !!w.isVisible});
            if (w?.context?.path?.endsWith('.ipynb') && w?.content?.model && (w.isVisible || !panel)) panel = w;
        }
        if (!panel) return out;
        const sm = panel.content.model.sharedModel;
        out.panelPath = panel.context.path;
        out.addCellType = typeof sm?.addCell;
        out.insertCellType = typeof sm?.insertCell;
        out.cellsBefore = sm?.cells?.length;
        try {
            sm.addCell({cell_type: 'code', source: '# probe-live-insert', metadata: {probe: true}});
            out.cellsAfter = sm.cells.length;
        } catch (e) { out.addErr = String(e); return out; }
        try {
            await panel.context.save();
            out.saved = true;
        } catch (e) { out.saveErr = String(e); }
        return out;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1))
    if info.get("panelPath"):
        r = httpx.get(f"{JUP}/api/contents/{info['panelPath']}", headers=HDR, timeout=10)
        cells = r.json()["content"]["cells"]
        print("disk cells:", len(cells), "| last source:", repr(cells[-1]["source"])[:80])
    browser.close()
