# Local imports
import alignment

# Matcha-related imports
from pathlib import Path
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
import torch

from matcha.hifigan.config import v1
from matcha.hifigan.denoiser import Denoiser
from matcha.hifigan.env import AttrDict
from matcha.hifigan.models import Generator as HiFiGAN
from matcha.models.matcha_tts import MatchaTTS
from matcha.utils.utils import intersperse

# Logging
import logging
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

# Other imports
import os, sys



####### New functions ##############################################################

def create_tensor(speakers,device,dtype=torch.long):
    return torch.tensor(speakers,device=device,dtype=dtype)

# if the same model/file is found in multiple paths, the first one will be used
def find_model(name, paths):
    for p in paths:
        f = os.path.join(p, name)
        if os.path.isfile(f):
            return f
    return None


def create_path(p,create=False):
    p = os.path.expandvars(p)
    if create:
        folder = Path(p)
        folder.mkdir(exist_ok=True, parents=True)
        #logger.debug(f"Created directory: {p}")
    if not os.path.isdir(p):
        raise IOError(f"Couldn't create output folder: {p}")
    return p


def clear_audio(audio_path):
    logger.info(f"Clearing audio set to true")
    n=0
    for fn in os.listdir(audio_path):
        file_path = os.path.join(audio_path, fn)
        if os.path.isfile(file_path):
            os.remove(file_path)
            n+=1
            #print(fn, "is removed")
    logger.info(f"Deleted {n} files from folder {audio_path}")
    

def save_output(matcha_output: dict, parsed_output, folder: str, basename: str):
    folder = Path(folder)
    folder.mkdir(exist_ok=True, parents=True)
    parsed_output['audio'] = str(folder.resolve() / f"{basename}.wav")

    # save spectrogram
    png_file = folder / f"{basename}.png"
    plot_spectrogram_to_numpy(np.array(matcha_output["mel"].squeeze().float().cpu()), png_file)
    np.save(folder / f"{basename}", matcha_output["mel"].cpu().numpy())

    # save wav file
    wav_file = folder / f"{basename}.wav"
    sf.write(wav_file, matcha_output["waveform"], 22050, "PCM_24")

    # save label file
    lab_file = os.path.join(folder, f"{basename}.lab")
    with open(lab_file, "w") as f:
        for token in parsed_output['alignment']:
            f.write(f"{token['start_time']}\t{token['end_time']}\t{token['phonemes']}\n")

    # save json
    import json
    json_file = os.path.join(folder, f"{basename}.json")
    with open(json_file, 'w') as f:
        json.dump(parsed_output, f, ensure_ascii=False, indent=4)

    # copy to latest
    parsed_output_latest = parsed_output
    parsed_output_latest['audio'] = str(folder.resolve() / "latest.wav")
    json_file_latest = os.path.join(folder, "latest.json")
    with open(json_file_latest, 'w') as f:
        json.dump(parsed_output_latest, f, ensure_ascii=False, indent=4)

    output_files = {
        png_file: folder / "latest.png",
        wav_file: folder / "latest.wav",
        lab_file: folder / "latest.lab"
    }
    import shutil
    for source,dest in output_files.items():
        print(source, dest)
        shutil.copy(source,dest)
        
    return parsed_output



####### Adapted from Matcha's cli.py ###################################################


