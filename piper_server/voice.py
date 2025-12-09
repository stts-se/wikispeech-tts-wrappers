# Imports from this repo
import tools

# Logging
logger = tools.get_logger()

from piper import PiperVoice, SynthesisConfig
import wave

import sys, os, re
from pathlib import Path
import json

phoneme_input_re = re.compile("\\[\\[(.*)\\]\\]")
separate_comma_re = re.compile("(^|[^\\[]) *, *($|[^\\]])")
wordsplit=re.compile(" +")

from dataclasses import dataclass, asdict
@dataclass
class Voice:
    name: str
    enabled: bool
    config: object

    model: str
    piper_voice: PiperVoice
    
    speaker_id: int
    length_scale: float
    noise_scale: float
    noise_w_scale: float
    
    phonemizers: list
    selected_phonemizer_index: int

    def __post_init__(self):
        self.loaded = False
    
    def __str__(self):
        dict = asdict(self)
        return f"{dict}"

    def as_json(self):
        phner = None
        if self.selected_phonemizer() is not None:
            phner = self.selected_phonemizer().name
        obj = {
            "name": self.name,
            "model": self.model,

            "length_scale": self.length_scale,
            "noise_scale": self.noise_scale,
            "noise_w_scale": self.noise_w_scale,            
            #"speaker_id": self.speaker_id,

            "phonemizers": list(map(lambda p: p.as_json(), self.phonemizers)),
            "selected_phonemizer": phner
        }
        return obj

    def load(self, model_paths):
        if not self.enabled:
            logger.error("Cannot load voice {self.name} (voice not enabled)")
            return
        phonemizers = []
        defaultPhnIndex = 0
        for i, phizer in enumerate(self.config['phonemizers']):
            if phizer.get('enabled', True):
                if phizer.get('default', False):
                    defaultPhnIndex = i
                if phizer['type'] == "deep_phonemizer":
                    model_path = tools.find_file(phizer['model'], model_paths)
                    if model_path is None:
                        raise Exception(f"Couldn't find model {phizer['model']} for {phizer['name']}. Looked in {model_paths}")
                    phonemizers.append(Phonemizer(phizer['name'], phizer['type'], phizer['lang'], model_path))
                elif phizer['type'] == "espeak":
                    phonemizers.append(Phonemizer(phizer['name'], phizer['type'], phizer['lang']))
                else:
                    raise Exception(f"Unknown phonemizer type {type} for {phizer['name']}")

        if len(phonemizers) == 0:
            raise Exception(f"Couldn't find phonemizer for voice '{self.config['name']}' in config file {config_file}")

        onnx_fn = str(Path(self.config['model']).with_suffix(".onnx"))
        model_path = tools.find_file( onnx_fn, model_paths)
        cuda = False
        config = None # Explicit path to config file, but we should always have the config file stored with the onnx model
        piper_voice = PiperVoice.load(model_path, config, cuda)

        self.piper_voice = piper_voice
        self.phonemizers=phonemizers
        self.selected_phonemizer_index=defaultPhnIndex
        onnx_fn = str(Path(self.config['model']).with_suffix(".onnx"))
        self.model_path = tools.find_file(onnx_fn, model_paths)
        self.loaded = True
        logger.debug(f"Loaded voice {self.name}")
    
    def validate(self, fail_on_error = True):
        if self.length_scale < -1.0 or self.length_scale > 5.0:
            msg = f"Invalid length scale: {self.length_scale} (expected -1.0 < speaking_rate < 5.0)"
            if fail_on_error:
                raise Exception(msg)
            else:
                logger.error(msg)

    def selected_phonemizer(self):
        if len(self.phonemizers) > 0:
            return self.phonemizers[self.selected_phonemizer_index]
        else:
            return None
    
    def process_tokens(self, tokens: str):
        res = []

        for t in tokens:
            w = {}
            if "orth" in t:
                w["orth"] = t["orth"]
            if "lang" in t:
                w["lang"] = t["lang"]
            if "g2p_method" in t:
                w["g2p_method"] = t["g2p_method"]
            if "phonemes" in t:
                w["input"] =  t["phonemes"]
                w["phonemes"] =  t["phonemes"]
            else:
                lang = w.get("lang", None)
                phner = self.selected_phonemizer()
                result = phner.phonemize(t["orth"], lang)
                w["input"] = t["orth"]
                w["phonemes"] = result
                w["g2p_method"] = phner.tpe
            res.append(w)
        return res
        
    def synthesize_all(self, inputs, input_type, output_folder, params):
        import uuid
        uid = uuid.uuid4()
        res = []
        i = 0
        spk_id = tools.get_or_else(vars(params).get("speaker_id"), self.speaker_id)
        for input in inputs:
            i = i+1
            base_name = f"utt_{uid}_{i:03d}_spk_{spk_id:03d}" if spk_id is not None else f"utt_{uid}_{i:03d}"
            output_file = os.path.join(output_folder, base_name)
            res.append(self.synthesize(input, input_type, output_file, params))
        if len(res) > 0:
            tools.copy_to_latest(res[len(res)-1],output_folder)
        return res

    def synthesize(self, input, input_type, output_file, syn_config):
        if not self.loaded:
            return None
            
        input_tokens = tools.input2tokens(input, input_type)
        
        set_wav_format = True
        tokens_processed = self.process_tokens(input_tokens)
        piper_input = tools.tokens2piper(tokens_processed)

        logger.debug(f"syn_config: {syn_config}")

        wav_file=str(Path(output_file).with_suffix('.wav'))
        lab_file=str(Path(output_file).with_suffix('.lab'))

        alignments = []
        piper_alignments_enabled = True
        sample_rate = None

        logger.debug(f"Input: {input}")
        logger.debug(f"Piper input: {piper_input}")

        with wave.open(wav_file, "wb") as wf:
            chunks = []
            try:
                chunks = self.piper_voice.synthesize(piper_input, syn_config=syn_config, include_alignments=piper_alignments_enabled)
            except TypeError as e:
                    logger.warning(f"Got TypeError from voice.synthesize: {e}. Likely caused by running on piper release 1.3.0 rather than a dev build (because of alignment dependency). Alignment output will be disabled.")    
                    chunks = self.piper_voice.synthesize(piper_input, syn_config=syn_config)
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
                logger.info(f"Audio saved to {wav_file}")

                if piper_alignments_enabled and audio_chunk.phoneme_alignments:
                    alignments.extend(audio_chunk.phoneme_alignments)

        if piper_alignments_enabled and len(alignments) == 0:
            logger.warning(f" No alignments in output from synthesize_wav. This is probably because the model is not alignment-enabled. See https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md for information on how to enable alignments.")
            #return

        result = {
            "input": input,
            "input_type": input_type,
            "tts_config": syn_config
        }

        if piper_alignments_enabled:
            tokens = tools.align(alignments, sample_rate)
            if len(tokens) == len(tokens_processed):
                for i, t in enumerate(tokens):
                    tokens[i] = tokens[i] | tokens_processed[i]
            result["tokens"] = tokens
        result["audio"] = os.path.basename(wav_file)

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
            logger.info(f"JSON saved to {json_output}")

        # lab file
        with open(lab_file, "w") as f:
            for t in tokens:
                f.write(f"{t['start_time']}\t{t['end_time']}\t{t['phonemes']}\n")
        logger.info(f"Label style output saved to {lab_file}")

        return result



