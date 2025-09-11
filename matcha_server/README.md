# Server for Matcha-TTS

Wrapper for runtime use of the [Matcha-TTS](https://github.com/shivammehta25/Matcha-TTS) text-to-speech engine.

## Installation

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation)**

**2. Set up `venv` and install Matcha-TTS**

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install Matcha-TTS==0.0.7.2
```

Supported Matcha version: [0.0.7.2](https://pypi.org/project/matcha-tts/0.0.7.2)

**3. Download models**

Replace `$HOME/.local/share/matcha_tts` if you want to save your models elsewhere. In that case, you also have to update `model_paths` in your config file (see below).

__Matcha models__

```
mkdir -p $HOME/.local/share/matcha_tts
cd $HOME/.local/share/matcha_tts
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/generator_v1 -o hifigan_T2_v1
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/g_02500000 -o hifigan_univ_v1
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/matcha_ljspeech.ckpt -o matcha_ljspeech.ckpt
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/matcha_vctk.ckpt -o matcha_vctk.ckpt
cd -
```

__Additional Matcha models__

Download additional models for Matcha from [STTS Google Drive](https://drive.google.com/drive/folders/1g8tw6tKBd32gcgHbPSTPg5b8dFhQ8SOP?usp=sharing) and save to `$HOME/.local/share/matcha_tts`.

__Phonetization models__

Download phonetization models for Deep Phonemizer from [STTS Google Drive](https://drive.google.com/drive/folders/1XAgg_fu7Ay4eEad0n5WW7m-IX1XKIXNz?usp=sharing) and save to `$HOME/.local/share/deep_phonemizer`

**4. Check config**

Verify paths and other config settings in `config_sample.json`

_Notes on specific voices_

In order to use the Swedish test voices `hb_last.ckpt` and `svensk_multi.ckpt` (disabled by default), you need to save those checkpoint files in your `model_paths` list (as defined in the config file).

**5. Start server**

```
uvicorn matcha_server:app --env-file config_sample.env
```


**6. Access server**

Use your browser to go to http://127.0.0.1:8000/docs


**7. Audio and other output**

Output files will be in the `output_path` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* png – spectrogram
* lab – word alignment (could be used as input in Audacity or other software)
* json – same as server response

There are currently two ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8000/static/AUDIOILE.wav` or `http://127.0.0.1:8000/static/latest.wav`

Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).


<!--
--------

# Vendoring dependencies (experimental)

**2a. Set up `venv` and install Matcha-TTS**

```
uv venv
source .venv/bin/activate
uv pip install Matcha-TTS --prefix vendor
uv pip install uvicorn dotenv
```

**2b. Add imports to matcha_server.py**

```
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor/lib/python3.10/site-packages')
sys.path.append(vendor_dir)
```
-->
