import sys

import wave
from piper import PiperVoice, SynthesisConfig

import argparse

cmd='piper_cli'
parser = argparse.ArgumentParser(
    prog=cmd,
    description='A simple piper client',
)

parser.add_argument('onnx_model')
parser.add_argument('input')
parser.add_argument('output_file')

args = parser.parse_args()

voice = PiperVoice.load(args.onnx_model)

syn_config = SynthesisConfig(
    volume=1.0,
    length_scale=1.0,  # 2.0 = twice as slow
    noise_scale=1.0,  # audio variation
    noise_w_scale=1.0,  # speaking variation
    normalize_audio=False, # use raw audio from voice
)

with wave.open(args.output_file, "wb") as wav:
    voice.synthesize_wav(args.input, wav, syn_config=syn_config)
    print(f"[{cmd}] Printed output to {args.output_file}", file=sys.stderr)
