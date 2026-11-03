from pathlib import Path
import subprocess,threading,json
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
folder=ROOT/'streams'
folder.mkdir(exist_ok=True)
python=ROOT.parent/'backend'/'.venv'/'Scripts'/'python.exe'
code='import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'
ffmpeg=subprocess.check_output([str(python),'-c',code],text=True).strip()
for args in [
 ['-c','copy','-f','hls','-hls_time','4','-hls_list_size','0',str(folder/'test.m3u8')],
 ['-c','copy','-f','dash','-seg_duration','4',str(folder/'test.mpd')],
]:
 subprocess.run([ffmpeg,'-y','-i',str(ROOT/'sample-with-audio.mp4'),*args],cwd=folder,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
class Handler(SimpleHTTPRequestHandler):
 def end_headers(self):
  self.send_header('Access-Control-Allow-Origin','*')
  super().end_headers()
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8036),partial(Handler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(channel='chrome',headless=True)
  page=browser.new_page()
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:print('Browser:',m.text[:250],flush=True) if m.type in ['error','warning'] else None)
  page.on('response',lambda r:print(r.status,r.url,flush=True) if ':8036' in r.url else None)
  page.goto('http://127.0.0.1:5186')
  page.get_by_role('button',name='Continue with Google',exact=True).click()
  page.get_by_role('button',name='Continue to workspace',exact=False).click()
  for path in ['sample-with-audio.mp4','streams/test.m3u8','streams/test.mpd']:
   print('Checking',path,flush=True)
   page.get_by_role('button',name='Add source',exact=True).click()
   page.get_by_label('VIDEO OR STREAM URL',exact=True).fill('http://127.0.0.1:8036/'+path)
   page.get_by_role('button',name='Open source',exact=False).click()
   try:
    page.wait_for_function('document.querySelector("video")?.readyState>=2',timeout=15000)
   except Exception:
    print('Errors:',errors,flush=True)
    print(page.locator('video').evaluate('(v)=>({src:v.src,currentSrc:v.currentSrc,error:v.error?.message,ready:v.readyState})'),flush=True)
    page.screenshot(path=str(ROOT/'stream-error.png'),full_page=True)
    raise
   page.locator('video').evaluate('(v)=>v.play()')
   page.wait_for_function('document.querySelector("video")?.currentTime>0.5')
   assert not page.locator('video').evaluate('(v)=>v.muted')
   results.append(path+' loads and plays, audio unmuted')
  assert not errors,errors
  browser.close()
finally:server.shutdown()
(ROOT/'stream-results.json').write_text(json.dumps({'passed':results,'errors':errors},indent=2))
print(json.dumps(results,indent=2))
