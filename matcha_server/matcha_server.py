# For usage info, se README.md

import os, sys

from argparse import Namespace

# Imports from this repo
import tools

logger = tools.get_logger("matcha_server")

import config

# TODO: default values for args/params


# Other imports
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel # data models for post requests
from dotenv import load_dotenv

load_dotenv()

input_types = ['text','phonemes','mixed']
return_types = ['json','wav']

global_cfg = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_cfg
    json_config = os.getenv("MATCHA_CONFIG") # Reads from .env file passed to uvicorn
    if not json_config:
        raise RuntimeError("Config not provided. Start server with --env-file")
    global_cfg = config.load_config(json_config)
    for v in global_cfg.voices:
        global_cfg.voices[v].validate(fail_on_error=False)

    global paths
    app.mount("/static", StaticFiles(directory=global_cfg.output_path), name="static")
    # ->  http://127.0.0.1:8000/static/FILENAME.wav    

    yield

app = FastAPI(lifespan=lifespan,swagger_ui_parameters={"tryItOutEnabled": True})

# TODO: API-call to show valid symbols

@app.get("/synthesize/sv_se_nst_male1")
async def synthesize_sv_se_nst_male1(input_type: str = 'mixed',
                                     input: str = "så här skickar man in [[bl°and`ad]] input till en manlig röst",
                                     speaking_rate: float = None):
    return await synthesize_as_get(voice = 'sv_se_nst_male1',
                                   input_type = input_type,
                                   input = input)

@app.get("/synthesize/sv_se_nst_female1")
async def synthesize_sv_se_nst_female1(input_type: str = 'mixed',
                                       input: str = "så här skickar man in [[bl°and`ad]] input till en kvinnlig röst",
                                       speaking_rate: float = None):
    return await synthesize_as_get(voice = 'sv_se_nst_female1',
                                   input_type = input_type,
                                   input = input)

@app.get("/synthesize/en_us_vctk")
async def synthesize_en_us_vctk(input_type: str = 'phonemes',
                                input: str = "ðɛɹ mˈʌst biː ɐn ˈeɪndʒəl",
                                speaking_rate: float = None,
                                speaker_id: int = 4):
    return await synthesize_as_get(voice = 'en_us_vctk',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate,
                            speaker_id = speaker_id)

@app.get("/synthesize/en_us_ljspeech")
async def synthesize_en_us_ljspeech(input_type: str = 'text',
                                    input: str = "are you an angel",
                                    speaking_rate: float = None):
    return await synthesize_as_get(voice = 'en_us_ljspeech',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate)
       
@app.get("/voices/")
async def voices():
    global global_cfg
    res = []
    for k,v in global_cfg.voices.items():
        # TODO: simple json representation
        res.append(v.as_json())
    return res

@app.get("/symbol_set/")
async def symbols_set(voice: str):
    global global_cfg
    for k,v in global_cfg.voices.items():
        if v.name == voice:
            return {
                "symbols": "".join(v.symbols),
            }
    msg = f"No such voice: {voice}"
    raise HTTPException(status_code=404, detail=msg)
    

class SynthRequest(BaseModel):
    voice: str = "sv_se_nst_female1"
    input_type: str = "tokens"
    input: list = [
        [
            { "orth": "jag" },
            { "orth": "testar" },
            { "orth": "matcha" },
            { "orth": "med", "phonemes": "mˈEd" },
            { "orth": "post", "phonemes": "pˈəʊst" },
            { "orth": "request", "phonemes": "rɪkwˈest" },
        ],
    ]
    speaking_rate: float | None = 1.0
    speaker_id: int = -1
    return_type: str = 'json'

@app.post("/synthesize/")
async def synthesize_as_post(request: SynthRequest):
    if request.voice not in global_cfg.voices:
        msg = f"No such voice: {request.voice}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)

    logger.debug(f"synthesize input: {request}")

    # remap default values from json
    if request.speaking_rate == 0:
        request.speaking_rate = 1.0
    if request.speaker_id == -1:
        request.speaker_id = None
    params = Namespace(
        speaking_rate = request.speaking_rate,
        speaker_id = request.speaker_id,
    )
    res = global_cfg.voices[request.voice].synthesize_all(request.input, request.input_type, global_cfg.output_path, params)
        

    # return type
    if request.return_type == 'json':
        for i, obj in enumerate(res):
            res[i] = obj
            return res
    elif request.return_type == 'wav':
        if len(res) == 1:
            f = res[0]['audio']
            full_path = os.path.join(global_cfg.output_path, f)
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
async def synthesize_as_get(voice: str = 'sv_se_nst_STTS_test',
                            input_type: str = 'text',
                            input: str="Vi testar talsyntes och det är kul.",
                            #input: str = "viː tˈɛstar tˈɑːlsyntˌeːs",
                            speaking_rate: float = 1.0,
                            speaker_id: int = None,
                            return_type: str = 'json'):
    if voice not in global_cfg.voices:
        msg = f"No such voice: {voice}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)

    logger.debug(f"synthesize input: {input}")
    
    import re
    input = input.strip()
    input = re.sub("  +"," ",input)
    inputs = re.split(r" *[.!?]+(?: +|$)", input)
    while "" in inputs:
        inputs.remove("")
    params = Namespace(
        speaking_rate = speaking_rate,
        speaker = speaker_id,
    )
    global input_types
    if input_type not in input_types:
        msg = f"Invalid input type: '{input_type}'. Use one of the following: {input_types}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)
    try:
        res = global_cfg.voices[voice].synthesize_all(inputs, input_type, global_cfg.output_path, params)
    except RuntimeError as e:
        logger.error(f"Matcha error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error, see server log for details")
        

    # return type
    if return_type == 'json':
        for i, obj in enumerate(res):
            res[i] = obj
            return res
    elif return_type == 'wav':
        if len(res) == 1:
            f = res[0]['audio']
            full_path = os.path.join(global_cfg.output_path, f)
            return FileResponse(full_path, filename=os.path.basename(f), media_type="audio/wav")
        else:
            msg = f"Cannot use return type {return_type} for multiple output objects. Try json instead."
            logger.error(msg)
            raise HTTPException(status_code=400, detail=msg)
    else:
        msg = f"Invalid return type: '{return_type}'. Use one of the following: {return_types}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)


          

