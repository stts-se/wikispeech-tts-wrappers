# pylint: disable=C0301,W1203,C0114,C0116,E0118,W0603

import os
import re
import json
from pathlib import Path
import logging
import shutil

LOGGER = None

def get_logger(name="matcha"):
    global LOGGER
    if LOGGER is not None:
        return LOGGER
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    LOGGER = logging.getLogger(name)
    logging.getLogger(name).setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s:%(filename)s - %(levelname)s - %(message)s')
    return LOGGER


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
        #LOGGER.debug(f"Created directory: {p}")
    if not os.path.isdir(p):
        raise IOError(f"Couldn't create output folder: {p}")
    return p


def clear_audio(audio_path):
    get_logger().info("Clearing audio set to true")
    n=0
    for fn in os.listdir(audio_path):
        file_path = os.path.join(audio_path, fn)
        if os.path.isfile(file_path):
            os.remove(file_path)
            n+=1
            #print(fn, "is removed")
    get_logger().debug(f"Deleted {n} files from folder {audio_path}")

def get_or_else(value1, value2, default=None):
    if value1 is not None:
        return value1
    if value2 is not None:
        return value2
    return default

def copy_to_latest(result,output_folder):
    basename = Path(result["audio"]).with_suffix("")

    wav_file = os.path.join(output_folder, basename.with_suffix('.wav'))
    png_file = os.path.join(output_folder, basename.with_suffix('.png'))
    lab_file = os.path.join(output_folder, basename.with_suffix('.lab'))

    latest_json = result.copy()
    latest_json['audio'] = "latest.wav"
    with open(os.path.join(output_folder, "latest.json"), 'w', encoding="utf-8") as f:
        json.dump(latest_json, f, ensure_ascii=False, indent=4)

    output_files = {
        wav_file: os.path.join(output_folder, "latest.wav"),
        png_file: os.path.join(output_folder, "latest.png"),
        lab_file: os.path.join(output_folder, "latest.lab")
    }
    for source, dest in output_files.items():
        if os.path.isfile(source):
            shutil.copy(source, dest)

phoneme_input_re = re.compile("\\[\\[(.*)\\]\\]")
separate_comma_re = re.compile("(^|[^\\[]) *, *($|[^\\]])")
wordsplit=re.compile(" +")
def input2tokens(input_string, input_type):
    if input_type == "tokens":
        return input_string

    tokens = []
    s = input_string
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
    return tokens
