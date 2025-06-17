# Server for Piper TTS

Piper URL: https://github.com/rhasspy/piper

Supported version 1.2.0


## Installation

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation)**

**2. Set up `venv` and install piper-tts**


```
uv venv
source .venv/bin/activate
uv pip install piper-tts
uv pip install "fastapi[standard]"
uv pip install uvicorn
```

**3. Download models**

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
cd -
```

**4. Check config**

Verify paths and other config settings in `config_sample.env`


**5. Start server**

```
uvicorn piper_server:app --env-file config_sample.env
```


**6. Access server**

Use your browser to go to http://127.0.0.1:8000/docs



**7. Audio and other output**

Output files will be in the `output_path` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* json – same as server response

There are currently two ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8000/static/AUDIOILE.wav` or `http://127.0.0.1:8000/static/latest.wav`

Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).
