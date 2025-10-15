import sys
import os
from pathlib import Path

# imports from this repo
import tools

# Logging
logger = tools.get_logger("matcha_cli")

import config

### EXAMPLE COMMANDS WITH PUBLICLY AVAILABLE MODELS

# python matcha_cli.py --config_file config_sample.json --voice en_us_vctk --phonemizer espeak "and this is espeak with a config file" --speaker 3

# python matcha_cli.py --config_file config_sample.json --voice en_us_ljspeech "l j speech is a public domain voice" --speaking-rate 1.5


### EXAMPLE COMMANDS WITH STTS INTERNAL MODELS

# python matcha_cli.py -m ~/.local/share/matcha_tts/martin_singlechar_ipa.ckpt -v ~/.local/share/matcha_tts/hifigan_univ_v1 --phonemizer ~/.local/share/deep_phonemizer/dp_single_char_swe_langs.pt -l swe "jag är nikolajs martinröst" --symbols cli_symbols/symbols_martin_singlechar.txt

# python matcha_cli.py -m ~/.local/share/matcha_tts/svensk_multi.ckpt -v ~/.local/share/matcha_tts/hifigan_univ_v1 --phonemizer ~/.local/share/deep_phonemizer/joakims_best_model_no_optim.pt -l sv --speaker 1 "jag är joakims röst" --symbols cli_symbols/symbols_joakims.txt

# python matcha_cli.py --config_file config_stts.json --voice sv_se_nst_STTS-test --phonemizer sv_se_braxen_full_sv "här använder vi en configfil"

# python matcha_cli.py --config_file config_stts.json --voice sv_se_nst_STTS-test --phonemizer sv_se_braxen_full_sv "här använder vi en json [[k°ɔnfɪgf\`Il]]"


import argparse

parser = argparse.ArgumentParser(
                    prog='matcha_cli',
                    description='Matcha client with option to use deep phonemizer for transcriptions',
#                    epilog='<Extra help text>'
)

# With config file
parser.add_argument('--config_file')
parser.add_argument('--voice')

# With cmdline args
parser.add_argument('-m', '--model', help="Path to voice model (.ckpt)")
parser.add_argument('-v', '--vocoder', help="Path to vocoder (usually no extension)")
parser.add_argument('-l', '--phonemizer-lang')
parser.add_argument('--symbols', default=None, type=str, help="File or string")

parser.add_argument('--steps', default=10, type=int)
parser.add_argument('--temperature', default=0.667, type=float)
parser.add_argument('--denoiser-strength', default=0.00025, type=float)
parser.add_argument('--device', type=str, default="cpu")
parser.add_argument('--speaker', type=int, default=None) # default is fetched from voice config
parser.add_argument('--speaking-rate', type=float, default=0.85, help="higher value=>slower, lower=>faster, 1.0=neutral, default=0.85") # default is fetched from voice config
parser.add_argument('--clear-audio',action='store_true', help="Clear audio on startup")

parser.add_argument('--phonemizer')

input_types = ['text','phonemes','mixed']
parser.add_argument('-i', '--input-type', default="mixed", help=f"{input_types}; for mixed input, orth input is expected, but you can put phoneme input in [[double brackets]]")

parser.add_argument('input', help='input (text, phonemes or mixed)')

#base_name = f"utterance_{i:03d}"
default_dir=os.path.join(os.getcwd(), "audio_files")
os.makedirs(default_dir, exist_ok=True)
default_file=os.path.join(default_dir, "cli_utterance_001.wav")
parser.add_argument('-o', '--output-file', default=default_file, help=f"default: {default_file}")

args = parser.parse_args()

if args.config_file:
    if args.voice is None:
        parser.error("--config_file requires --voice")
        os.exit(1)
    if args.symbols is not None:
        parser.error("--symbols is not allowed with --config_file")
        os.exit(1)

if not args.config_file:
    if  (args.model is None or args.vocoder is None):
        parser.error("--model and --vocoder are required for use without config file")
        os.exit(1)
    if args.input_type not in ["phonemes","mixed"] and not args.phonemizer:
        parser.error(" --phonemizer is required for input_type phonemes/mixed when used without config file")
        os.exit(1)

if args.input_type not in input_types:
    parser.error(f"Invalid input type: '{input_type}'. Use one of the following: {input_types}")
    os.exit(1)
       

if args.config_file:
    result = config.load_config(args.config_file)
    if args.voice in result.voices:
        voice = result.voices[args.voice]
    else:
        raise Exception(f"Couldn't find a voice named '{args.voice}' in config file {args.config_file}")    
else:
    voice = config.load_from_args(args)
voice.validate()
logger.debug(f"Loaded voice: {voice.name}: {voice}")

### Set voice properties if included in args
if args.speaking_rate:
    voice.speaking_rate=args.speaking_rate
if args.speaker:
    voice.speaker=args.speaker
if args.steps:
    voice.steps=args.steps
if args.temperature:
    voice.temperature=args.temperature
if args.device:
    voice.device=args.device
if args.denoiser_strength:
    voice.denoiser_strength=args.denoiser_strength
                               
### Select phonemizer
if args.phonemizer == None:
    voice.selected_phonemizer_index = 0
elif args.config_file == None:
    voice.selected_phonemizer_index = 0
else:
    found_named_phonemizer = False
    for i, phoner in enumerate(voice.phonemizers):
        if phoner.name == args.phonemizer:
            voice.selected_phonemizer_index = i
            found_named_phonemizer = True
    if not found_named_phonemizer:
        raise Exception(f"No phonemizer named {args.phonemizer} for voice {voice.name}")

logger.debug(f"Selected phonemizer: {voice.selected_phonemizer()}")

voice.validate()

result = voice.synthesize(args.input, args.input_type, args.output_file, args)
print(f"[+] Final output {result}")
