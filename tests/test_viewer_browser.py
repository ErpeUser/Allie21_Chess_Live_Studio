"""Browser integration with real DOM/video layout and deterministic fake media/API.

This does not certify Windows capture exclusion or a real display picker.
Set ALLIE_BROWSER_EXECUTABLE when Chromium is not on PATH.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

try:
    import playwright.sync_api as playwright
except ImportError:
    if os.environ.get("ALLIE_REQUIRE_BROWSER_TESTS") == "1":
        raise
    pytest.skip("Playwright is optional outside the browser CI gate", allow_module_level=True)
ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {
    "white_elo": 1800, "black_elo": 2000, "player_side": "white",
    "time_control": "300+0", "ocr_history": False,
    "recognition_max_width": 1280, "recognition_interval_ms": 400,
    "capability_token": "fixture-only", "instance_id": "fixture-instance",
}
FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
STATE = {
    "message": "Ready", "running": True, "recommendations_enabled": True,
    "generation": 1, "history_complete": True, "turn_verified": True,
    "history_source": "fixture", "moves_seen": 0,
    "detection": {"fen": FEN, "frame": [640, 480], "box": [80, 0, 480, 480],
                  "confidence": .99, "orientation": "white"},
    "result": {"fen": FEN, "plan_messages": ["Develop pieces and protect the king."],
               "my_moves": [{"uci": "e2e4"}], "opponent_moves": [],
               "premove": {"uci": "g1f3"},
               "moves": [{"san": "e4", "uci": "e2e4", "probability": .42}],
               "expected_think_time_s": 2.5, "brief": ["A fixture, not a model prediction."]},
}
FAKE_CAPTURE = """
window.captureRequests=[];
window.testStreams=[];
window.makeTestStream=()=>{
  const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
  const context=canvas.getContext('2d');context.fillRect(0,0,640,480);
  const stream=canvas.captureStream(2);
  window.testStreams.push(stream);return stream;
};
if(!navigator.mediaDevices)Object.defineProperty(navigator,'mediaDevices',{value:{}});
navigator.mediaDevices.getDisplayMedia=async options=>{
  window.captureRequests.push(options);
  if(window.testCaptureError)throw new DOMException('Fixture',window.testCaptureError);
  if(window.testPickerPending)return new Promise(resolve=>{window.resolveTestPicker=resolve;});
  return window.makeTestStream();
};
"""


@pytest.fixture
def browser_page():
    with playwright.sync_playwright() as pw:
        executable = os.environ.get("ALLIE_BROWSER_EXECUTABLE") or shutil.which("chromium")
        if not executable and Path(pw.chromium.executable_path).is_file():
            executable = pw.chromium.executable_path
        if not executable and os.environ.get("ALLIE_REQUIRE_BROWSER_TESTS") == "1":
            pytest.fail("CI requires an installed Chromium browser")
        if not executable:
            pytest.skip("Install Playwright Chromium or set ALLIE_BROWSER_EXECUTABLE")
        browser = pw.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"] if os.name == "posix" and os.geteuid() == 0 else [])
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        class Requests:
            def __iter__(self):
                return iter(page.evaluate("window.fixtureRecords || []"))
        requests, errors = Requests(), []
        model = {"available": True, "mode": "normal"}
        html = (ROOT / "viewer/index.html").read_text(encoding="utf-8").replace(
            "__ALLIE_CONFIG__", json.dumps(SETTINGS))
        page.on("pageerror", lambda error: errors.append(str(error)))
        def open_viewer():
            # No navigation or network is needed: exercise the exact production
            # HTML with deterministic in-memory HTTP and capture boundaries.
            page.evaluate("""configuration => {
              window.fixtureConfig=configuration;
              const storage=new Map([['allie-private-overlay', configuration.private_requested ? 'on' : 'off']]);
              Object.defineProperty(window,'localStorage',{configurable:true,value:{
                getItem:key=>storage.get(key)??null,
                setItem:(key,value)=>storage.set(key,String(value))
              }});
              window.fixturePaths=[];window.fixtureRecords=[];
              window.fetch=async (path,options={})=>{
                window.fixturePaths.push(path);
                const json=options.headers?.['Content-Type']==='application/json';
                const data=json?JSON.parse(options.body):null;
                window.fixtureRecords.push([path,data]);
                if(path==='/api/overlay/mode')configuration.mode=data.mode;
                const overlay={mode:configuration.mode,available:configuration.available,
                  capture_excluded:configuration.available,visible:false,
                  state:configuration.available?'ready':'unsupported',reason:'fixture'};
                const body=path==='/health'?{ready:true,instance_id:'fixture-instance',
                  model_loaded:true,stockfish_available:true,overlay}:
                  path.startsWith('/api/overlay/')?overlay:
                  path==='/api/stop'?{running:false,message:'Stopped',recommendations_enabled:true}:
                  path==='/analyze'?configuration.state.result:configuration.state;
                return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
              };
            }""", {**model, "state": STATE})
            page.evaluate("() => {" + FAKE_CAPTURE + "}")
            page.set_content(html, wait_until="load")
        yield page, requests, errors, model, open_viewer
        context.close()
        browser.close()


def test_real_dom_initialization_capture_and_external_bubbles(browser_page):
    page, requests, errors, _, open_viewer = browser_page
    open_viewer()
    page.click("#start")
    page.wait_for_function("document.querySelector('#allieBubble').hidden === false")
    assert not errors
    assert any(path == "/api/start" for path, _ in requests)
    page.wait_for_function("window.fixturePaths.includes('/api/frame')")
    assert any(path == "/api/frame" for path, _ in requests)
    for width in (1440, 850, 420):
        page.set_viewport_size({"width": width, "height": 1000})
        rectangles = page.evaluate("""() => {
          const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();
            return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};};
          return {video:rect('video'),bubble:rect('allieBubble'),hud:rect('hud')};
        }""")
        video = rectangles["video"]
        for name in ("bubble", "hud"):
            rect = rectangles[name]
            assert (rect["left"] >= video["right"] or rect["right"] <= video["left"]
                    or rect["top"] >= video["bottom"] or rect["bottom"] <= video["top"])
    page.click("#stop")
    page.wait_for_function("!document.querySelector('#start').disabled")
    assert page.evaluate("window.testStreams.every(s=>s.getTracks().every(t=>t.readyState==='ended'))")
    assert not errors


def test_private_unavailable_does_not_silently_enable_browser_hints(browser_page):
    page, _, errors, model, open_viewer = browser_page
    model["available"] = False
    model["private_requested"] = True
    open_viewer()
    page.wait_for_function("document.querySelector('#privateOverlayState').textContent==='Nicht verfuegbar'")
    assert page.is_checked("#privateOverlayToggle")
    assert page.is_visible("#retryPrivateOverlay")
    page.click("#start")
    page.wait_for_function("document.querySelector('#screen').style.display==='block'")
    assert page.locator("#arrows line").count() == 0
    assert page.locator("#allieBubble").is_hidden()
    assert page.locator("#hud").is_hidden()
    assert "42.0" not in page.locator("#analysis").inner_text()
    assert page.evaluate("localStorage.getItem('allie-private-overlay')") == "on"
    assert not errors


def test_capture_denial_and_retry_remain_usable(browser_page):
    page, requests, errors, _, open_viewer = browser_page
    open_viewer()
    page.evaluate("window.testCaptureError='NotAllowedError'")
    page.click("#start")
    page.wait_for_function("!document.querySelector('#start').disabled")
    assert not any(path == "/api/start" for path, _ in requests)
    assert "abgelehnt" in page.locator("#status").inner_text()
    page.evaluate("window.testCaptureError=null")
    page.click("#start")
    page.wait_for_function("document.querySelector('#screen').style.display==='block'")
    assert not errors


def test_stop_while_picker_pending_discards_late_stream(browser_page):
    page, requests, errors, _, open_viewer = browser_page
    open_viewer()
    page.evaluate("window.testPickerPending=true")
    page.click("#start")
    page.click("#stop")
    page.evaluate("window.resolveTestPicker(window.makeTestStream())")
    page.wait_for_function("!document.querySelector('#start').disabled")
    assert page.evaluate("window.testStreams[0].getTracks()[0].readyState") == "ended"
    assert not any(path == "/api/start" for path, _ in requests)
    assert not errors


def test_manual_fen_uses_stockfish_not_allie_history_api(browser_page):
    page, requests, errors, _, open_viewer = browser_page
    open_viewer()
    page.locator("#manualDetails > summary").click()
    page.fill("#manual", FEN)
    page.click("#manualGo")
    page.wait_for_function("!document.querySelector('#manualGo').disabled")
    analyses = [data for path, data in requests if path == "/analyze"]
    assert len(analyses) == 1
    assert analyses[0]["analysis_source"] == "stockfish"
    assert analyses[0]["fen"] == FEN
    assert not errors

