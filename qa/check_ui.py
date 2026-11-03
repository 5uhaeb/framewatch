from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parent
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':1512,'height':1000},device_scale_factor=1)
    page=context.new_page()
    errors=[]
    predictions=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:5186',wait_until='networkidle')
    assert page.locator('html').evaluate('(e)=>e.classList.contains("dark")')
    page.screenshot(path=str(ROOT/'login.png'),full_page=True)
    page.get_by_label('EMAIL',exact=True).fill('xyz@gmail.com')
    page.get_by_label('PASSWORD',exact=True).fill('wrong-password')
    page.get_by_role('button',name='Sign in',exact=True).click()
    assert page.get_by_role('alert').is_visible()
    page.get_by_label('PASSWORD',exact=True).fill('12345678')
    page.get_by_role('button',name='Sign in',exact=True).click()
    page.get_by_role('heading',name='Keep an eye on').wait_for()
    page.screenshot(path=str(ROOT/'studio.png'),full_page=True)
    results.append('Dark default, wrong password feedback, demo password sign-in')
    page.locator('input[type=file]').set_input_files(str(ROOT/'sample-with-audio.mp4'))
    page.wait_for_function('document.querySelector("video")?.readyState >= 2')
    assert page.locator('video').evaluate('(v)=>v.muted') is False
    with page.expect_response(lambda r:'/api/predict' in r.url and r.ok,timeout=45000) as pending:
        page.get_by_role('button',name='Start detection',exact=True).click()
    predictions.append(pending.value.json())
    page.wait_for_function('document.querySelector(".stats-strip > div:nth-child(2) strong")?.textContent !== "00"',timeout=45000)
    assert predictions and len(predictions[0]['scores'])==2
    results.append('Local file with unmuted audio; real model inference returns two scores')
    page.get_by_role('button',name='Stop detection',exact=True).click()
    page.get_by_role('button',name='Mark moment',exact=True).click()
    assert page.get_by_role('button',name='Review marker at',exact=False).count()>=1
    page.screenshot(path=str(ROOT/'video-review.png'),full_page=True)
    source_cache=page.evaluate('Object.keys(sessionStorage).filter(k=>k.startsWith("framewatch:events:"))')
    assert source_cache
    page.reload(wait_until='networkidle')
    page.locator('input[type=file]').set_input_files(str(ROOT/'sample-with-audio.mp4'))
    page.wait_for_function('document.querySelector("video")?.readyState >= 2')
    assert page.get_by_role('button',name='Review marker at',exact=False).count()>=1
    page.get_by_role('button',name='Review marker at',exact=False).last.click()
    page.get_by_role('button',name='Clear',exact=True).click()
    page.get_by_role('button',name='Clear markers',exact=True).click()
    assert page.get_by_role('button',name='Review marker at',exact=False).count()==0
    results.append('Manual marker, cached restore after refresh, timestamp seek, clear confirmation')
    page.get_by_role('button',name='Model settings',exact=True).click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_label('FLAGGED CLASS',exact=True).select_option(str(max(range(2),key=lambda i:predictions[0]['scores'][i])))
    dialog.get_by_label('FLAG THRESHOLD',exact=False).fill('0.5')
    dialog.get_by_role('button',name='Save settings',exact=True).click()
    page.get_by_role('button',name='Start detection',exact=True).click()
    page.wait_for_selector('.timeline-marker:not(.manual)',timeout=45000)
    page.get_by_role('button',name='Stop detection',exact=True).click()
    assert page.get_by_text('Possible anomaly',exact=True).count()>=1
    page.screenshot(path=str(ROOT/'model-markers.png'),full_page=True)
    results.append('Actual model-generated marker with adjustable class/threshold and temporary storage')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(ROOT/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('button',name='Light',exact=True).click()
    assert not page.locator('html').evaluate('(e)=>e.classList.contains("dark")')
    results.append('Responsive 390px layout without horizontal overflow; working light theme')
    assert not errors,errors
    (ROOT/'ui-results.json').write_text(json.dumps({'passed':results,'predictions':predictions,'page_errors':errors},indent=2))
    browser.close()
print(json.dumps(results,indent=2))
