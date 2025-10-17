from piper import PiperVoice
import wave

import os

from piper_phonemize import phonemize_codepoints, phonemize_espeak, tashkeel_run

from typing import Iterable, List, Optional, Union

class Voice:
    pvoice: PiperVoice
    def __init__(self, pv: PiperVoice):
        self.pvoice = pv
       
    def phonemize(self, text: str) -> List[List[str]]:
        """Text to phonemes grouped by sentence."""
        #print(self.pvoice.config.phoneme_type)
        # TODO: piper fails if espeak voice is not defined
        if self.pvoice.config.espeak_voice == "ar":
            # Arabic diacritization
            # https://github.com/mush42/libtashkeel/
            text = tashkeel_run(text)
            
        return phonemize_espeak(text, self.pvoice.config.espeak_voice)
        #raise ValueError(f"Unexpected phoneme type: {self.pvoice.config.phoneme_type}")

    def synthesize_phonemes(
        self,
        sentence_phonemes: Iterable[str],
        wav_file: str,
        speaker_id: Optional[int] = None,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w: Optional[float] = None,
        sentence_silence: float = 0.0,
    ):
        """Synthesize WAV audio from phonemes."""
        
        with wave.open(wav_file, "wb") as wf:
            wf.setframerate(self.pvoice.config.sample_rate)
            wf.setsampwidth(2)  # 16-bit
            wf.setnchannels(1)  # mono

            for audio_bytes in self.synthesize_phonemes_raw(
                    sentence_phonemes,
                    speaker_id=speaker_id,
                    length_scale=length_scale,
                    noise_scale=noise_scale,
                    noise_w=noise_w,
                    sentence_silence=sentence_silence,
            ):
                wf.writeframes(audio_bytes)

    def synthesize_phonemes_raw(
        self,
        sentence_phonemes: Iterable[str],
        speaker_id: Optional[int] = None,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w: Optional[float] = None,
        sentence_silence: float = 0.0,
    ) -> Iterable[bytes]:
        """Synthesize raw audio from a phoneme sequence."""

        # 16-bit mono
        num_silence_samples = int(sentence_silence * self.pvoice.config.sample_rate)
        silence_bytes = bytes(num_silence_samples * 2)

        for phonemes in sentence_phonemes:
            phoneme_ids = self.pvoice.phonemes_to_ids(phonemes)
            yield self.pvoice.synthesize_ids_to_raw(
                phoneme_ids,
                speaker_id=speaker_id,
                length_scale=length_scale,
                noise_scale=noise_scale,
                noise_w=noise_w,
            ) + silence_bytes

    def process_input(self, input, input_type, output_dir, basename, synthesize_args):
        wav_file = os.path.join(output_dir,f"{basename}.wav")
        if input_type=='phonemes':
            phoneme_input = [input]
            phoneme_str = input
        else:
            phonemes = self.phonemize(input)
            phoneme_input = phonemes
            phoneme_str = ''.join([''.join(x) for x in phonemes])
        self.synthesize_phonemes(sentence_phonemes=phoneme_input, wav_file=wav_file, **synthesize_args)
        entry = {
            'input': input,
            'phonemes': phoneme_str,
            'audio': wav_file,
        }
        import shutil
        shutil.copy(wav_file,os.path.join(output_dir, "latest.wav"))
        
        import json
        json_file = os.path.join(output_dir, f"{basename}.json")
        with open(json_file, 'w') as f:
            json.dump(entry, f, ensure_ascii=False, indent=4)
        return entry
    
