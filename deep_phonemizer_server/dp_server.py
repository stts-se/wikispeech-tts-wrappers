# For usage info, se README.md

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from dp.phonemizer import Phonemizer
from dotenv import load_dotenv
import json

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from common import phn_mapper, io, release

load_dotenv()

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
@dataclass
class Model:
    name: str
    path: str
    deep_phonemizer: object
    lang: str
    

json_config = os.getenv("DP_CONFIG") # Reads from .env file passed to uvicorn
if not json_config:
        raise RuntimeError("Config not provided. Start server with --env-file")

phoners={}
mappers={}

def load_config():
    with open(json_config, 'r') as file:
        data = json.load(file)
        model_paths = [os.path.expandvars(x) for x in data['model_paths']]
        for model in data['models']:
            name = model['name']
            enabled = model['enabled']
            if not enabled:
                continue
            model_file = model['model']
            lang = model['lang']
            if 'maptable' in model:
                maptable=model['maptable']
                f = io.find_file(maptable,model_paths)
                if f is None:
                    raise IOError(f"Could not find {maptable} in {model_paths}")
                mapper=phn_mapper.PhnMapper("",f)
                mappers[name] = mapper
                
            path = io.find_file(model_file,model_paths)
            if path is None:
                raise IOError(f"Failed to find model {model_file}")
            dp = Phonemizer.from_checkpoint(path)
            phoner = Model(name, path, dp, lang)
            phoners[name] = phoner
            

    
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vInfo
    startedAt = release.genStartedAtString()
    vInfo = release.versionInfo("deep_phonemizer",startedAt)
    load_config()
    yield

app = FastAPI(lifespan=lifespan,swagger_ui_parameters={"tryItOutEnabled": True})

# temporary workaround for Swedish due to small training data set
def sv_put_back_length(trans: str) -> str:
    return trans.replace("I", "iː").replace("Y", "yː").replace("E", "eː").replace("Ɛ", "ɛː").replace("Æ", "æː").replace("Ø", "øː").replace("Œ", "ɶː").replace("U", "uː").replace("O", "oː").replace("Ʉ", "ʉː").replace("Ʊ", "ʊː").replace("Ɑ", "ɑː").replace("A", "aː").replace('°', '"') # NB: last one changes tone 2 main stress

def post_proc(lang, name, trans):
    if name in mappers:
        return mappers[name].convert_trans(trans)[0]
    else:
        return trans
    #'sv': sv_put_back_length,
    #'swe': sv_put_back_length

#def no_postproc(trans: str) -> str:
#    return trans

import re
@app.get("/phonemize/sv_se_braxen_full_sv")
async def phonemize_sv(text = "jag kan ge dig svenska fonem"):
    return await phonemize("sv_se_braxen_full_sv", text)

@app.get("/phonemize/sv_se_braxen_full_langs")
async def phonemize_sv_langs(text = "hejsan en français", lang = "fre"):
    return await phonemize("sv_se_braxen_full_langs", text, lang)

@app.get("/phonemize/en_us_cmudict")
async def phonemize_en_us(text = "this model does not have word stress at all"):
    return await phonemize("en_us_cmudict", text)

@app.get("/phonemize/{model_name}/{text}")
async def phonemize(model_name: str, text: str, lang: str=""):
    if not model_name in phoners:
        msg = f"No such model: {model_name}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    phoner = phoners[model_name]
    words = re.split(r'[," ]+', text.replace(".", ""))
    if lang == "":
        lang = phoner.lang
    phonemes = [{'g': w, 'p': post_proc(phoner.lang, model_name, phoner.deep_phonemizer(w.lower(), lang=lang))} for w in words if w != ""]
    return {
        'name': phoner.name,
        'lang': lang,
        'phonemes': phonemes
    }

@app.get("/models")
async def models():
    res = []
    for k,v in phoners.items():
        res.append({
            'name': v.name,
            'lang': v.lang,
            'path': v.path
        })
    return res


@app.get("/ping")
async def ping():
    return HTMLResponse(content="deep_phonemizer", media_type="text")

@app.get('/version')
def version():
    resp = HTMLResponse("\n".join(vInfo), media_type="text")
    resp.headers["Content-type"] = "text/plain"
    return resp
