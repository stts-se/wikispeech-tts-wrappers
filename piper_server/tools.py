import sys, os
from pathlib import Path

import json

import wave
from piper import PiperVoice, SynthesisConfig

logger = None
def get_logger(name="piper"):
    global logger
    if logger is not None:
        return logger
    import logging
    #logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logger = logging.getLogger(name)
    logging.getLogger(name).setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s:%(filename)s - %(levelname)s - %(message)s')
    return logger
logger=get_logger()

# TODO input as tokens
def synthesize(voice, input, input_type, output_dir, basename, syn_config):
    set_wav_format = True

    logger.debug(f"syn_config: {syn_config}")
    
    wav_file=str(Path(Path(output_dir) / basename).with_suffix('.wav'))
    lab_file=str(Path(Path(output_dir) / basename).with_suffix('.lab'))

    alignments = []
    piper_alignments_enabled = True
    sample_rate = None

    adapted_input = input
    if input_type == "phonemes":
        adapted_input = f"[[ {input} ]]"
    elif input_type == "tokens":
        adapted_inputs = []
        for chunk in input:
            for t in chunk: # TODO: keep nested structure in output?
                if "phonemes" in t:
                    adapted_inputs.append(f"[[ {t['phonemes']} ]]")
                else:
                    adapted_inputs.append(t['orth'])
        adapted_input = " ".join(adapted_inputs)

    logger.debug(f"Adapted input: {adapted_input}")
        
    with wave.open(wav_file, "wb") as wf:
        chunks = []
        try:
            chunks = voice.synthesize(adapted_input, syn_config=syn_config, include_alignments=piper_alignments_enabled)
        except TypeError as e:
                logger.warning(f"Got TypeError from voice.synthesize: {e}. Likely caused by running on piper release 1.3.0 rather than a dev build (because of alignment dependency). Alignment output will be disabled.")    
                chunks = voice.synthesize(adapted_input, syn_config=syn_config)
                piper_alignments_enabled = False

        first_chunk = True
        for audio_chunk in chunks:
            sample_rate = audio_chunk.sample_rate
            if first_chunk and set_wav_format:
                # Set audio format on first chunk
                wf.setframerate(audio_chunk.sample_rate)
                wf.setsampwidth(audio_chunk.sample_width)
                wf.setnchannels(audio_chunk.sample_channels)
            first_chunk = False

            wf.writeframes(audio_chunk.audio_int16_bytes)
            logger.info(f"Saved audio to {wav_file}")

            if piper_alignments_enabled and audio_chunk.phoneme_alignments:
                alignments.extend(audio_chunk.phoneme_alignments)

    if piper_alignments_enabled and len(alignments) == 0:
        logger.warning(f" No alignments in output from synthesize_wav. This is probably because the model is not alignment-enabled. See https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md for information on how to enable alignments.")
        #return
                
    result = {
        "input": input,
        "adapted_input": adapted_input,
        "input_type": input_type,
        "tts_config": syn_config
    }

    if piper_alignments_enabled:
        tokens = align(alignments, sample_rate)
        result["tokens"] = tokens
    result["audio"] = wav_file

    # json file
    json_obj = result
    json_obj["tts_config"] = {
        "volume": syn_config.volume,
        "length_scale": syn_config.length_scale,
        "noise_scale": syn_config.noise_scale,
        "noise_w_scale": syn_config.noise_w_scale,
        "normalize_audio": syn_config.normalize_audio,
        "speaker_id": syn_config.speaker_id,
    }
    json_output = Path(wav_file).with_suffix('.json')
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        logger.debug(f"JSON output saved: {wav_file}")

    # lab file
    with open(lab_file, "w") as f:
        for t in tokens:
            f.write(f"{t['start_time']}\t{t['end_time']}\t{t['phonemes']}\n")


    copy_to_latest(result, output_dir)    
    return result

    
def align(alignments, sample_rate):
    at_sample = 0
    current_token = {
        "phonemes": "",
        "start_time": 0.0,
        #"start_sample": 0
    }
    tokens = []
    total_samples = 0
    
    for ali in alignments:
            total_samples += ali.num_samples
            phn = ali.phoneme
            sample_start = at_sample
            sample_end = at_sample+int(ali.num_samples)
            if at_sample == 0 and phn == "^": # exclude chunk start label from aligned tokens
                sample_start = sample_end # float(at_sample + sample_end)/2
                #current_token["start_sample"] = sample_start
                current_token["start_time"] = sample_start/sample_rate
                at_sample = sample_end
                continue
            if phn == "$":
                #at_sample = sample_end
                continue
            if phn == " ":
                current_token["end_time"] = sample_end/sample_rate
                #current_token["end_sample"] = sample_end
                tokens.append(current_token)
                current_token = {
                    "phonemes": "",
                    "start_time": sample_end/sample_rate,
                    #"start_sample": sample_end,
                }
            else:
                current_token['phonemes'] += phn
            at_sample = sample_end

    if len(current_token["phonemes"]) > 0:
        current_token["end_time"] = at_sample/sample_rate
        #current_token["end_sample"] = at_sample
        tokens.append(current_token)

    return tokens

def copy_to_latest(result, output_folder):
    basename = Path(result["audio"]).with_suffix("")

    wav_file = os.path.join(output_folder, basename.with_suffix('.wav'))
    lab_file = os.path.join(output_folder, basename.with_suffix('.lab'))

    latest_json = result.copy()
    latest_json['audio'] = "latest.wav"
    with open(os.path.join(output_folder, "latest.json"), 'w') as f:
        json.dump(latest_json, f, ensure_ascii=False, indent=4)
        
    output_files = {
        wav_file: os.path.join(output_folder, "latest.wav"),
        lab_file: os.path.join(output_folder, "latest.lab")
    }
    import shutil
    for source, dest in output_files.items():
        if os.path.isfile(source): 
            shutil.copy(source, dest)
        
