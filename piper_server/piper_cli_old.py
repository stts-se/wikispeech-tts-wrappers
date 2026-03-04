## NEEDS TO RUN ON A PIPER DEV BUILD, NOT THE PRE-INSTALLED 1.3.0 VERSION

import sys
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
)
set_wav_format = True

alignments = []
piper_alignments_enabled = True

with wave.open(args.output_file, "wb") as wav_file:
    chunks = []
    try:
        chunks = voice.synthesize(args.input, syn_config=syn_config, include_alignments=True)
    except TypeError as e:
            print(f"[{cmd}] Got TypeError from voice.synthesize: {e}. Likely caused by running on piper release 1.3.0 instead of a dev build (because of alignment dependency). Alignment output will be disabled.", file=sys.stderr)    
            chunks = voice.synthesize(args.input, syn_config=syn_config)
            piper_alignments_enabled = False
            #sys.exit(1)

    first_chunk = True
    for audio_chunk in chunks:
        if first_chunk:
            if set_wav_format:
                # Set audio format on first chunk
                wav_file.setframerate(audio_chunk.sample_rate)
                wav_file.setsampwidth(audio_chunk.sample_width)
                wav_file.setnchannels(audio_chunk.sample_channels)

            first_chunk = False

            wav_file.writeframes(audio_chunk.audio_int16_bytes)
            print(f"[{cmd}] Saved output to {args.output_file}", file=sys.stderr)

            if piper_alignments_enabled and audio_chunk.phoneme_alignments:
                alignments.extend(audio_chunk.phoneme_alignments)

if piper_alignments_enabled and len(alignments) == 0:
    print(f"[{cmd}] WARNING: No alignments in output from synthesize_wav. This is probably because the model is not alignment-enabled. See https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md for information on how to enable alignments", file=sys.stderr)
    sys.exit(0)

if not piper_alignments_enabled:
    #print(f"[{cmd}] No .lab file output", file=sys.stderr)
    sys.exit(0)

# ALIGNMENT
at_sample = 0
current_word = {
    "phonemes": "",
    "start_time": 0.0,
    "start_sample": 0
}
words = []
total_samples = 0

for ali in alignments:
        total_samples += ali.num_samples
        phn = ali.phoneme
        sample_start = at_sample
        sample_end = at_sample+int(ali.num_samples)
        if at_sample == 0 and phn == "^": # exclude chunk start label from aligned words
            sample_start = sample_end # float(at_sample + sample_end)/2
            current_word["start_sample"] = sample_start
            current_word["start_time"] = sample_start/audio_chunk.sample_rate
            at_sample = sample_end
            continue
        if phn == "$":
            #at_sample = sample_end
            continue
        if phn == " ":
            current_word["end_time"] = sample_end/audio_chunk.sample_rate
            current_word["end_sample"] = sample_end
            words.append(current_word)
            current_word = {
                "phonemes": "",
                "start_time": sample_end/audio_chunk.sample_rate,
                "start_sample": sample_end,
            }
        else:
            current_word['phonemes'] += phn
        at_sample = sample_end

if len(current_word["phonemes"]) > 0:
    current_word["end_time"] = at_sample/audio_chunk.sample_rate
    current_word["end_sample"] = at_sample
    words.append(current_word)

with open(lab_file, "w") as f:
    for w in words:
        f.write(f"{w['start_time']}\t{w['end_time']}\t{w['phonemes']}\n")
print(f"[{cmd}] Saved alignment to {lab_file}", file=sys.stderr)
