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

            v = voice.Voice(name=voice_config.get('name',voice_config['model']),
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
            if not voice_config.get('enabled', True):
                logger.debug(f"Skipping voice {name} (not enabled)")
                continue
            v.enabled = True
            if not voice_config.get('load_on_startup', True):
                logger.debug(f"Not loading voice {name} on startup")
                continue
            v.load(result.model_paths)
            
    logger.debug(f"Loaded config file {config_file}")
    return result