def batched_synthesis_NONFUNCT(args, device, model, vocoder, denoiser, params, spk, symbolset, process_input):
    logger.info(f"Calling batched_synthesis with input {params.input_type} {params.input}")
    total_rtf = []
    total_rtf_w = []
    processed_input = [process_input(i, input, params.input_type, "cpu") for i, input in enumerate(params.input)]
    dataloader = torch.utils.data.DataLoader(
        BatchedSynthesisDataset(processed_input),
        batch_size=args.batch_size,
        collate_fn=batched_collate_fn,
        num_workers=8,
    )
    res = []
    for i, batch in enumerate(dataloader):
        batch["phonemes"] = processed_input[i] # phonemes do not seem to be retained in the dataset, so let's try to re-insert it here
        i = i + 1
        start_t = dt.datetime.now()
        b = batch["x"].shape[0]
        output = model.synthesise(
            batch["x"].to(device),
            batch["x_lengths"].to(device),
            n_timesteps=args.steps,
            temperature=args.temperature,
            spks=spk.expand(b) if spk is not None else spk,
            length_scale=params.speaking_rate,
        )

        output["waveform"] = to_waveform(output["mel"], vocoder, denoiser, args.denoiser_strength)
        t = (dt.datetime.now() - start_t).total_seconds()
        rtf_w = t * 22050 / (output["waveform"].shape[-1])
        logger.info(f"[🍵-Batch: {i}] Matcha-TTS RTF: {output['rtf']:.4f}")
        logger.info(f"[🍵-Batch: {i}] Matcha-TTS + VOCODER RTF: {rtf_w:.4f}")
        total_rtf.append(output["rtf"])
        total_rtf_w.append(rtf_w)
        import uuid
        uid = uuid.uuid4()
        for j in range(output["mel"].shape[0]):
            base_name = f"utt_{uid}_{j:03d}_spk_{args.spk:03d}" if args.spk is not None else f"utt_{uid}_{j:03d}"
            length = output["mel_lengths"][j]
            if len(output["waveform"]) > 1:
                new_dict = {"mel": output["mel"][j][:, :length], "waveform": output["waveform"][j][: length * 256]}
                aligned = alignment.align(batch, output, symbolset.id2symbol)
                entry = {
                    'input': input,
                    'input_type': params.input_type,                     
                    'phonemes': "".join(batch['phonemes']),
                    'alignment': aligned
                }
                entry = save_output(output, entry, args.output_folder, base_name)
                res.append(entry)
                logger.info(f"[+] Waveform saved: {entry['audio']}")

    #logger.info("".join(["="] * 100))
    logger.info(f"[🍵] Average Matcha-TTS RTF: {np.mean(total_rtf):.4f} ± {np.std(total_rtf)}")
    logger.info(f"[🍵] Average Matcha-TTS + VOCODER RTF: {np.mean(total_rtf_w):.4f} ± {np.std(total_rtf_w)}")
    logger.info("[🍵] Enjoy the freshly whisked 🍵 Matcha-TTS!")
    return res


def unbatched_synthesis(args, device, model, vocoder, denoiser, params, spk, symbolset, process_input):
    logger.info(f"Calling unbatched_synthesis with input {params.input_type} {params.input}")
    total_rtf = []
    total_rtf_w = []
    res = []
    import uuid
    uid = uuid.uuid4()
    for i, input in enumerate(params.input):
        i = i + 1
        base_name = f"utt_{uid}_{i:03d}_spk_{args.spk:03d}" if args.spk is not None else f"utt_{uid}_{i:03d}"

        input = input.strip()
        processed_input = process_input(i, input, params.input_type, device)

        logger.info(f"[🍵] Whisking Matcha-T(ea)TS for: {i}")
        start_t = dt.datetime.now()
        output = model.synthesise(
            processed_input["x"],
            processed_input["x_lengths"],
            n_timesteps=args.steps,
            temperature=args.temperature,
            spks=spk,
            length_scale=params.speaking_rate,
        )
        output["waveform"] = to_waveform(output["mel"], vocoder, denoiser, args.denoiser_strength)

        # RTF with HiFiGAN
        t = (dt.datetime.now() - start_t).total_seconds()
        rtf_w = t * 22050 / (output["waveform"].shape[-1])
        logger.info(f"[🍵-{i}] Matcha-TTS RTF: {output['rtf']:.4f}")
        logger.info(f"[🍵-{i}] Matcha-TTS + VOCODER RTF: {rtf_w:.4f}")
        total_rtf.append(output["rtf"])
        total_rtf_w.append(rtf_w)

        aligned = alignment.align(processed_input, output, symbolset.id2symbol)
        entry = {
            'input': input,
            'input_type': params.input_type,                     
            'phonemes': "".join(processed_input['phonemes']),
            'alignment': aligned
        }
        entry = save_output(output, entry, args.output_folder, base_name)
        res.append(entry)
        logger.info(f"[+] Waveform saved: {entry['audio']}")

    #logger.info("".join(["="] * 100))
    logger.info(f"[🍵] Average Matcha-TTS RTF: {np.mean(total_rtf):.4f} ± {np.std(total_rtf)}")
    logger.info(f"[🍵] Average Matcha-TTS + VOCODER RTF: {np.mean(total_rtf_w):.4f} ± {np.std(total_rtf_w)}")
    logger.info("[🍵] Enjoy the freshly whisked 🍵 Matcha-TTS!")
    return res



