import json
import sys, os
from pathlib import Path

# Logging
import logging
logger = logging.getLogger('matcha')

# Imports from this repo
import tools, voice

class MatchaConfig:
    voices: dict
    model_paths: list
    output_path: str
    force_cpu: bool

    
def load_from_args(args):
    symbols = args.symbols
    if os.path.isfile(args.symbols):
        with open(args.symbols, 'r') as file:
            symbols = file.read()
        
    if args.clear_audio:
        folder = os.path.dirname(args.output_file)
        tools.clear_audio(folder)

    if args.phonemizer == "espeak":
        phonemizer = Phonemizer("espeak", "espeak", args.phonemizer_lang)
    else:
        phonemizer = Phonemizer("deep_phonemizer", "deep_phonemizer", args.phonemizer_lang, args.phonemizer)
    return voice.Voice(name="cmdline_voice",
                       model=args.model,
                       vocoder=args.vocoder,
                       speaking_rate=args.speaking_rate,
                       speaker=args.speaker,
                       steps=args.steps,
                       temperature=args.temperature,
                       device=args.device,
                       denoiser_strength=args.denoiser_strength,
                       symbols=symbols,
                       phonemizers=[phonemizer],
                       selected_phonemizer_index=0)
    

def load_config(config_file):
    with open(config_file, 'r') as file:
        data = json.load(file)
        result = MatchaConfig()
        result.model_paths = list(map(tools.create_path, data['model_paths']))
        result.output_path = tools.create_path(data['output_path'], create=True)
        result.force_cpu = data.get('force_cpu', False)
        result.voices = {}
        
        #result.do_clear_audio = True
        #if 'clear_audio_on_startup' in data:
        #    result.do_clear_audio = ['clear_audio_on_startup']
        #if result.do_clear_audio:
        #    tools.clear_audio(result.output_path)
        if data.get('clear_audio_on_startup', False):
            tools.clear_audio(result.output_path)

        ## read voices in config file
        for voice_config in data['voices']:
            name = voice_config['name']
            if name in result.voices:
                raise Exception(f"Config file contains duplicate voices named {name}")

            if not voice_config.get('enabled', True):
                logger.debug(f"Skipping voice {name} (not enabled)")
                continue

            symbols = [voice_config['symbols']['pad']] + list(voice_config['symbols']['punctuation']) + list(voice_config['symbols']['letters']) + list(voice_config['symbols']['letters_ipa'])
            
            phonemizers = []
            for phizer in voice_config['phonemizers']:
                if phizer.get('enabled', True):
                    if phizer['type'] == "deep_phonemizer":
                        model_path = tools.find_file(phizer['model'], result.model_paths)
                        if model_path is None:
                            raise Exception(f"Couldn't find model {name} for {phizer['name']}. Looked in {result.model_paths}")
                        phonemizers.append(Phonemizer(phizer['name'], phizer['type'], phizer['lang'], model_path))
                    elif phizer['type'] == "espeak":
                        phonemizers.append(Phonemizer(phizer['name'], phizer['type'], phizer['lang']))
                    else:
                        raise Exception(f"Unknown phonemizer type {type} for {phizer['name']}")
                    
            if len(phonemizers) == 0:
                raise Exception(f"Couldn't find phonemizer for voice '{voice_config['name']}' in config file {config_file}")

            v = voice.Voice(name=voice_config['name'],
                            model=tools.find_file(voice_config['model'], result.model_paths),
                            vocoder=tools.find_file(voice_config['vocoder'], result.model_paths),
                            speaking_rate=voice_config.get('speaking_rate',1.0),
                            speaker=voice_config.get('spk',None),
                            steps=voice_config.get('steps',10),
                            temperature=voice_config.get('temperature',0.667),
                            device=voice_config.get('device','cpu'),
                            denoiser_strength=voice_config.get('denoiser_strength',0.00025),
                            symbols=symbols,
                            phonemizers=phonemizers,
                            selected_phonemizer_index=0) ## default phonemizer
            result.voices[name] = v
    logger.debug(f"Loaded config file {config_file}")
    return result


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
                if path is None:
                    raise Exception(f"Deep phonemizer {name} cannot be loaded without a model path. Found None")
                if not os.path.isfile(self.path):
                    raise Exception(f"Model path for deep phonemizer {name} does not exist: {path}")
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


    def as_json(self):
        obj = {
            "name": self.name,
            "type": self.tpe,
            "lang": self.lang,
            "path": self.path,
        }
        return obj

    def phonemize(self, input):
        if self.tpe == "deep_phonemizer":
            return self.pher(input, lang=self.lang)
        else:
            return self.pher.phonemize([input], strip=True, njobs=1)[0]

    def __str__(self):
        return f"(name={self.name},lang={self.lang},model={self.path})"
