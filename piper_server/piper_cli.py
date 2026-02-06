import tools, voice

import sys, os
from pathlib import Path

import wave
from piper import PiperVoice, SynthesisConfig

import argparse

cmd='piper_cli'

print(f"[{cmd}] Work in progress, this client is not working atm", file=sys.stderr)
sys.exit(1)


# parser = argparse.ArgumentParser(
#     prog=cmd,
#     description='A simple piper client',
# )

# parser.add_argument('onnx_model')
# parser.add_argument('input')
# parser.add_argument('output_file')

# args = parser.parse_args()




# # workaround for Swedish Piper voice
# if not (args.input.endswith(" .") or args.input.endswith(" .]]")):
#     args.input = args.input + " ."

# if not args.onnx_model.endswith(".onnx"):
#     args.onnx_model = args.onnx_model + ".onnx"
    
# print(f"[{cmd}] Adapted input {args.input}", file=sys.stderr)

# v = voice.Voice(name=args.onnx_model,
#                 enabled=True,
#                 config=None,
#                 piper_voice=None,
#                 model=None, # tools.find_file(voice_config['model'], result.model_paths),
#                 length_scale=1.0,#args.length_scale,#1.0),
#                 noise_scale=1.0,#args.noise_scale,#1.0),
#                 noise_w_scale=1.0,#args.noise_w_scale,#1.0),                                                                
#                 speaker_id=None,#args.speaker_id,#None),
#                 phonemizers=[],
#                 selected_phonemizer_index=0)
# v.load(["."])

# output_dir=os.path.dirname(args.output_file)
# basename=Path(os.path.basename(args.output_file)).with_suffix("")
# input_type="mixed"
# outfilebase = Path(output_dir / basename)
# v.synthesize_all([args.input], input_type, outfilebase, syn_config)
