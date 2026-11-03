"""Regression: a real response arriving after playback ends must still save."""
from pathlib import Path
import subprocess,time,json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
exe=ROOT.parent/'backend/.venv/Scripts/python.exe'
ffmpeg=subprocess.check_output([str(exe),'-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],text=True).strip()
clip=ROOT/'short-detection.mp4'
subprocess.run([ffmpeg,'-y','-i',str(ROOT/'sample-with-audio.mp4'),'-t','6','-c','copy',str(clip)],check=True,stderr=subprocess.PIPE)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050})
    page.add_init_script('sessionStorage.setItem("framewatch:settings",JSON.stringify({backend:"",index:0,threshold:0.5,preprocessing:"zero_one",playbackOnly:false}))')
    page.goto('http://127.0.0.1:5186',wait_until='networkidle')
    page.get_by_role('button',name='Continue with Google',exact=True).click()
    page.get_by_role('button',name='Continue to workspace',exact=False).click()
    page.locator('input[type=file]').set_input_files(str(clip))
    page.wait_for_function('document.querySelector("video")?.readyState>=2')
    def delayed_response(route):
        response=route.fetch(timeout=60000)
        time.sleep(4)
        route.fulfill(response=response)
    page.route('**/api/predict',delayed_response)
    page.get_by_role('button',name='Start detection',exact=True).click()
    page.wait_for_selector('.timeline-marker:not(.manual)',timeout=40000)
    assert page.locator('video').evaluate('(v)=>v.ended')
    assert page.get_by_text('Flag saved to timeline',exact=True).is_visible()
    assert 'Class 0:' in page.locator('.detector-result').inner_text()
    assert page.locator('.detector-result button').count()==1
    page.screenshot(path=str(ROOT/'detection-finish.png'),full_page=True)
    result={'passed':['Real inference result is preserved after natural end, despite delayed response','Model flag renders on timeline and in moment list','Last processed timestamp and both raw scores are visible']}
    (ROOT/'detection-finish-results.json').write_text(json.dumps(result,indent=2))
    browser.close()
print(json.dumps(result))
