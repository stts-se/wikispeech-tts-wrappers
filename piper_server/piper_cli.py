## FOR ALIGNED OUTPUT, YOU NEED TO RUN THIS ON A PIPER DEV BUILD FOR 1.3.1 OR HIGHER, NOT THE RELEASED 1.3.0 VERSION
## SEE README FOR INSTALLATION INSTRUCTIONS

import tools

import sys, os
from pathlib import Path

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
lab_file=Path(args.output_file).with_suffix('.lab')

# workaround for Swedish Piper voice
if not (args.input.endswith(" .") or args.input.endswith(" .]]")):
    args.input = args.input + " ."

if not args.onnx_model.endswith(".onnx"):
    args.onnx_model = args.onnx_model + ".onnx"
    
print(f"[{cmd}] Adapted input {args.input}", file=sys.stderr)
voice = PiperVoice.load(args.onnx_model)

syn_config = SynthesisConfig(
    volume=1.0,
    length_scale=1.0,  # 2.0 = twice as slow
    noise_scale=1.0,  # audio variation
    noise_w_scale=1.0,  # speaking variation
    normalize_audio=False, # use raw audio from voice
    #speaker_id=0, # TODO: look up id from speaker name
)
output_dir=os.path.dirname(args.output_file)
basename=Path(os.path.basename(args.output_file)).with_suffix("")
input_type="mixed"
outfilebase = Path(output_dir / basename)
tools.synthesize(voice, args.input, input_type, outfilebase, syn_config)
