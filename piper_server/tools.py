import sys, os
from pathlib import Path

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from common import log

import json, re

def get_or_else(value1, value2, default=None):
    if value1 is not None:
        return value1
    elif value2 is not None:
        return value2
    else:
        return default

def postmatch_alignments(tokens_processed, tokens_aligned):
    if len(tokens_aligned) == len(tokens_processed):
        for i, t in enumerate(tokens_aligned):
            hidden = tokens_aligned[i].get("hidden", False)
            tokens_aligned[i] = tokens_aligned[i] | tokens_processed[i]
    else: # if they don't match, try the same matching but with empty orth words removed instead
        tokens_processed_nonempty = []
        for i, t in enumerate(tokens_processed):
            if "orth" not in t or t["orth"] == "":
                continue
            else:
                tokens_processed_nonempty.append(t)

        if len(tokens_aligned) == len(tokens_processed_nonempty):
            for i, t in enumerate(tokens_aligned):
                hidden = tokens_aligned[i].get("hidden", False)
                tokens_aligned[i] = tokens_aligned[i] | tokens_processed_nonempty[i]
        else:
            log.debug(f"Unable to match input tokens with aligned tokens! token counts: {len(tokens_processed)} / {len(tokens_aligned)}")
            if len(tokens_processed_nonempty) != len(tokens_processed):
                log.debug(f"Unable to match input tokens with aligned tokens! token counts: {len(tokens_processed_nonempty)} / {len(tokens_aligned)}")
            log.debug(f"Unable to match input tokens with aligned tokens! tokens_processed: {tokens_processed}")
            log.debug(f"Unable to match input tokens with aligned tokens! tokens_aligned: {tokens_aligned}")
    return tokens_aligned
    
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
        #log.debug(f"Created directory: {p}")
    if not os.path.isdir(p):
        raise IOError(f"Couldn't create output folder: {p}")
    return p


def clear_audio(audio_path):
    log.info(f"Clearing audio set to true")
    n=0
    for fn in os.listdir(audio_path):
        file_path = os.path.join(audio_path, fn)
        if os.path.isfile(file_path):
            os.remove(file_path)
            n+=1
            #print(fn, "is removed")
    log.debug(f"Deleted {n} files from folder {audio_path}")
   
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
def input2tokens(input, input_type, lang):
    tokens = None
    if input_type == "tokens":
        tokens = input
    else:
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
    if lang.startswith("sv"):
        if len(tokens) > 0 and tokens[-1].get("orth","") != "":
            tokens.append({"orth": ".", "hidden": True, "prepunct": ",", "phonemes": "."})
        if len(tokens) > 0 and tokens[0].get("orth","") != "":
            tokens.insert(0,{"orth": ".", "hidden": True, "prepunct": ",", "phonemes": "."})
    return tokens


empty_phoneme_re = re.compile("^\\[\\[ *\\]\\]")
def tokens2piper(tokens):
    res = []
    for t in tokens:
        if t in tokens:
            if "phonemes" in t:
                res.append(f"[[ {t['phonemes']} ]]")
            else: #elif "orth" in t:
                res.append(t['orth'])
            # if res[-1] == "":
            #     res[-1] = "."
            # if empty_phoneme_re.match(res[-1]):
            #     res[-1] = "."
    return " ".join(res).replace(" ]] [[ ", " ")
