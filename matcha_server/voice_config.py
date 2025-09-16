import json
import sys, os
from pathlib import Path

# Logging
import logging
logger = logging.getLogger('matcha')
logger.setLevel(logging.DEBUG)

from dataclasses import dataclass, asdict
@dataclass
class VoiceConfig:
    name: str
    model: str
    vocoder: str
    speaking_rate: float

    steps: int
    temperature: float
    denoiser_strength: float
    device: str

    speaker: object
    symbols: str

    phonemizer: object

    def __str__(self):
        dict = asdict(self)
        dict['phonemizer'] = f"{self.phonemizer}"
        dict['symbols'] = "".join(self.symbols)
        return f"{dict}"

    def validate(__self__):
        if __self__.symbols == "":
            raise Exception(f"No symbols defined for voice {__self__.name}")

def find_file(name, paths):
    for p in paths:
        f = os.path.join(p, name)
        if os.path.isfile(f):
            return f
    return None
    
def load_from_args(args):
    symbols = args.symbols
    if os.path.isfile(args.symbols):
        with open(args.symbols, 'r') as file:
            symbols = file.read()
        
    if args.phonemizer == "espeak":
        phonemizer = Phonemizer("espeak", "espeak", args.phonemizer_lang)
    else:
        phonemizer = Phonemizer("deep_phonemizer", "deep_phonemizer", args.phonemizer_lang, args.phonemizer)
    return VoiceConfig(name="cmdline_voice",
                       model=args.model,
                       vocoder=args.vocoder,
                       speaking_rate=args.speaking_rate,
                       speaker=args.matcha_speaker,
                       steps=args.steps,
                       temperature=args.temperature,
                       device=args.device,
                       denoiser_strength=args.denoiser_strength,
                       symbols=symbols,
                       phonemizer=phonemizer)
    

def get_or_else(value1, value2, default=None):
    if value1 is not None:
        return value1
    elif value2 is not None:
        return value2
    else:
        return default
    
def load_from_config(args):
    found_voice = False
    with open(args.config_file, 'r') as file:
        data = json.load(file)
        model_paths = list(map(os.path.expandvars, data['model_paths']))
        force_cpu = data.get('force_cpu', False)

        ## read voices in config file
        for voice in data['voices']:
            name = voice['name']
            if name != args.voice:
                continue
            if 'enabled' in voice and voice['enabled'] == False:
                raise Exception(f"Voice {args.voice} is not enabled")

            found_voice = True
            symbols = [voice['symbols']['pad']] + list(voice['symbols']['punctuation']) + list(voice['symbols']['letters']) + list(voice['symbols']['letters_ipa'])
            
            phonemizer = None
            if not args.input_type == "phonemes" or args.input_type == "mixed":
                for phizer in voice['phonemizers']:
                    if phizer['name'] != args.phonemizer:
                        continue
                    if 'enabled' in phizer and phizer['enabled'] == False:
                        raise Exception(f"Phonemizer {args.phonemizer} is not enabled")
                    if phizer['type'] == "deep_phonemizer":
                              phonemizer = Phonemizer(args.phonemizer, phizer['type'], phizer['lang'], find_file(phizer['model'],model_paths))
                    elif phizer['type'] == "espeak":
                              phonemizer = Phonemizer(args.phonemizer, phizer['type'], phizer['lang'])
                    else:
                        raise Exception(f"Unknown phonemizer type {type} for {args.phonemizer}")

            return VoiceConfig(name=args.voice,
                               model=find_file(voice['model'], model_paths),
                               vocoder=find_file(voice['vocoder'], model_paths),
                               speaking_rate=get_or_else(args.speaking_rate, voice.get('speaking_rate',1.0)),
                               speaker=get_or_else(args.matcha_speaker, voice.get('spk',None)),
                               steps=get_or_else(args.steps, voice.get('steps',10)),
                               temperature=get_or_else(args.temperature, voice.get('temperature',0.667)),
                               device=get_or_else(args.device,voice.get('device','cpu')),
                               denoiser_strength=get_or_else(args.denoiser_strength,voice.get('denoiser_strength',0.00025)),
                               symbols=symbols,
                               phonemizer=phonemizer)
            
    if found_voice:
        raise Exception(f"Couldn't find a phonemizer named '{args.phonemizer}' for voice '{args.voice}' in config file {args.config_file}")
    else:
        raise Exception(f"Couldn't find a voice named '{args.voice}' in config file {args.config_file}")
    return None


class Phonemizer:
    name: str
    tpe: str
    lang: str
    pher: object
    def __init__(self, name, tpe, lang, path=None):
        self.name = name
        self.tpe = tpe
        self.lang = lang
        self.path = path
        try:
            if tpe == "deep_phonemizer":
                from dp.phonemizer import Phonemizer
                self.pher = Phonemizer.from_checkpoint(path)
            elif tpe == "espeak":
                import phonemizer
                self.pher = phonemizer.backend.EspeakBackend(
                    language=lang,
                    preserve_punctuation=True,
                    with_stress=True,
                    language_switch="remove-flags",
                    logger=logger,
                )
        except RuntimeError as e:
            msg = f"Couldn't load phonetizer for voice {name}: {e}. Voice will not be loaded."
            logger.error(msg)


    def phonemize(self, input):
        if self.tpe == "deep_phonemizer":
            return self.pher(input, lang=self.lang)
        else:
            return self.pher.phonemize([input], strip=True, njobs=1)[0]

    def __str__(self):
        return f"(name={self.name},lang={self.lang},model={self.path})"
