import symbolset

# Other matcha-related imports
from argparse import Namespace
import torch

from matcha_utils import(
    intersperse,
    unbatched_synthesis,
)

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
@dataclass
class Synthesizer:
    args: Namespace
    device: str
    model: object
    vocoder: object
    denoiser: object
    spk: object
    phonemizer: object
    symbolset: object
    config: object

    def process_input(self, i: int, input: str, input_type: str, device: torch.device):
        logger.debug(f"process_input [{i}] - Input: {input}")
        matcha_input = input
        if input_type == "text":
            if self.phonemizer is None:
                msg = f"No phonemizer defined for voice {self.args.name}"
                logger.error(msg)
                raise IOError(msg)
            #text = lowercase(text) # TODO
            #text = expand_abbreviations(text) # TODO
            matcha_input = self.phonemizer.phonemize([matcha_input], strip=True, njobs=1)[0]
            logger.info(f"phonemizer output: {matcha_input}")
            # Added in some cases espeak is not removing brackets
            #phonemes = remove_brackets(phonemes) # TODO
            #phonemes = collapse_whitespace(phonemes) # TODO
        invalid = []
        for symbol in matcha_input:
            if not symbol in self.symbolset.symbol2id:
                invalid += symbol
        if len(invalid) > 0:
            raise KeyError(f"Invalid input symbols: {invalid}")
        seq = self.symbolset.text_to_sequence(matcha_input)
        x = torch.tensor(
            intersperse(seq, 0),
            dtype=torch.long,
            device=device,
        )[None]
        x_lengths = torch.tensor([x.shape[-1]], dtype=torch.long, device=device)
        x_phones = self.symbolset.sequence_to_text(x.squeeze(0).tolist())
        logger.info(f"[{i}] - Processed input: {x_phones[1::2]}")
        
        res = {"phonemes": {x_phones[1::2]}, "x_orig": input, "x": x, "x_lengths": x_lengths, "x_phones": x_phones}
        return res
    
    @torch.no_grad()
    def synthesize(self, params):
        args = self.args
        args.speaking_rate = args.speaking_rate * params.speaking_rate
        logger.debug(f"synthesize params: {params}")
        return  unbatched_synthesis(args, self.device, self.model, self.vocoder, self.denoiser, params, self.spk, self.symbolset, self.process_input)

        
