import json
import sys, os
from pathlib import Path

# Imports from this repo
import tools, voice

from piper import PiperVoice, SynthesisConfig

# Logging
logger = tools.get_logger()

defaults = {
    "length_scale": 1.10,
    "noise_scale": 1.0,
    "noise_w_scale": 1.0,    
}

class PiperConfig:
    voices: dict
    model_paths: list
    output_path: str
    force_cpu: bool

    
def load_config(config_file):
    with open(config_file, 'r') as file:
        data = json.load(file)
        result = PiperConfig()
        result.model_paths = list(map(tools.create_path, data['model_paths']))
        result.output_path = tools.create_path(data['output_path'], create=True)
        result.force_cpu = data.get('force_cpu', False)
        result.voices = {}

        if data.get('clear_audio_on_startup', False):
            tools.clear_audio(result.output_path)

        ## read voices in config file
        for voice_config in data['voices']:
            name = voice_config.get('name', voice_config['model'])
            if name in result.voices:
                raise Exception(f"Config file contains duplicate voices named {name}")

            if not voice_config.get('enabled', True):
                logger.debug(f"Skipping voice {name} (not enabled)")
                v = voice.Voice(name=voice_config['name'],
                                enabled=False,
                                config=voice_config,
                                piper_voice=None,
                                model=None, # tools.find_file(voice_config['model'], result.model_paths),
                                length_scale=voice_config.get('length_scale',1.0),
                                noise_scale=voice_config.get('noise_scale',1.0),
                                noise_w_scale=voice_config.get('noise_w_scale',1.0),                                                                
                                speaker_id=voice_config.get('speaker_id',None),
                                phonemizers=[],
                                selected_phonemizer_index=0)
                result.voices[name] = v
                continue

            phonemizers = []
            defaultPhnIndex = 0
            for i, phizer in enumerate(voice_config['phonemizers']):
                if phizer.get('enabled', True):
                    if phizer.get('default', False):
                        defaultPhnIndex = i
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

            onnx_fn = str(Path(voice_config['model']).with_suffix(".onnx"))
            model_path = tools.find_file( onnx_fn, result.model_paths)
            cuda = False
            config = None # Explicit path to config file, but we should always have the config file stored with the onnx model
            piper_voice = PiperVoice.load(model_path, config, cuda)
            v = voice.Voice(name=voice_config.get('name',voice_config['model']),
                            enabled=True,
                            config=voice_config,
                            piper_voice=piper_voice,
                            model=model_path,
                            length_scale=voice_config.get('length_scale',1.0),
                            noise_scale=voice_config.get('noise_scale',1.0),
                            noise_w_scale=voice_config.get('noise_w_scale',1.0),
                            speaker_id=voice_config.get('speaker_id',None),
                            phonemizers=phonemizers,
                            selected_phonemizer_index=defaultPhnIndex)
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
                logger.debug(f"Loaded dp phonemizer {self.pher}")
            elif tpe == "espeak":
                import phonemizer
                self.pher = phonemizer.backend.EspeakBackend(
                    language=lang,
                    preserve_punctuation=True,
                    with_stress=True,
                    language_switch="remove-flags",
                    logger=logger,
                )
                logger.debug(f"Loaded espeak phonemizer {self.pher}")
            else:
                raise Exception(f"Unknown phonemizer type {typ} for {selfname}")
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

    def phonemize(self, input, lang=None):
        logger.debug("phonemize called with {input}")
        if self.tpe == "deep_phonemizer":
            if lang is None:
                lang = self.lang
            else:
                if lang not in self.pher.predictor.text_tokenizer.languages:
                    logger.info(f"Language {lang} is not supported by phonemizer. Using {self.lang} instead")
                    lang = self.lang
            return self.pher(input, lang)
        else:
            return self.pher.phonemize([input], strip=True, njobs=1)[0]

    def __str__(self):
        return f"(name={self.name},lang={self.lang},model={self.path})"
