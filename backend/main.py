"""Local inference bridge for the supplied 16-frame MoBiLSTM model.

No videos or detections are stored by inference. Conversion uploads expire after
one hour. Class labels and preprocessing were absent from the supplied artifact.
"""
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
import base64
import io
import os
import secrets
import shutil
import tempfile
import time
import threading

import numpy as np
from PIL import Image
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT=Path(__file__).parent
RUNTIME=ROOT/'runtime'
RUNTIME.mkdir(exist_ok=True)
model=None
model_error=None
ready=threading.Event()
inference_lock=threading.Lock()
converting=asyncio.Semaphore(1)

def load_model():
    global model,model_error
    try:
        os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
        import keras
        model=keras.models.load_model(ROOT/'models'/'mobilstm.keras',compile=False,safe_mode=True)
        model(np.zeros((1,16,64,64,3),dtype=np.float32),training=False)
    except Exception as error:
        model_error=str(error)
    finally:
        ready.set()

def expire_uploads():
    cutoff=time.time()-3600
    for file in RUNTIME.iterdir():
        if file.is_file() and file.stat().st_mtime<cutoff:
            file.unlink(missing_ok=True)

@asynccontextmanager
async def lifespan(app):
    expire_uploads()
    threading.Thread(target=load_model,daemon=True).start()
    yield

app=FastAPI(title='Framewatch inference',lifespan=lifespan)
origins=os.environ.get('FRONTEND_ORIGINS','http://127.0.0.1:5186,http://localhost:5186').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.get('/api/health')
def health():
    return {'status':'ready' if model is not None else 'error' if ready.is_set() else 'loading','model':'MoBiLSTM / MobileNetV2 + BiLSTM','input_shape':[16,64,64,3],'class_labels_verified':False,'preprocessing_verified':False,'error':model_error}

class Clip(BaseModel):
    frames:list[str]=Field(min_length=16,max_length=16)
    timestamp:float=Field(ge=0)
    preprocessing:str='zero_one'
    anomaly_index:int=Field(default=1,ge=0,le=1)

@app.post('/api/predict')
def predict(clip:Clip):
    if model is None:
        raise HTTPException(503,'Model failed to load.' if model_error else 'The model is still loading. Try again shortly.')
    if clip.preprocessing not in ['zero_one','minus_one_one','raw']:
        raise HTTPException(422,'Unknown preprocessing profile.')
    try:
        frames=[]
        for frame in clip.frames:
            if len(frame)>50000: raise ValueError('Frame payload exceeds limit')
            data=base64.b64decode(frame.split(',')[-1],validate=True)
            image=Image.open(io.BytesIO(data))
            if image.width>256 or image.height>256: raise ValueError('Frames must be at most 256 pixels per side')
            frames.append(np.asarray(image.convert('RGB').resize((64,64)),dtype=np.float32))
        array=np.stack(frames)[None,...]
    except Exception:
        raise HTTPException(422,'Provide 16 valid base64-encoded small RGB images.')
    if clip.preprocessing=='zero_one': array/=255.0
    elif clip.preprocessing=='minus_one_one': array=array/127.5-1
    with inference_lock:
        result=np.asarray(model(array,training=False))[0]
    return {'timestamp':clip.timestamp,'scores':[float(x) for x in result],'anomaly_score':float(result[clip.anomaly_index]),'anomaly_index':clip.anomaly_index,'mapping_verified':False}

@app.post('/api/convert')
async def convert(file:UploadFile):
    """Convert browser-incompatible local containers to H.264/AAC MP4."""
    import imageio_ffmpeg
    expire_uploads()
    key=secrets.token_hex(16)
    source=RUNTIME/(key+'.input')
    output=RUNTIME/(key+'.mp4')
    try:
        total=0
        with source.open('wb') as target:
            while chunk:=await file.read(1024*1024):
                total+=len(chunk)
                if total>1024*1024*1024: raise HTTPException(413,'Conversion supports files up to 1 GB.')
                target.write(chunk)
        async with converting:
            process=await asyncio.create_subprocess_exec(imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-y','-i',str(source),'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE)
            try:
                _,err=await asyncio.wait_for(process.communicate(),timeout=600)
            except asyncio.TimeoutError:
                process.kill();await process.wait()
                raise HTTPException(408,'Conversion timed out. Try a shorter clip.')
            if process.returncode:
                output.unlink(missing_ok=True)
                raise HTTPException(422,'This file could not be decoded as video.')
        return {'url':'/api/media/'+key,'expires_in':3600}
    finally:
        source.unlink(missing_ok=True)
        await file.close()

@app.get('/api/media/{key}')
def media(key:str):
    if len(key)!=32 or any(c not in '0123456789abcdef' for c in key): raise HTTPException(404)
    path=RUNTIME/(key+'.mp4')
    if not path.exists() or time.time()-path.stat().st_mtime>3600:
        path.unlink(missing_ok=True);raise HTTPException(404,'The converted video has expired.')
    return FileResponse(path,media_type='video/mp4')
