"""Probe what's exposed on the iframe's lab window."""
from playwright.sync_api import sync_playwright, expect

PORTAL_URL = "http://localhost:5180"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1600, "height": 900})
    page = ctx.new_page()
    page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90_000)
    expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(timeout=60_000)

    jupyter = page.frame_locator("iframe[title='JupyterLab']")
    expect(jupyter.locator("#jp-MainLogo, .jp-NotebookPanel-toolbar").first).to_be_visible(timeout=90_000)
    page.wait_for_timeout(3000)

    iframe_el = page.locator("iframe[title='JupyterLab']").element_handle()
    frame = iframe_el.content_frame()
    info = frame.evaluate("""() => {
        const out = {keys: [], commands: false, app: false, exposed: []};
        for (const k of Object.keys(window)) {
            if (/jupyter|lab|app|JL/i.test(k)) out.keys.push(k);
        }
        try { out.exposed.push('jupyterapp:' + (typeof window.jupyterapp)); } catch(e){}
        try { out.exposed.push('JupyterLab:' + (typeof window.JupyterLab)); } catch(e){}
        try { out.exposed.push('app:' + (typeof window.app)); } catch(e){}
        const cmd = window?.jupyterapp?.commands;
        out.commands = !!cmd;
        if (cmd) { try { out.commandsList = cmd.listCommands().slice(0,5); } catch(e){ out.commandsErr = String(e); } }
        return out;
    }""")
    print(info)
    ctx.close()
    browser.close()