####### Functions basically copied verbatim from Matcha's cli.py ##########################

class BatchedSynthesisDataset(torch.utils.data.Dataset):
    def __init__(self, processed_input):
        self.processed_input = processed_input

    def __len__(self):
        return len(self.processed_input)

    def __getitem__(self, idx):
        return self.processed_input[idx]


def get_device(args):
    if torch.cuda.is_available() and not args.cpu:
        print("[+] GPU Available! Using GPU")
        device = torch.device("cuda")
    else:
        print("[-] GPU not available or forced CPU run! Using CPU")
        device = torch.device("cpu")
    return device


def load_hifigan(checkpoint_path, device):
    h = AttrDict(v1)
    hifigan = HiFiGAN(h).to(device)
    hifigan.load_state_dict(torch.load(checkpoint_path, map_location=device)["generator"])
    _ = hifigan.eval()
    hifigan.remove_weight_norm()
    return hifigan


def load_vocoder(vocoder_name, checkpoint_path, device):
    print(f"[!] Loading {vocoder_name}!")
    vocoder = None
    if vocoder_name in ("hifigan_T2_v1", "hifigan_univ_v1"):
        vocoder = load_hifigan(checkpoint_path, device)
    else:
        raise NotImplementedError(
            f"Vocoder {vocoder_name} not implemented! define a load_<<vocoder_name>> method for it"
        )

    denoiser = Denoiser(vocoder, mode="zeros")
    print(f"[+] {vocoder_name} loaded!")
    return vocoder, denoiser


def load_matcha(model_name, checkpoint_path, device):
    print(f"[!] Loading {model_name}!")
    model = MatchaTTS.load_from_checkpoint(checkpoint_path, map_location=device)
    _ = model.eval()

    print(f"[+] {model_name} loaded!")
    return model


def plot_spectrogram_to_numpy(spectrogram, filename):
    fig, ax = plt.subplots(figsize=(12, 3))
    im = ax.imshow(spectrogram, aspect="auto", origin="lower", interpolation="none")
    plt.colorbar(im, ax=ax)
    plt.xlabel("Frames")
    plt.ylabel("Channels")
    plt.title("Synthesised Mel-Spectrogram")
    fig.canvas.draw()
    plt.savefig(filename)


def to_waveform(mel, vocoder, denoiser=None, denoiser_strength=0.00025):
    audio = vocoder(mel).clamp(-1, 1)
    if denoiser is not None:
        audio = denoiser(audio.squeeze(), strength=denoiser_strength).cpu().squeeze()

    return audio.cpu().squeeze()


def batched_collate_fn(batch):
    x = []
    x_lengths = []

    for b in batch:
        x.append(b["x"].squeeze(0))
        x_lengths.append(b["x_lengths"])

    x = torch.nn.utils.rnn.pad_sequence(x, batch_first=True)
    x_lengths = torch.concat(x_lengths, dim=0)
    return {"x": x, "x_lengths": x_lengths}


def validate_args(args):
    assert (
        args.text or args.file
    ), "Either text or file must be provided Matcha-T(ea)TTS need sometext to whisk the waveforms."
    assert args.temperature >= 0, "Sampling temperature cannot be negative"
    assert args.steps > 0, "Number of ODE steps must be greater than 0"

    if args.checkpoint_path is None:
        # When using pretrained models
        if args.model in SINGLESPEAKER_MODEL:
            args = validate_args_for_single_speaker_model(args)

        if args.model in MULTISPEAKER_MODEL:
            args = validate_args_for_multispeaker_model(args)
    else:
        # When using a custom model
        if args.vocoder != "hifigan_univ_v1":
            warn_ = "[-] Using custom model checkpoint! I would suggest passing --vocoder hifigan_univ_v1, unless the custom model is trained on LJ Speech."
            warnings.warn(warn_, UserWarning)
        if args.speaking_rate is None:
            args.speaking_rate = 1.0

    if args.batched:
        assert args.batch_size > 0, "Batch size must be greater than 0"
    assert args.speaking_rate > 0, "Speaking rate must be greater than 0"

    return args

