from pathlib import Path
import json
import urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parent
with sync_playwright() as p:
    request=p.request.new_context(base_url='http://127.0.0.1:8016')
    health=request.get('/api/health').json()
    assert health['status']=='ready',health
    assert request.post('/api/predict',data={'frames':[],'timestamp':0}).status==422
    assert request.get('/api/media/../../no-file').status==404
    response=request.post('/api/convert',multipart={'file':{'name':'sample-with-audio.mp4','mimeType':'video/mp4','buffer':(ROOT/'sample-with-audio.mp4').read_bytes()}},timeout=120000)
    assert response.ok,response.text()
    media=request.get(response.json()['url'],headers={'Range':'bytes=0-1023'})
    assert media.status==206,media.status
    out=ROOT/'converted-sample.mp4'
    out.write_bytes(request.get(response.json()['url']).body())
    request.dispose()
import subprocess
exe=ROOT.parent/'backend'/'.venv'/'Scripts'/'python.exe'
run=subprocess.run([str(exe),'-c','import imageio_ffmpeg,subprocess,sys; r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-i",sys.argv[1]],capture_output=True,text=True); print(r.stderr)',str(out)],capture_output=True,text=True,check=True)
assert 'Audio: aac' in run.stdout and 'Video: h264' in run.stdout
(ROOT/'service-results.json').write_text(json.dumps({'health':health,'checks':['Invalid clips rejected','Unknown media rejected','FFmpeg converts actual video','Converted file has H.264 video and AAC audio','Byte-range playback returns 206']},indent=2))
print('Service checks passed: inference validation, conversion, audio, byte-range playback.')
