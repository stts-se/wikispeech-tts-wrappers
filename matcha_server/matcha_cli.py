import sys

import argparse

parser = argparse.ArgumentParser(
                    prog='matcha_cli',
                    description='Matcha client with option to use deep phonemizer for transcriptions',
#                    epilog='<Extra help text>'
)
parser.add_argument('-d', '--deep_phonemizer')
parser.add_argument('-m', '--model', required=True)
parser.add_argument('-v', '--vocoder', required=True)
parser.add_argument('-l', '--dp-lang', required=True)
parser.add_argument('--matcha-speaker', type=int, default=None)

parser.add_argument('-p', '--phoneme_input', action='store_true')
parser.add_argument('input', help='text/phonemes (default: text)')

# EXAMPLE COMMANDS

#python matcha_cli.py -d ~/.local/share/deep_phonemizer/dp_single_char_swe_langs.pt -m ~/.local/share/matcha_tts/martin_singlechar_ipa.ckpt -v ~/.local/share/matcha_tts/hifigan_univ_v1 -l swe "idag är det torsdag"
#
#python matcha_cli.py -d ~/.local/share/deep_phonemizer/joakims_best_model_no_optim.pt -m ~/.local/share/matcha_tts/svensk_multi.ckpt -v ~/.local/share/matcha_tts/hifigan_univ_v1 -l sv --matcha-speaker 1 "idag är det torsdag"

args = parser.parse_args()

print("Starting imports...",file=sys.stderr)


from matcha.utils.utils import intersperse

from matcha.cli import to_waveform, save_to_folder, load_matcha, load_vocoder
from pathlib import Path
import os
import torch

# importing local symbols from working folder
if "martin_singlechar" in args.model:
    print(f"Loading symbols matcha_cli_symbols_martin_singlechar", file=sys.stderr)
    from matcha_cli_symbols_martin_singlechar import symbols
elif "svensk_multi" in args.model:
    print(f"Loading symbols matcha_cli_symbols_joakims", file=sys.stderr)
    from matcha_cli_symbols_joakims import symbols
else:
    print(f"No symbols.py for model {args.model}",file=sys.stderr)
    sys.exit(1)

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

def process_text_ws_svenska(i: int, input: str, device: torch.device):
    print(f"[{i}] - Input text: {input}")


    s = input.lower()
    s = s.replace(".","")

    if not args.phoneme_input:    
        phn_list = []
        for w in s.split(" "):
            result = phonemizer(w, lang=lang)
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


device = "cpu"
phonemizer = None
if not args.phoneme_input:
    from dp.phonemizer import Phonemizer
    phonemizer = Phonemizer.from_checkpoint(args.deep_phonemizer)
    lang = args.dp_lang
    

model_name = args.model
checkpoint_path = Path(model_name)

vocoder_checkpoint_path = args.vocoder # "/home/hanna/.local/share/matcha_tts/hifigan_univ_v1"
vocoder_name = os.path.basename(vocoder_checkpoint_path)

model = load_matcha(model_name, checkpoint_path, device)
vocoder, denoiser = load_vocoder(vocoder_name, vocoder_checkpoint_path, device)

#args
steps = 10
temperature = 0.667
speaking_rate = 0.85
denoiser_strength = 0.00025
output_folder = os.getcwd()


i = 0
base_name = f"utterance_{i:03d}"


text_processed = process_text_ws_svenska(i, args.input, device)


print(text_processed)
print(steps, temperature, args.matcha_speaker, speaking_rate)

spk = torch.tensor([args.matcha_speaker],device=device) if args.matcha_speaker is not None else None
output = model.synthesise(
    text_processed["x"],
    text_processed["x_lengths"],
    n_timesteps=steps,
    temperature=temperature,
    spks=spk,
    length_scale=speaking_rate,
)

with torch.no_grad():
    output["waveform"] = to_waveform(output["mel"], vocoder, denoiser, denoiser_strength)


location = save_to_folder(base_name, output, output_folder)
print(f"[+] Waveform saved: {location}")
