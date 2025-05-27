import torch

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

# Constants
hop_length = 256            # Typically 256 in most models
sample_rate = 22050         # Depends on your setup

word_boundary = ' '
pause = ','

def align(input_processed, output, id2symbol):
    #"attn": torch.Tensor, shape: (batch_size, max_text_length, max_mel_length),
    #Alignment map between text and mel spectrogram
    
    alignment_phonemes = input_processed['x'][0]
 
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
            
            start_time = start_frame * hop_length / sample_rate
            end_time = (end_frame + 1) * hop_length / sample_rate  # +1 for inclusive range

            id = phoneme_ids[phoneme_idx].item()
            phoneme = id2symbol.get(id, '?')

            #logger.debug(f"alignment debug {id} {phoneme} {start_time} {end_time}")
                
            if acc_word['start_time'] is None:
                acc_word['start_time'] = start_time

            if phoneme == pause:
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
