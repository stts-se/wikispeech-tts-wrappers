import torch

import tools
logger = tools.get_logger()

# Constants
HOP_LENGTH = 256            # Typically 256 in most models
SAMPLE_RATE = 22050         # Depends on your setup

word_boundary = ' '
pause = ','

# combine input tokens with aligned tokens
def combine(tokens, aligned):
    if len(tokens) == len(aligned):
        res = []
        for idx, w in enumerate(tokens):
            res.append(w | aligned[idx])
        return res
    else:
        logger.error("Different number of tokens vs aligned tokens -- output json file will not include aligmnent")
        logger.error(f"Tokens {tokens}")
        logger.error(f"Aligned tokens {aligned}")
        return tokens


def align(input_processed, output, id2symbol):
    #"attn": torch.Tensor, shape: (batch_size, max_text_length, max_mel_length),
    #Alignment map between text and mel spectrogram

    #alignment_phonemes = input_processed['x'][0]

    attn = output["attn"][0][0]  # shape: (max_text_length, max_mel_length)
    #mel_len = output["mel_lengths"][0].item()
    x = input_processed['x']
    phoneme_ids = x[0]     # shape: (max_text_length,)

    acc_word = {
        'phonemes': "",
        'start_time': None,
        'end_time': None,
    }
    res = []
    for phoneme_idx in range(attn.shape[0]):
        mel_indices = torch.where(attn[phoneme_idx] > 0)[0]  # frames aligned to this phoneme

        if len(mel_indices) > 0:
            start_frame = mel_indices[0].item()
            end_frame = mel_indices[-1].item()

            start_time = start_frame * HOP_LENGTH / SAMPLE_RATE
            end_time = (end_frame + 1) * HOP_LENGTH / SAMPLE_RATE  # +1 for inclusive range

            pid = phoneme_ids[phoneme_idx].item()
            phoneme = id2symbol.get(pid, '?')

            #logger.debug(f"alignment debug {pid} {phoneme} {start_time} {end_time}")

            if acc_word['start_time'] is None:
                acc_word['start_time'] = start_time

            if phoneme == pause and len(acc_word['phonemes']) > 0:
                res.append(acc_word)
                acc_word = {
                    'phonemes': phoneme,
                    'start_time': start_time,
                    'end_time': end_time,
                }
            elif phoneme == word_boundary:
                acc_word['end_time'] = end_time
                res.append(acc_word)
                acc_word = {
                    'phonemes': "",
                    'start_time': None,
                    'end_time': None,
                }
            else:
                if phoneme != '_':
                    acc_word['phonemes'] += phoneme
                acc_word['end_time'] = end_time

    if len(acc_word) > 0:
        res.append(acc_word)
    return res