class Phonemizer:
    name: str
    tpe: str
    lang: str
    pher: object
    def __init__(self, name, tpe, lang, path=None):
        self.name = name
        self.tpe = tpe
        self.lang = lang
        self.path = path
        try:
            if tpe == "deep_phonemizer":
                from dp.phonemizer import Phonemizer
                if path is None:
                    raise Exception(f"Deep phonemizer {name} cannot be loaded without a model path. Found None")
                if not os.path.isfile(self.path):
                    raise Exception(f"Model path for deep phonemizer {name} does not exist: {path}")
                self.pher = Phonemizer.from_checkpoint(path)
                logger.debug(f"Loaded dp phonemizer {self.pher}")
            elif tpe == "espeak":
                import phonemizer
                self.pher = phonemizer.backend.EspeakBackend(
                    language=lang,
                    preserve_punctuation=True,
                    with_stress=True,
                    language_switch="remove-flags",
                    logger=logger,
                )
                logger.debug(f"Loaded espeak phonemizer {self.pher}")
            else:
                raise Exception(f"Unknown phonemizer type {typ} for {selfname}")
        except RuntimeError as e:
            msg = f"Couldn't load phonetizer for voice {name}: {e}. Voice will not be loaded."
            logger.error(msg)


    def as_json(self):
        obj = {
            "name": self.name,
            "type": self.tpe,
            "lang": self.lang,
            "path": self.path,
        }
        return obj

    def phonemize(self, input, lang=None):
        if self.tpe == "deep_phonemizer":
            if lang is None:
                lang = self.lang
            else:
                if lang not in self.pher.predictor.text_tokenizer.languages:
                    logger.info(f"Language {lang} is not supported by phonemizer. Using {self.lang} instead")
                    lang = self.lang
            return self.pher(input, lang)
        else:
            return self.pher.phonemize([input], strip=True, njobs=1)[0]

    def __str__(self):
        return f"(name={self.name},lang={self.lang},model={self.path})"
