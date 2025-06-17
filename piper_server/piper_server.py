from fastapi import FastAPI

import sys, os
from pathlib import Path

from piper import PiperVoice

# Local import
import wrapper
import piper_utils

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

from typing import Optional

class Settings:
    model_dir: str
    output_dir: str

input_types = ['text','phonemes']
return_types = ['json','wav']
    
settings = Settings()
synths = {}
def load_config():
    global settings
    # Reads from .env file passed to uvicorn
    settings.model_dir = create_path(os.getenv("PIPER_MODEL_DIR"))
    settings.output_dir = create_path(os.getenv("PIPER_OUTPUT_DIR"), create=True)
    clear_audio_on_startup = os.getenv("PIPER_CLEAR_AUDIO_ON_STARTUP")
    if clear_audio_on_startup == 'true' or clear_audio_on_startup == 'True':
        clear_audio_on_startup = True
    
    for f in os.listdir(settings.model_dir):
        if f.endswith("onnx"):
            onnx = os.path.join(settings.model_dir, f)
            config = None # explicit path to config file
            cuda = False # gpu
            voice = wrapper.Voice(PiperVoice.load(onnx, config, cuda))
            voice.name = Path(onnx).stem
            synths[voice.name] = voice
            logger.info(f"Loaded voice {voice.name}")

    if clear_audio_on_startup == True:
        clear_audio(settings.output_dir)
    logger.info(f"Loaded config")
    
demo_text = {
    "en_US-norman-medium": "I see trees outside my window",
    "en_US-bryce-medium": "I don't see any trees",
    "sv_SE-nst-medium": "Jag är en gammal trött gubbe",
    "ar_JO-kareem-medium": "ويكيبيديا العربية"
}

demo_phonemes = {
    #"en_US-norman-medium": "I see trees outside my window",
    #"en_US-bryce-medium": "I don't see any trees",
    "sv_SE-nst-medium": ["jɑːɡ ɛːr ɛn ɡˈamal trˈœt ɡˈɵbə"]
    #"ar_JO-kareem-medium": "ويكيبيديا العربية"
}

def clear_audio(audio_path):
    logger.info(f"Clearing audio set to true")
    n=0
    for fn in os.listdir(audio_path):
        file_path = os.path.join(audio_path, fn)
        if os.path.isfile(file_path):
            os.remove(file_path)
            n+=1
            #print(fn, "is removed")
    logger.info(f"Deleted {n} files from folder {audio_path}")


def create_path(p,create=False):
    p = os.path.expandvars(p)
    if create:
        folder = Path(p)
        folder.mkdir(exist_ok=True, parents=True)
    if not os.path.isdir(p):
        raise IOError(f"Couldn't create output folder: {p}")
    return p


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()

    global settings
    app.mount("/static", StaticFiles(directory=settings.output_dir), name="static")
    # ->  http://127.0.0.1:8000/static/FILENAME.wav    

    yield

app = FastAPI(lifespan=lifespan,swagger_ui_parameters={"tryItOutEnabled": True})

@app.get("/synthesize/sv_se_nst")
async def synthesize_sv_se_nst(input_type: str = 'phonemes',
                               input: str = "jɑːɡ ɛːr ɛn ɡˈamal trˈœt ɡˈɵbə",
                               length_scale: Optional[float] = None,
                               noise_scale: Optional[float] = None,
                               noise_w: Optional[float] = None,
                               sentence_silence: float = 0.0):
    return await synthesize(voice = 'sv_SE-nst-medium',
                            input_type = input_type,
                            input = input,
                            length_scale = length_scale,
                            noise_scale = noise_scale,
                            noise_w = noise_w,
                            sentence_silence = sentence_silence)

@app.get("/synthesize/en_us_bryce")
async def synthesize_en_us_bryce(input_type: str = 'text',
                               input: str = "hello, my name is bryce",
                               length_scale: Optional[float] = None,
                               noise_scale: Optional[float] = None,
                               noise_w: Optional[float] = None,
                               sentence_silence: float = 0.0):
    return await synthesize(voice = 'en_US-bryce-medium',
                            input_type = input_type,
                            input = input,
                            length_scale = length_scale,
                            noise_scale = noise_scale,
                            noise_w = noise_w,
                            sentence_silence = sentence_silence)

@app.get("/synthesize/en_us_norman")
async def synthesize_en_us_norman(input_type: str = 'text',
                               input: str = "hello, my name is norman",
                               length_scale: Optional[float] = None,
                               noise_scale: Optional[float] = None,
                               noise_w: Optional[float] = None,
                               sentence_silence: float = 0.0):
    return await synthesize(voice = 'en_US-norman-medium',
                            input_type = input_type,
                            input = input,
                            length_scale = length_scale,
                            noise_scale = noise_scale,
                            noise_w = noise_w,
                            sentence_silence = sentence_silence)

@app.get("/synthesize/ar_jo_kareem")
async def synthesize_ar_jo_kareem(input_type: str = 'text',
                               input: str = "ويكيبيديا العربية",
                               length_scale: Optional[float] = None,
                               noise_scale: Optional[float] = None,
                               noise_w: Optional[float] = None,
                               sentence_silence: float = 0.0):
    return await synthesize(voice = 'ar_JO-kareem-medium',
                            input_type = input_type,
                            input = input,
                            length_scale = length_scale,
                            noise_scale = noise_scale,
                            noise_w = noise_w,
                            sentence_silence = sentence_silence)

@app.get("/synthesize/")
async def synthesize(voice: str = "en_US-bryce-medium",
                     input: str = "hello",
                     input_type: str = "text",
                     #speaker_id: str = None,
                     length_scale: Optional[float] = None,
                     noise_scale: Optional[float] = None,
                     noise_w: Optional[float] = None,
                     sentence_silence: float = 0.0,
                     return_type: str = 'json'):
    if voice not in synths:
        msg = f"No such voice: {voice}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
        
    import re
    inputs = re.split(r"[.!?]+( +|$)", input)
    while "" in inputs:
        inputs.remove("")
    while " " in inputs:
        inputs.remove(" ")
    global input_types
    if input_type not in input_types:
        msg = f"Invalid input type: '{input_type}'. Use one of the following: {input_types}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)
    res = []
    import uuid
    uid = uuid.uuid4()
    try:
        for i, input in enumerate(inputs):
            basename = f"utt_{uid}_{i+1:03d}"
            synthesize_args = {
                "speaker_id": None,
                "length_scale": length_scale,
                "noise_scale": noise_scale,
                "noise_w": noise_w,
                "sentence_silence": sentence_silence,
            }
            entry = synths[voice].process_input(input, input_type, settings.output_dir, basename, synthesize_args)
            res.append(entry)
                
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
    global voices
    res = []
    for k,v in synths.items():
        pc = v.pvoice.config
        # sort phoneme id map and render as a string sequence of chars
        phoneme_id_map = sorted(pc.phoneme_id_map.items(), key=lambda kv: (kv[1], kv[0]))
        phonemes = "".join([''.join(x[0]) for x in phoneme_id_map])
        conf = {
            "name": v.name,
            "num_symbols": pc.num_symbols,
            "num_speakers": pc.num_speakers,
            "sample_rate": pc.sample_rate,
            "espeak_voice": pc.espeak_voice,
            "length_scale": pc.length_scale,
            "noise_scale": pc.noise_scale,
            "noise_w": pc.noise_w,            
            "phonemes": phonemes,
            #"phoneme_id_map": phoneme_id_map
        }
        res.append(conf)
    return res
