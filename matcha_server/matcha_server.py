# For usage info, se README.md

import os, sys

from argparse import Namespace

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

# Imports from this repo
import config, tools

# Other imports
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

@app.get("/synthesize/sv_se_hb")
async def synthesize_sv_se_hb(input_type: str = 'phonemes',
                              input: str = "viː tˈɛstar tˈɑːlsyntˌeːs",
                              speaking_rate: float = 1.0):
    return await synthesize(voice = 'sv_se_hb',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate)

@app.get("/synthesize/sv_se_nst")
async def synthesize_sv_se_nst(input_type: str = 'phonemes',
                               input: str = "jˈɑ:g t°ʏkər v°ɛldɪt m°ʏkət ˈɔm ɪtɐlɪˈe:nsk mˈɑ:t .",
                               speaking_rate: float = 1.0,
                               speaker_id: int = 1):
    return await synthesize(voice = 'sv_se_nst',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate,
                            speaker_id = speaker_id)

@app.get("/synthesize/sv_se_nst_STTS-test")
async def synthesize_sv_se_nst(input_type: str = 'mixed',
                               input: str = "så här skickar man in [[bl°and`ad]] input",
                               speaking_rate: float = 1.0):
    return await synthesize(voice = 'sv_se_nst_STTS-test',
                            input_type = input_type,
                            input = input)

@app.get("/synthesize/en_us_vctk")
async def synthesize_en_us_vctk(input_type: str = 'phonemes',
                                input: str = "ðɛɹ mˈʌst biː ɐn ˈeɪndʒəl",
                                speaking_rate: float = 1.0,
                                speaker_id: int = 4):
    return await synthesize(voice = 'en_us_vctk',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate,
                            speaker_id = speaker_id)

@app.get("/synthesize/en_us_ljspeech")
async def synthesize_en_us_ljspeech(input_type: str = 'text',
                                    input: str = "are you an angel",
                                    speaking_rate: float = 1.0):
    return await synthesize(voice = 'en_us_ljspeech',
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
    
                     
#@app.get("/synthesize/{voice}")
@app.get("/synthesize/")
async def synthesize(voice: str = 'sv_se_hb',
                     input_type: str = 'phonemes',
                     #input: str="Vi testar talsyntes. Det är kul.",
                     input: str = "viː tˈɛstar tˈɑːlsyntˌeːs",
                     speaking_rate: float = 1.0,
                     speaker_id: int = None,
                     return_type: str = 'json'):
    if voice not in global_cfg.voices:
        msg = f"No such voice: {voice}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
        
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
            #obj['audio'] = f"/static/{os.path.basename(obj['audio'])}"             
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


          

