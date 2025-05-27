# For usage info, se README.md

import os, sys

# Local imports
import symbolset
from matcha_utils import(
    create_path,
    do_clear_audio,
    find_model,
    get_device,
    intersperse,
    load_matcha,
    load_vocoder,
    unbatched_synthesis,
    validate_args
)

# Other matcha-related imports
from argparse import Namespace
import torch

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

# Other imports
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

def load_config():
    import json
    global paths, synths
    
    json_config = os.getenv("MATCHA_CONFIG") # Reads from .env file passed to uvicorn
    loaded_names = []
    # Open and read the JSON file
    with open(json_config, 'r') as file:
        data = json.load(file)
        paths.output = create_path(data['output_path'], create=True)
        paths.models = list(map(create_path, data['model_paths']))
        paths.models.insert(0,".")
        force_cpu = data.get('force_cpu', False)

        clear_audio = True
        if 'clear_audio_on_startup' in data:
            clear_audio = ['clear_audio_on_startup']

        if clear_audio:
            do_clear_audio(paths.output)
            
        
        ## read voices in config file
        for voice in data['voices']:
            if 'enabled' in voice and voice['enabled'] == False:
                continue
            name = voice['name']
            model = voice['model']
            vocoder = voice['vocoder']
            args = Namespace(
                name=name,
                cpu=force_cpu,
                denoiser_strength=voice.get('denoiser_strength',0.00025),
                speaking_rate=voice.get('speaking_rate',1.0),
                steps=voice.get('steps',10),
                temperature=voice.get('temperature',0.667),
                batch_size=voice.get('batch_size',32),
                spk=voice.get('spk',None),
                output_folder=paths.output
            )
            if 'spk_range' in voice:
                #args.spk_range=tuple(voice['spk_range']) # TODO
                args.spk_range = (0, 107)
            model_path = find_model(model,paths.models)
            if model_path is None:
                raise IOError(f"Failed to find model {model}")
            vocoder_path = find_model(vocoder,paths.models)
            args.checkpoint_path = model_path
            args.vocoder = vocoder_path
            #args = validate_args(args)
            logger.debug(f"load_config voice: {voice} args: {args}")
            device = get_device(args) # gpu/cpu # TODO move out
            model = load_matcha(voice['model'], model_path, device)
            vocoder, denoiser = load_vocoder(voice['vocoder'], vocoder_path, device)
            spk = torch.tensor([args.spk], device=device, dtype=torch.long) if args.spk is not None else None
            pzer = None
            if "phonemizer" in voice:
                phner = voice["phonemizer"]
                if phner["type"] == "espeak":
                    import phonemizer
                    try:
                        pzer = phonemizer.backend.EspeakBackend(
                            language=phner["lang"],
                            preserve_punctuation=True,
                            with_stress=True,
                            language_switch="remove-flags",
                            logger=logger,
                        )
                    except RuntimeError as e:
                        msg = f"Couldn't load phonetizer for voice {name}: {e}. Voice will not be loaded."
                        logger.error(msg)
                        continue
                else:
                    raise IOError(f"Invalid phonemizer type: {phner['type']}")
            if 'symbols' in voice:
                symbols = voice['symbols']
            else:
                    raise IOError(f"Voice {name} lacks required 'symbols' definition")
            synth = Synthesizer(args, device, model, vocoder, denoiser, spk, pzer,  symbolset.Symbols(symbols), config=voice)

            synths[name] = synth
            loaded_names.append(name)
    logger.info(f"Loaded voices: {loaded_names}")


input_types = ['text','phonemes']
return_types = ['json','wav']

from dataclasses import dataclass
@dataclass
class Synthesizer:
    args: Namespace
    device: str
    model: object
    vocoder: object
    denoiser: object
    spk: object
    phonemizer: object
    symbolset: object
    config: object

    def process_input(self, i: int, input: str, input_type: str, device: torch.device):
        logger.debug(f"process_input [{i}] - Input: {input}")
        matcha_input = input
        if input_type == "text":
            if self.phonemizer is None:
                msg = f"No phonemizer defined for voice {self.args.name}"
                logger.error(msg)
                raise IOError(msg)
            #text = lowercase(text) # TODO
            #text = expand_abbreviations(text) # TODO
            matcha_input = self.phonemizer.phonemize([matcha_input], strip=True, njobs=1)[0]
            logger.info(f"phonemizer output: {matcha_input}")
            # Added in some cases espeak is not removing brackets
            #phonemes = remove_brackets(phonemes) # TODO
            #phonemes = collapse_whitespace(phonemes) # TODO
        invalid = []
        for symbol in matcha_input:
            if not symbol in self.symbolset.symbol2id:
                invalid += symbol
        if len(invalid) > 0:
            raise KeyError(f"Invalid input symbols: {invalid}")
        seq = self.symbolset.text_to_sequence(matcha_input)
        x = torch.tensor(
            intersperse(seq, 0),
            dtype=torch.long,
            device=device,
        )[None]
        x_lengths = torch.tensor([x.shape[-1]], dtype=torch.long, device=device)
        x_phones = self.symbolset.sequence_to_text(x.squeeze(0).tolist())
        logger.info(f"[{i}] - Processed input: {x_phones[1::2]}")
        
        res = {"phonemes": {x_phones[1::2]}, "x_orig": input, "x": x, "x_lengths": x_lengths, "x_phones": x_phones}
        return res
    
    @torch.no_grad()
    def synthesize(self, params):
        args = self.args
        args.speaking_rate = args.speaking_rate * params.speaking_rate
        logger.debug(f"synthesize params: {params}")
        return  unbatched_synthesis(args, self.device, self.model, self.vocoder, self.denoiser, params, self.spk, self.symbolset, self.process_input)

        
synths = {}
paths = Namespace()

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()

    global paths
    app.mount("/static", StaticFiles(directory=paths.output), name="static")
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
                               speaking_rate: float = 1.0):
    return await synthesize(voice = 'sv_se_nst',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate)

@app.get("/synthesize/en_us_vctk")
async def synthesize_en_us_vctk(input_type: str = 'phonemes',
                                input: str = "ðɛɹ mˈʌst biː ɐn ˈeɪndʒəl",
                                speaking_rate: float = 1.0):
    return await synthesize(voice = 'en_us_vctk',
                            input_type = input_type,
                            input = input,
                            speaking_rate = speaking_rate)

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
    global synths
    res = []
    for k,v in synths.items():
        res.append(v.config)
    return res

@app.get("/symbol_set/")
async def symbols_set(voice: str):
    global synths
    if voice in synths:
        symset = synths[voice].symbolset
        return {
            "symbols": symset.symbols,
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
    params = Namespace (
        input = inputs,
        input_type = input_type,
        speaking_rate = speaking_rate,
    )
    global input_types
    if input_type not in input_types:
        msg = f"Invalid input type: '{input_type}'. Use one of the following: {input_types}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)
    try:
        res = synths[voice].synthesize(params)
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


          

