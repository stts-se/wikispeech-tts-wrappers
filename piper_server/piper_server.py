from fastapi import FastAPI

import sys, os
from pathlib import Path

from piper import PiperVoice, SynthesisConfig

# Local import
import tools, config

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from common import release, log

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel # data models for post requests
from dotenv import load_dotenv

from typing import Optional

class Settings:
    model_dir: str
    output_dir: str

input_types = ['mixed','phonemes','tokens','text']
return_types = ['json','wav']
    
global_cfg = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_cfg, vInfo
    json_config = os.getenv("PIPER_CONFIG") # Reads from .env file passed to uvicorn
    if not json_config:
        raise RuntimeError("Config not provided. Start server with --env-file")
    global_cfg = config.load_config(json_config)
    startedAt = release.genStartedAtString()
    vInfo = release.versionInfo("piper",startedAt)
    for v in global_cfg.voices:
        global_cfg.voices[v].validate(fail_on_error=False)

    app.mount("/static", StaticFiles(directory=global_cfg.output_path), name="static")
    # ->  http://127.0.0.1:8000/static/FILENAME.wav    

    yield

app = FastAPI(lifespan=lifespan,swagger_ui_parameters={"tryItOutEnabled": True})

@app.get("/synthesize/sv_vc_m2m_p")
async def synthesize_sv_vc_m2m_p(input_type: str = 'phonemes',
                                     input: str = "jˈⱭ ˈE ˈen g°am`al trˈøt g°ɵb`ə .",
                                     length_scale: Optional[float] = None,
                                     noise_scale: Optional[float] = None,
                                     noise_w_scale: Optional[float] = None):
    return await synthesize_as_get(voice = 'sv_vc_m2m_p',
                                   input_type = input_type,
                                   input = input,
                                   length_scale = length_scale,
                                   noise_scale = noise_scale,
                                   noise_w_scale = noise_w_scale)

@app.get("/synthesize/sv_vc_m2f_p")
async def synthesize_sv_vc_m2f_p(input_type: str = 'mixed',
                                     input: str = "[[ jˈⱭ ˈE ˈen g°am`al trˈøt ]] gumma .",
                                     length_scale: Optional[float] = None,
                                     noise_scale: Optional[float] = None,
                                     noise_w_scale: Optional[float] = None):
    return await synthesize_as_get(voice = 'sv_vc_m2f_p',
                                   input_type = input_type,
                                   input = input,
                                   length_scale = length_scale,
                                   noise_scale = noise_scale,
                                   noise_w_scale = noise_w_scale)

@app.get("/synthesize/en_us_ljspeech")
async def synthesize_en_us_ljspeech(input_type: str = 'mixed',
                               input: str = "hello, my name is lj speech",
                               length_scale: Optional[float] = None,
                               noise_scale: Optional[float] = None,
                               noise_w_scale: Optional[float] = None):
    return await synthesize_as_get(voice = 'en_US-ljspeech-high',
                                   input_type = input_type,
                                   input = input,
                                   length_scale = length_scale,
                                   noise_scale = noise_scale,
                                   noise_w_scale = noise_w_scale)


class SynthRequest(BaseModel):
    voice: str = "en_US-ljspeech-high"
    input_type: str = "tokens"
    input: list = [
        [
            { "orth": "first" },
            { "orth": "sentence" },            
        ],
        [
            { "orth": "hello" },
            { "orth": "my" },
            { "orth": "name"},
            { "orth": "is"},
            { "orth": "lj", "phonemes": "ˈɛlˌdʒeɪ"},
            { "orth": "speech"}
       ],
    ]
    length_scale: float = -1
    noise_scale: float = -1
    noise_w_scale: float = -1
    #speaker_id: int
    return_type: str = 'json'

