import json
import sys, os
from pathlib import Path

# Logging
import logging
logger = logging.getLogger('matcha')

# Imports from this repo
import tools, voice_config

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
        
    if args.phonemizer == "espeak":
        phonemizer = Phonemizer("espeak", "espeak", args.phonemizer_lang)
    else:
        phonemizer = Phonemizer("deep_phonemizer", "deep_phonemizer", args.phonemizer_lang, args.phonemizer)
    return voice_config.Voice(name="cmdline_voice",
                              model=args.model,
                              vocoder=args.vocoder,
                              speaking_rate=args.speaking_rate,
                              speaker=args.matcha_speaker,
                              steps=args.steps,
                              temperature=args.temperature,
                              device=args.device,
                              denoiser_strength=args.denoiser_strength,
                              symbols=symbols,
                              phonemizers=[phonemizer],
                              selected_phonemizer=phonemizer)
    

def load_config(config_file):
    with open(config_file, 'r') as file:
        data = json.load(file)
        result = MatchaConfig()
        result.model_paths = list(map(tools.create_path, data['model_paths']))
        result.output_path = tools.create_path(data['output_path'], create=True)
        result.force_cpu = data.get('force_cpu', False)
        result.voices = {}
        
        result.do_clear_audio = True
        if 'clear_audio_on_startup' in data:
            result.do_clear_audio = ['clear_audio_on_startup']
        if result.do_clear_audio:
            tools.clear_audio(result.output_path)

        ## read voices in config file
        for voice in data['voices']:
            name = voice['name']
            if name in result.voices:
                raise Exception(f"Config file contains duplicate voices named {name}")
            
            symbols = [voice['symbols']['pad']] + list(voice['symbols']['punctuation']) + list(voice['symbols']['letters']) + list(voice['symbols']['letters_ipa'])
            
            phonemizers = []
            for phizer in voice['phonemizers']:
                if phizer.get('enabled', True):
                    if phizer['type'] == "deep_phonemizer":
                        phonemizers.append(Phonemizer(phizer['name'], phizer['type'], phizer['lang'], tools.find_file(phizer['model'], result.model_paths)))
                    elif phizer['type'] == "espeak":
                        phonemizers.append(Phonemizer(phizer['name'], phizer['type'], phizer['lang']))
                    else:
                        raise Exception(f"Unknown phonemizer type {type} for {phizer['name']}")
                    
            if len(phonemizers) == 0:
                raise Exception(f"Couldn't find phonemizer for voice '{voice['name']}' in config file {config_file}")

            voice = voice_config.Voice(name=voice['name'],
                                       model=tools.find_file(voice['model'], result.model_paths),
                                       vocoder=tools.find_file(voice['vocoder'], result.model_paths),
                                       speaking_rate=voice.get('speaking_rate',1.0),
                                       speaker=voice.get('spk',None),
                                       steps=voice.get('steps',10),
                                       temperature=voice.get('temperature',0.667),
                                       device=voice.get('device','cpu'),
                                       denoiser_strength=voice.get('denoiser_strength',0.00025),
                                       symbols=symbols,
                                       phonemizers=phonemizers,
                                       selected_phonemizer=phonemizers[0]) ## default phonemizer
            result.voices[name] = voice
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
