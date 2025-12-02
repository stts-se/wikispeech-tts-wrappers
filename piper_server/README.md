# Server for Piper TTS

___WORK IN PROGRESS___

STTS' Piper fork: [https://github.com/stts-se/piper1-gpl](https://github.com/stts-se/piper1-gpl)

Main Piper repo: [https://github.com/OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)

Supported Piper version 1.3.0


## Installation

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation)**

**2. Set up `venv` and install piper-tts**


```
uv venv
source .venv/bin/activate
uv pip install piper-tts==1.3.0
uv pip install "fastapi[standard]"
uv pip install uvicorn
```

**3. Download models**

Replace `$HOME/.local/share/piper_tts` if you want to save your models elsewhere.

<!-- In that case, you also have to update `paths` in your config file (see below). -->

___3.1 Piper models___

```
mkdir -p $HOME/.local/share/piper_tts
cd $HOME/.local/share/piper_tts
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/bryce/medium/en_US-bryce-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/bryce/medium/en_US-bryce-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/norman/medium/en_US-norman-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/norman/medium/en_US-norman-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/sv/sv_SE/lisa/medium/sv_SE-lisa-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/sv/sv_SE/lisa/medium/sv_SE-lisa-medium.onnx.json
cd -
```
___3.2 Additional models___

For now, these models are only available for users approved by STTS. Some of these will be made publicly available once we sort out some licensing issues.

Download additional Piper models from [STTS Google Drive](https://drive.google.com/drive/folders/1quDWeW1Vemky1YFdLv17m8Chtpg7ZPSO?usp=sharing) and save to `$HOME/.local/share/piper_tts`

<!-- Download Deep Phonemizer models from [STTS Google Drive](https://drive.google.com/drive/folders/1XAgg_fu7Ay4eEad0n5WW7m-IX1XKIXNz?usp=sharing) and save to `$HOME/.local/share/deep_phonemizer` -->



**4. Cmdline client**

`bash piper_cli.sh <model name> <input text or phonemes> <output file*>`

_\* if no output file is set, audio will be played immediately using ffplay (dependency)_



**4. Check config**

Verify paths and other config settings in `config_sample.env`


**5. Server**

___5.1 Start server___

```
uvicorn piper_server:app --env-file config_sample.env --port 8010
```

NB! For aligned output, you need to run this on a piper dev build for 1.3.1 or higher, since the released 1.3.0 version isn't alignment enabled

Docs:    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/BUILDING.md    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md    

```
git clone https://github.com/stts-se/piper1-gpl.git
cd piper1-gpl
uv venv
source .venv/bin/activate
uv pip install "fastapi[standard]"
uv pip install uvicorn
uvicorn --app-dir <path-to-piper-server> piper_server:app --env-file <path-to-piper-server>/config_sample.env -port=8010
```


___5.2 Access server___

Use your browser to go to http://127.0.0.1:8010/docs


___5.3 Audio and other output___

Output files will be in the `PIPER_OUTPUT_DIR` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* json – same as server response

There are currently two ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8010/static/AUDIOILE.wav` or `http://127.0.0.1:8010/static/latest.wav`

Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).

