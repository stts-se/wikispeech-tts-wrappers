import json
#import sys
import os

# Imports from this repo
import tools
import voice

# Logging
logger = tools.get_logger()

defaults = {
    "steps": 10,
    "speaking_rate": 1.0,
    "denoiser_strength": 0.00025,
    "temperature": 0.667
}

class MatchaConfig:
    voices: dict
    model_paths: list
    output_path: str
    force_cpu: bool


def load_from_args(args):
    symbols = args.symbols
    if os.path.isfile(args.symbols):
        with open(args.symbols, 'r', encoding="utf-8") as file:
            symbols = file.read()

    if args.clear_audio:
        folder = os.path.dirname(args.output_file)
        tools.clear_audio(folder)

    phonemizers = []
    if args.phonemizer_type == "espeak":
        phonemizers.append(voice.Phonemizer("espeak", "espeak", args.phonemizer_lang))
    elif args.phonemizer_type == "deep_phonemizer":
        phonemizers.append(voice.Phonemizer("deep_phonemizer", "deep_phonemizer", args.phonemizer_lang, args.phonemizer))
    elif args.phonemizer_type is not None:
        raise Exception(f"Unknown phonemizer type {args.phonemizer_type}")
    return voice.Voice(name="cmdline_voice",
                       enabled=True,
                       config=None,
                       model=args.model,
                       vocoder=args.vocoder,
                       speaking_rate=args.speaking_rate,
                       speaker=args.speaker,
                       steps=args.steps,
                       temperature=args.temperature,
                       device=args.device,
                       denoiser_strength=args.denoiser_strength,
                       symbols=symbols,
                       phonemizers=phonemizers,
                       selected_phonemizer_index=0)


def load_config(config_file):
    with open(config_file, 'r', encoding="utf-8") as file:
        data = json.load(file)
        result = MatchaConfig()
        result.model_paths = list(map(tools.create_path, data['model_paths']))
        result.output_path = tools.create_path(data['output_path'], create=True)
        result.force_cpu = data.get('force_cpu', False)
        result.voices = {}

        if data.get('clear_audio_on_startup', False):
            tools.clear_audio(result.output_path)

        ## read voices in config file
        for voice_config in data['voices']:
            name = voice_config['name']
            if name in result.voices:
                raise Exception(f"Config file contains duplicate voices named {name}")

            # TODO error handling if symbols and/or symbols/XX is missing from config
            symbols = [voice_config['symbols']['pad']] + list(voice_config['symbols']['punctuation']) + list(voice_config['symbols']['letters']) + list(voice_config['symbols']['letters_ipa'])

            v = voice.Voice(name=voice_config['name'],
                            enabled=False,
                            config=voice_config,
                            model=None, # tools.find_file(voice_config['model'], result.model_paths),
                            vocoder=None, # tools.find_file(voice_config['vocoder'], result.model_paths),
                            speaking_rate=voice_config.get('speaking_rate',1.0),
                            speaker=voice_config.get('spk',None),
                            steps=voice_config.get('steps',10),
                            temperature=voice_config.get('temperature',0.667),
                            device=voice_config.get('device','cpu'),
                            denoiser_strength=voice_config.get('denoiser_strength',0.00025),
                            symbols=symbols,
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

    return result
