from fastapi import FastAPI

import sys, os
from pathlib import Path

from piper import PiperVoice, SynthesisConfig

# Local import
import tools, config

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel # data models for post requests
from dotenv import load_dotenv

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

from typing import Optional

class Settings:
    model_dir: str
    output_dir: str

input_types = ['mixed','phonemes','tokens','text']
return_types = ['json','wav']
    
global_cfg = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_cfg
    json_config = os.getenv("PIPER_CONFIG") # Reads from .env file passed to uvicorn
    if not json_config:
        raise RuntimeError("Config not provided. Start server with --env-file")
    global_cfg = config.load_config(json_config)
    for v in global_cfg.voices:
        global_cfg.voices[v].validate(fail_on_error=False)

    app.mount("/static", StaticFiles(directory=global_cfg.output_path), name="static")
    # ->  http://127.0.0.1:8000/static/FILENAME.wav    

    yield

app = FastAPI(lifespan=lifespan,swagger_ui_parameters={"tryItOutEnabled": True})

@app.get("/synthesize/sv_se_nst_male1")
async def synthesize_sv_se_nst_male1(input_type: str = 'phonemes',
                                     input: str = "jˈⱭ ˈE ˈen g°am`al trˈøt g°ɵb`ə .",
                                     length_scale: Optional[float] = None,
                                     noise_scale: Optional[float] = None,
                                     noise_w_scale: Optional[float] = None):
    return await synthesize_as_get(voice = 'sv_se_nst_male1_p',
                                   input_type = input_type,
                                   input = input,
                                   length_scale = length_scale,
                                   noise_scale = noise_scale,
                                   noise_w_scale = noise_w_scale)

@app.get("/synthesize/en_us_bryce")
async def synthesize_en_us_bryce(input_type: str = 'mixed',
                               input: str = "hello, my name is bryce",
                               length_scale: Optional[float] = None,
                               noise_scale: Optional[float] = None,
                               noise_w_scale: Optional[float] = None):
    return await synthesize_as_get(voice = 'en_US-bryce-medium',
                                   input_type = input_type,
                                   input = input,
                                   length_scale = length_scale,
                                   noise_scale = noise_scale,
                                   noise_w_scale = noise_w_scale)

@app.get("/synthesize/ar_jo_kareem")
async def synthesize_ar_jo_kareem(input_type: str = 'phonemes',
                                  input: str = "wikibˈiːdia alʕarabˈiːa",
                                  length_scale: Optional[float] = None,
                                  noise_scale: Optional[float] = None,
                                  noise_w_scale: Optional[float] = None):
    return await synthesize_as_get(voice = 'ar_JO-kareem-medium',
                                   input_type = input_type,
                                   input = input,
                                   length_scale = length_scale,
                                   noise_scale = noise_scale,
                                   noise_w_scale = noise_w_scale)

class SynthRequest(BaseModel):
    voice: str = "en_US-bryce-medium"
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
            { "orth": "bryce", "phonemes": "brˈɪs" },
            { "orth": "with"} ,
            { "orth": "a" },
            { "orth": "post" },
            { "orth": "request" },            
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
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)              
    
    logger.debug(f"synthesize input: {request}")
    syn_config = SynthesisConfig(
        volume=1.0,
        normalize_audio=False, # use raw audio from voice
        #speaker_id=0, # TODO: look up id from speaker name
    )
    if request.length_scale >= 0:
        syn_config.length_scale=request.length_scale
    if request.noise_scale >= 0:
        syn_config.noise_scale=request.noise_scale,  # audio variation
    if request.noise_w_scale >= 0:
        syn_config.noise_w_scale=request.noise_w_scale,  # speaking variation
    v = global_cfg.voices[request.voice]
    if not v.loaded:
        v.load(global_cfg.model_paths)
    res = v.synthesize_all(request.input, request.input_type, global_cfg.output_path, syn_config)

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
            logger.error(msg)
            raise HTTPException(status_code=400, detail=msg)
    else:
        msg = f"Invalid return type: '{request.return_type}'. Use one of the following: {return_types}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)

    
@app.get("/synthesize/")
async def synthesize_as_get(voice: str = "en_US-bryce-medium",
                            input: str = "hello my name is bryce with a get request",
                            input_type: str = "mixed",
                            length_scale: Optional[float] = None,
                            noise_scale: Optional[float] = None,
                            noise_w_scale: Optional[float] = None,
                            #sentence_silence: float = 0.0,
                            #speaker_id: str = None,
                            return_type: str = 'json'):
    if voice not in global_cfg.voices:
        msg = f"No such voice: {voice}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
        
    import re
    input = input.strip()
    inputs = re.split(r"[.!?]+( +|$)", input)
    while "" in inputs:
        inputs.remove("")
    while " " in inputs:
        inputs.remove(" ")
    if input_type not in input_types:
        msg = f"Invalid input type: '{input_type}'. Use one of the following: {input_types}"
        logger.error(msg)
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
            return FileResponse(f, filename=os.path.basename(f), media_type="audio/wav")
        else:
            msg = f"Cannot use return type {return_type} for multiple output objects. Try json instead."
            logger.error(msg)
            raise HTTPException(status_code=400, detail=msg)
    else:
        msg = f"Invalid return type: '{return_type}'. Use one of the following: {return_types}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)


@app.get("/voices/")
async def voices():
    res = []
    for k,v in global_cfg.voices.items():
        # TODO: simple json representation
        res.append(v.as_json())
    return res
