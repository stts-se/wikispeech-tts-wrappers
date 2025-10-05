# Logging
import logging
logger = logging.getLogger('matcha')

logger.debug("Starting Matcha imports...")
from matcha.utils.utils import intersperse
from matcha.cli import to_waveform, save_to_folder, load_matcha, load_vocoder
import torch
logger.debug("    ... Matcha imports completed")

# Imports from this repo
import alignment, tools

import sys, os, re
from pathlib import Path
import json

phoneme_input_re = re.compile("\\[\\[(.*)\\]\\]")

from dataclasses import dataclass, asdict
@dataclass
class Voice:
    name: str
    model: str
    vocoder: str

    steps: int
    temperature: float
    denoiser_strength: float
    device: str

    speaking_rate: float
    speaker: object
    symbols: str
    
    phonemizers: list
    selected_phonemizer_index: int

    def __post_init__(self):
        self.SPACE_ID = self.symbols.index(" ")
        
        # Mappings from symbol to numeric ID and vice versa:
        self.symbol2id = {s: i for i, s in enumerate(self.symbols)}
        self.id2symbol = {i: s for i, s in enumerate(self.symbols)}  # pylint: disable=unnecessary-comprehension

        self.loaded = False
        self.matcha_model = None
        self.matcha_vocoder = None
        self.matcha_denoiser = None
    
    def __str__(self):
        dict = asdict(self)
        return f"{dict}"

    def as_json(self):
        obj = {
            "name": self.name,
            "model": self.model,
            "vocoder": self. vocoder,
            "steps": self.steps,
            "temperature": self.temperature,
            "denoiser_strength": self.denoiser_strength,
            "device": self.device,
            
            "speaking_rate": self.speaking_rate,
            "speaker": self.speaker,
            "symbols": "".join(self.symbols),

            "phonemizers": list(map(lambda p: p.as_json(), self.phonemizers)),
            "selected_phonemizer": self.selected_phonemizer().name
        }
        return obj

    def validate(self, fail_on_error = True):
        if self.speaking_rate < -1.0 or self.speaking_rate > 5.0:
            msg = f"Invalid speaking rate: {self.speaking_rate} (expected -1.0 < speaking_rate < 5.0)"
            if fail_on_error:
                raise Exception(msg)
            else:
                logger.error(msg)
        if self.symbols == "":
            msg = f"No symbols defined for voice {self.name}"
            if fail_on_error:
                raise Exception(msg)
            else:
                logger.error(msg)

    def cleaned_text_to_sequence(self, cleaned_text):
        """Converts a string of text to a sequence of IDs corresponding to the symbols in the text.
        Args:
          text: string to convert to a sequence
        Returns:
          List of integers corresponding to the symbols in the text
        """
        sequence = [self.symbol2id[symbol] for symbol in cleaned_text]
        return sequence


    def sequence_to_text(self, sequence):
        """Converts a sequence of IDs back to a string"""
        result = ""
        for symbol_id in sequence:
            s = self.id2symbol[symbol_id]
            result += s
        return result

    def selected_phonemizer(self):
        return self.phonemizers[self.selected_phonemizer_index]
    
    def process_text(self, input: str, input_type: str):
        #print(f"[{i}] - Input text: {input}")

        s = input
        s = s.replace(".","")

        words = []
        if input_type == "text":
            phn_list = []
            for w in s.split(" "):
                result = self.selected_phonemizer().phonemize(w)
                phn_list.append(result)
                words.append({
                    "input": w,
                    "orth": w,
                    "phonemes": result
                })
            phn = " ".join(phn_list)
            cleaned_text = self.cleaned_text_to_sequence(phn)
        elif input_type == "mixed":
            phn_list = []
            for w in s.split(" "):
                m = phoneme_input_re.match(w)
                if m:
                    phn_list.append(m.group(1))
                    words.append({
                        "input": w,
                        "phonemes": m.group(1)
                    })
                else:
                    result = self.selected_phonemizer().phonemize(w)
                    phn_list.append(result)
                    words.append({
                        "input": w,
                        "orth": w,
                        "phonemes": result
                    })
            phn = " ".join(phn_list)
            cleaned_text = self.cleaned_text_to_sequence(phn)
        else:
            for w in s.split(" "):
                words.append({"phonemes": w})
            cleaned_text = self.cleaned_text_to_sequence(input)

        x = torch.tensor(
            intersperse(cleaned_text, 0),
            dtype=torch.long,
            device=self.device,
        )[None]
        x_lengths = torch.tensor([x.shape[-1]], dtype=torch.long, device=self.device)
        x_phones = self.sequence_to_text(x.squeeze(0).tolist())
        #print(f"[{i}] - Phonetised text: {x_phones[1::2]}")
        return {"words": words, "x_orig": input, "x": x, "x_lengths": x_lengths, "x_phones": x_phones}

    def synthesize_all(self, inputs, input_type, output_folder, params):
        import uuid
        uid = uuid.uuid4()
        res = []
        i = 0
        spk_id = tools.get_or_else(vars(params).get("speaker"), self.speaker)
        for input in inputs:
            input = input.strip()
            i = i+1
            base_name = f"utt_{uid}_{i:03d}_spk_{spk_id:03d}" if spk_id is not None else f"utt_{uid}_{i:03d}"
            output_file = os.path.join(output_folder, base_name)
            res.append(self.synthesize(input, input_type, output_file, params))
        if len(res) > 0:
            copy_to_latest(res[len(res)-1],output_folder)
        return res
    
    def synthesize(self, input, input_type, output_file, params):
        output_name = os.path.basename(output_file)
        output_name = Path(output_name).with_suffix('')
        output_folder = os.path.dirname(output_file)
            
        if not self.loaded:
            checkpoint_path = Path(self.model)
            vocoder_name = os.path.basename(self.vocoder)
            self.matcha_model = load_matcha(self.model, checkpoint_path, self.device)
            self.matcha_vocoder, self.matcha_denoiser = load_vocoder(vocoder_name, self.vocoder, self.device)
            self.loaded = True

        ### SYNTHESIZE
        text_processed = self.process_text(input, input_type)
        spk_id = tools.get_or_else(vars(params).get("speaker"), self.speaker, None)

        spk = torch.tensor([spk_id],device=self.device) if spk_id is not None else None
        output = self.matcha_model.synthesise(
            text_processed["x"],
            text_processed["x_lengths"],
            n_timesteps=self.steps,
            temperature=self.temperature,
            spks=spk,
            length_scale=tools.get_or_else(vars(params).get("speaking_rate"), self.speaking_rate),
        )

        ## PROCESS ALIGNMENT
        import alignment
        id2symbol={i: s for i, s in enumerate(self.symbols)} 
        tokens = text_processed['words']

        phonemes = []
        for token in tokens:
            if "phonemes" in token:
                phonemes.append(token["phonemes"])
        aligned = alignment.align(text_processed, output, self.id2symbol)
        logger.debug(f"ALIGNED {aligned}")
        if len(tokens) == len(aligned):
            for idx, w in enumerate(tokens):
                tokens[idx] = tokens[idx] | aligned[idx]
                    
        result = {
            "input": input,
            "input_type": input_type,
            "speaking_rate": params.speaking_rate,
            "speaker_id": spk_id,         
        }
        if len(phonemes) > 0:
            result["phonemes"]=" ".join(phonemes)
        result["tokens"] = tokens
        result["audio"] = f"{Path(os.path.basename(output_file)).with_suffix('.wav')}"

        ## SAVE OUTPUT

        # json file
        json_output = Path(output_file).with_suffix('.json')
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            logger.debug(f"JSON output saved: {json_output}")

        # wav file
        with torch.no_grad():
            output["waveform"] = to_waveform(output["mel"], self.matcha_vocoder, self.matcha_denoiser, self.denoiser_strength)

        location = save_to_folder(output_name, output, output_folder)
        logger.debug(f"Waveform saved: {location}")

        # label file
        lab_file = os.path.join(output_folder, f"{output_name}.lab")
        with open(lab_file, "w") as f:
            for token in result['tokens']:
                f.write(f"{token['start_time']}\t{token['end_time']}\t{token['phonemes']}\n")

        return result


def copy_to_latest(result,output_folder):
    basename = Path(result["audio"]).with_suffix("")

    wav_file = os.path.join(output_folder, basename.with_suffix('.wav'))
    png_file = os.path.join(output_folder, basename.with_suffix('.png'))
    lab_file = os.path.join(output_folder, basename.with_suffix('.lab'))

    latest_json = result.copy()
    latest_json['audio'] = "latest.wav"
    with open(os.path.join(output_folder, "latest.json"), 'w') as f:
        json.dump(latest_json, f, ensure_ascii=False, indent=4)
        
    output_files = {
        wav_file: os.path.join(output_folder, "latest.wav"),
        png_file: os.path.join(output_folder, "latest.png"),
        lab_file: os.path.join(output_folder, "latest.lab")
    }
    import shutil
    for source, dest in output_files.items():
        shutil.copy(source, dest)
        
