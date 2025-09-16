import sys
import os
from pathlib import Path

# Logging
import logging
logger = logging.getLogger('matcha')
logger.setLevel(logging.DEBUG)

# EXAMPLE COMMANDS

# python matcha_cli.py -m ~/.local/share/matcha_tts/martin_singlechar_ipa.ckpt -v ~/.local/share/matcha_tts/hifigan_univ_v1 --phonemizer ~/.local/share/deep_phonemizer/dp_single_char_swe_langs.pt -l swe "jag är nikolajs martinröst" --symbols symbols/symbols_martin_singlechar.txt

# python matcha_cli.py -m ~/.local/share/matcha_tts/svensk_multi.ckpt -v ~/.local/share/matcha_tts/hifigan_univ_v1 --phonemizer ~/.local/share/deep_phonemizer/joakims_best_model_no_optim.pt -l sv --matcha-speaker 1 "jag är joakims röst" --symbols symbols/symbols_joakims.txt

# python matcha_cli.py --config_file config_hl_matcha_cli.json --voice sv_se_nst_STTS-test --phonemizer sv_se_braxen_full_sv "här använder vi en configfil"

# python matcha_cli.py --config_file config_hl_matcha_cli.json --voice en_us_vctk --phonemizer espeak "and this is espeak with a config file" --matcha-speaker 3

import argparse

parser = argparse.ArgumentParser(
                    prog='matcha_cli',
                    description='Matcha client with option to use deep phonemizer for transcriptions',
#                    epilog='<Extra help text>'
)

# Using config file
parser.add_argument('--config_file')
parser.add_argument('--voice')


# Using cmdline args
parser.add_argument('-m', '--model', help="Path to voice model (.ckpt)")
parser.add_argument('-v', '--vocoder', help="Path to vocoder (usually no extension)")
parser.add_argument('-l', '--phonemizer-lang')
parser.add_argument('--symbols', default=None, type=str, help="File or string")

parser.add_argument('--steps', default=10, type=int)
parser.add_argument('--temperature', default=0.667, type=float)
parser.add_argument('--denoiser-strength', default=0.00025, type=float)
parser.add_argument('--device', type=str, default="cpu")
parser.add_argument('--matcha-speaker', type=int, default=None) # default is fetched from voice config
parser.add_argument('--speaking-rate', type=float, default=0.85, help="higher value=>slower, lower=>faster, 1.0=neutral, default=0.85") # default is fetched from voice config

parser.add_argument('--phonemizer')

parser.add_argument('-i', '--input_type', default="text", help="text, phonemes or mixed")
parser.add_argument('input', help='input text/phonemes')

#base_name = f"utterance_{i:03d}"
default_file=os.path.join(os.getcwd(), "utterance_001.wav")
parser.add_argument('-o', '--output-file', default=default_file, help=f"Default: {default_file}")

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
        parser.error("--config_file unset requires --model and --vocoder")
        os.exit(1)

if args.input_type not in ["phonemes","mixed"] and not args.phonemizer:
    parser.error(" --phonemizer is required for input_type phonemes/mixed")
    os.exit(1)

if args.input_type not in ["text","phoneme","mixed"]:
    parser.error(f"--input_type takes values text, phonemes or mixed; found {args.input_type}")
    os.exit(1)
        

import voice_config
if args.config_file:
    voice = voice_config.load_from_config(args)
else:
    voice = voice_config.load_from_args(args)
voice.validate()
print(f"[+] Loaded voice: {voice.name}: {voice}")
symbols = voice.symbols
SPACE_ID = symbols.index(" ")


output_name = os.path.basename(args.output_file)
output_name = Path(output_name).with_suffix('')
output_folder = os.path.dirname(args.output_file)

print("Starting imports...",file=sys.stderr)

from matcha.utils.utils import intersperse
from matcha.cli import to_waveform, save_to_folder, load_matcha, load_vocoder
import torch

print("... imports completed",file=sys.stderr)

# Mappings from symbol to numeric ID and vice versa:
_symbol_to_id = {s: i for i, s in enumerate(symbols)}
_id_to_symbol = {i: s for i, s in enumerate(symbols)}  # pylint: disable=unnecessary-comprehension


def cleaned_text_to_sequence(cleaned_text):
    """Converts a string of text to a sequence of IDs corresponding to the symbols in the text.
    Args:
      text: string to convert to a sequence
    Returns:
      List of integers corresponding to the symbols in the text
    """
    sequence = [_symbol_to_id[symbol] for symbol in cleaned_text]
    return sequence


def sequence_to_text(sequence):
    """Converts a sequence of IDs back to a string"""
    result = ""
    for symbol_id in sequence:
        s = _id_to_symbol[symbol_id]
        result += s
    return result

def process_text(i: int, input: str, device: torch.device):
    print(f"[{i}] - Input text: {input}")


    s = input.lower()
    s = s.replace(".","")

    if not args.input_type == "phonemes":
        phn_list = []
        for w in s.split(" "):
            #result = phonemizer(w, lang=lang)
            result = voice.phonemizer.phonemize(w)            
            print(f"{w}\t{result}")
            phn_list.append(result)
        phn = " ".join(phn_list)
        cleaned_text = cleaned_text_to_sequence(phn)
        print(f"{phn=}\t{cleaned_text=}")
    else:
        cleaned_text = cleaned_text_to_sequence(input)
        print(f"{input=}\t{cleaned_text=}")

    x = torch.tensor(
        intersperse(cleaned_text, 0),
        dtype=torch.long,
        device=device,
    )[None]
    x_lengths = torch.tensor([x.shape[-1]], dtype=torch.long, device=device)
    x_phones = sequence_to_text(x.squeeze(0).tolist())
    print(f"[{i}] - Phonetised text: {x_phones[1::2]}")

    return {"x_orig": input, "x": x, "x_lengths": x_lengths, "x_phones": x_phones}


checkpoint_path = Path(voice.model)

vocoder_name = os.path.basename(voice.vocoder)

model = load_matcha(voice.model, checkpoint_path, voice.device)
vocoder, denoiser = load_vocoder(vocoder_name, voice.vocoder, voice.device)

index = 0
text_processed = process_text(index, args.input, voice.device)


print(text_processed)
print(voice.steps, voice.temperature, voice.speaker, voice.speaking_rate)

spk = torch.tensor([voice.speaker],device=voice.device) if voice.speaker is not None else None
output = model.synthesise(
    text_processed["x"],
    text_processed["x_lengths"],
    n_timesteps=voice.steps,
    temperature=voice.temperature,
    spks=spk,
    length_scale=voice.speaking_rate,
)

import alignment
id2symbol={i: s for i, s in enumerate(symbols)} 
aligned = alignment.align(text_processed, output, id2symbol)
print("alignment", aligned)

with torch.no_grad():
    output["waveform"] = to_waveform(output["mel"], vocoder, denoiser, voice.denoiser_strength)


location = save_to_folder(output_name, output, output_folder)
print(f"[+] Waveform saved: {location}")