@app.post("/synthesize/")
async def synthesize_as_post(request: SynthRequest):
    if request.voice not in global_cfg.voices:
        msg = f"No such voice: {request.voice}"
        log.error(msg)
        raise HTTPException(status_code=404, detail=msg)              
    
    log.debug(f"synthesize input: {request}")
    syn_config = SynthesisConfig(
        volume=1.0,
        normalize_audio=False, # use raw audio from voice
        #speaker_id=0, # TODO: look up id from speaker name
    )
    if request.length_scale >= 0:
        syn_config.length_scale=request.length_scale
    if request.noise_scale >= 0:
        syn_config.noise_scale=request.noise_scale  # audio variation
    if request.noise_w_scale >= 0:
        syn_config.noise_w_scale=request.noise_w_scale  # speaking variation
    v = global_cfg.voices[request.voice]
    if not v.loaded:
        v.load(global_cfg.model_paths)
    res = v.synthesize_all(request.input, request.input_type, global_cfg.output_path, syn_config)

    log.debug(f"synthesize_as_post res: {res}")
    
    # return type
    if request.return_type == 'json':
        for i, obj in enumerate(res):
            res[i] = obj
            return res
    elif request.return_type == 'wav':
        if len(res) == 1:
            f = res[0]['audio']
            full_path = os.path.join(global_cfg.output_dir, f)
            return FileResponse(full_path, filename=os.path.basename(f), media_type="audio/wav")
        else:
            msg = f"Cannot use return type {request.return_type} for multiple output objects. Try json instead."
            log.error(msg)
            raise HTTPException(status_code=400, detail=msg)
    else:
        msg = f"Invalid return type: '{request.return_type}'. Use one of the following: {return_types}"
        log.error(msg)
        raise HTTPException(status_code=400, detail=msg)

    
@app.get("/synthesize")
async def synthesize_as_get(voice: str = "en_US-ljspeech-high",
                            input: str = "hello my name is ljspeech with a get request",
                            input_type: str = "mixed",
                            length_scale: Optional[float] = None,
                            noise_scale: Optional[float] = None,
                            noise_w_scale: Optional[float] = None,
                            #sentence_silence: float = 0.0,
                            #speaker_id: str = None,
                            return_type: str = 'json'):
    if voice not in global_cfg.voices:
        msg = f"No such voice: {voice}"
        log.error(msg)
        raise HTTPException(status_code=404, detail=msg)
        
    import re
    input = input.strip()
    inputs = [input] # re.split(r"[.!?]+( +|$)", input)
    while "" in inputs:
        inputs.remove("")
    while " " in inputs:
        inputs.remove(" ")
    if input_type not in input_types:
        msg = f"Invalid input type: '{input_type}'. Use one of the following: {input_types}"
        log.error(msg)
        raise HTTPException(status_code=400, detail=msg)
    res = []
    try:
        syn_config = SynthesisConfig(
            volume=1.0,
            length_scale=length_scale,  # 2.0 = twice as slow
            noise_scale=noise_scale,  # audio variation
            noise_w_scale=noise_w_scale,  # speaking variation
            normalize_audio=False, # use raw audio from voice
            #sentence_silence=sentence_silence,
            #speaker_id=0, # TODO: look up id from speaker name
        )
        v = global_cfg.voices[voice]
        if not v.loaded:
            v.load(global_cfg.model_paths)
        res = v.synthesize_all(inputs, input_type, global_cfg.output_path, syn_config)
                
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail="Internal server error, see server log for details")
        
    # return type
    if return_type == 'json':
        for i, obj in enumerate(res):
            obj['audio'] = f"/static/{os.path.basename(obj['audio'])}"
            res[i] = obj
        return res
    elif return_type == 'wav':
        if len(res) == 1:
            f = res[0]['audio']
            full_path = os.path.join(global_cfg.output_path, f)
            return FileResponse(full_path, filename=os.path.basename(f), media_type="audio/wav")
        else:
            msg = f"Cannot use return type {return_type} for multiple output objects. Try json instead."
            log.error(msg)
            raise HTTPException(status_code=400, detail=msg)
    else:
        msg = f"Invalid return type: '{return_type}'. Use one of the following: {return_types}"
        log.error(msg)
        raise HTTPException(status_code=400, detail=msg)


@app.get("/load")
async def load(voice: str):
    for k,v in global_cfg.voices.items():
        if v.name == voice:
            if v.loaded:
                return f"Voice {v.name} is already loaded"
            else:
                v.load(global_cfg.model_paths)
                return f"Loaded voice {v.name}"
    return f"No such voice: {v.name}"
            
@app.get("/load_all")
async def load_all():
    res = {
        "loaded": [],
        "already_loaded": []        
    }
    for k,v in global_cfg.voices.items():
        if v.loaded:
            res["already_loaded"].append(v.name)
        else:
            v.load(global_cfg.model_paths)
            res["loaded"].append(v.name)
    return res

@app.get("/voices")
async def voices():
    res = []
    for k,v in global_cfg.voices.items():
        # TODO: simple json representation
        res.append(v.as_json())
    return res


@app.get("/ping")
async def ping():
    return HTMLResponse(content="piper", media_type="text")

@app.get('/version')
def version():
    resp = HTMLResponse("\n".join(vInfo), media_type="text")
    resp.headers["Content-type"] = "text/plain"
    return resp
