## NEEDS TO RUN ON A PIPER DEV BUILD, NOT THE PRE-INSTALLED 1.3.0 VERSION

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

    
# ALIGNMENT
at_sample = 0
current_word = {
    "phonemes": "",
    "start_time": 0.0,
    "start_sample": 0
}
words = []
total_samples = 0

chunks = []
try:
    chunks = voice.synthesize(args.input,syn_config=syn_config,include_alignments=True)
except TypeError as e:
    print(f"[{cmd}] FATAL ERROR: TypeError {e} - likely caused by running on piper release 1.3.0 instead of a dev build (because of alignment dependency)", file=sys.stderr)    
    sys.exit(1)

for chunk in chunks:
    for ali in chunk.phoneme_alignments:
        total_samples += ali.num_samples
        print(f"{ali.phoneme}\t{int(ali.num_samples)}\t{total_samples}")
        #print(ali)
#         phn = alignment.phoneme
#         sample_start = at_sample
#         sample_end = at_sample+int(alignment.num_samples)
#         if phn == " ":
#             #sample_end = at_sample+int(alignment.num_samples-at_sample)/2
#             current_word["end_time"] = sample_end/chunk.sample_rate
#             current_word["end_sample"] = sample_end
#             words.append(current_word)
#             current_word = {
#                 "phonemes": "",
#                 "start_time": sample_end/chunk.sample_rate,
#                 "start_sample": sample_end,
#             }
#         else:
#             current_word['phonemes'] += phn
#         #set_audio_format(chunk.sample_rate, chunk.sample_width, chunk.sample_channels)
#         #write_raw_data(chunk.audio_int16_bytes)
#         at_sample = sample_end

# print("??", total_samples)
# current_word["end_time"] = at_sample/chunk.sample_rate
# current_word["end_sample"] = at_sample
# words.append(current_word)
# for w in words:
#     #print(w)
#     # .lab output
#     print(f"{w['start_time']}\t{w['end_time']}\t{w['phonemes']}")
