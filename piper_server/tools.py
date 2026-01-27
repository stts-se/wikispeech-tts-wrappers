import sys, os
from pathlib import Path

import json, re

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

def get_or_else(value1, value2, default=None):
    if value1 is not None:
        return value1
    elif value2 is not None:
        return value2
    else:
        return default

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

# if the same model/file is found in multiple paths, the first one will be used
def find_file(name, paths):
    for p in paths:
        f = os.path.join(p, name)
        if os.path.isfile(f):
            return f
    return None

def create_path(p,create=True):
    p = os.path.expandvars(p)
    if create:
        folder = Path(p)
        folder.mkdir(exist_ok=True, parents=True)
        #logger.debug(f"Created directory: {p}")
    if not os.path.isdir(p):
        raise IOError(f"Couldn't create output folder: {p}")
    return p


def clear_audio(audio_path):
    get_logger().info(f"Clearing audio set to true")
    n=0
    for fn in os.listdir(audio_path):
        file_path = os.path.join(audio_path, fn)
        if os.path.isfile(file_path):
            os.remove(file_path)
            n+=1
            #print(fn, "is removed")
    get_logger().debug(f"Deleted {n} files from folder {audio_path}")
   
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
        

phoneme_input_re = re.compile("\\[\\[(.*)\\]\\]")
separate_comma_re = re.compile("(^|[^\\[]) *, *($|[^\\]])")
wordsplit=re.compile(" +")
def input2tokens(input, input_type):
    if input_type == "tokens":
        # workaround for Swedish Piper voice
        input.append({"orth": "."})
        return input

    tokens = []
    s = input
    s = separate_comma_re.sub("\\1 , \\2",s)
    if input_type == "phonemes":
        for w in wordsplit.split(s):
            tokens.append({"phonemes": w})
    elif input_type == "mixed":
        for w in wordsplit.split(s):
            m = phoneme_input_re.match(w)
            if m:
                tokens.append({"phonemes": m.group(1)})
            else:
                tokens.append({"orth": w})
    else: # text input
        for w in wordsplit.split(s):
            tokens.append({"orth": w})
    # workaround for Swedish Piper voice
    tokens.append({"orth": "."})
    return tokens


def tokens2piper(tokens):
    res = []
    for t in tokens:
        if t in tokens:
            if "phonemes" in t:
                res.append(f"[[ {t['phonemes']} ]]")
            else:
                res.append(t['orth'])
    return " ".join(res).replace(" ]] [[ ", " ")
