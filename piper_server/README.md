# Server for Piper TTS

STTS' Piper fork: [https://github.com/stts-se/piper1-gpl](https://github.com/stts-se/piper1-gpl)    
Main Piper repo: [https://github.com/OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)

Supported Piper version 1.3.1


**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation) (optional)**

**2. Set up `venv` and install piper-tts**


NB! For aligned output, you need to run this on a piper dev build for 1.3.1 or higher, since the released 1.3.0 version doesn't have alignment enabled.

Docs:    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/BUILDING.md    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md    

```
cd ../.. # or to another location, just not in the wikispeech-tts-wrapers repo
git clone https://github.com/OHF-Voice/piper1-gpl.git
cd piper1-gpl
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
uv pip install uvicorn "fastapi[standard]" phonemizer
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r <deep_phonemizer>/requirements.txt	
python3 setup.py build_ext --inplace
```


**3. Workaround for PyTorch**

```
sed -i 's/checkpoint = torch.load(checkpoint_path, map_location=device)/checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.*/site-packages/dp/model/model.py
```


**4. Models**

___4.1 Download Piper models___

Replace `$HOME/.local/share/piper_tts` if you want to save your models elsewhere.

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

<!--
___4.2 Additional models___

For now, these models are only available for users approved by STTS. Some of these will be made publicly available once we sort out some licensing issues.

Download additional Piper + Deep Phonemizer models from :
-->

___4.2 Alignment patching___

```
python3 -m piper.patch_voice_with_alignment /path/to/model.onnx
```

Docs: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md    



**5. Check config**

Verify paths and other config settings in `config_sample.json`


**6. Cmdline client**

`python <path-to-piper-server>/piper_cli.py <onnx model> <input> <output file>`


**7. Server**

___7.1 Start server___


<!--
```
uvicorn piper_server:app --env-file config_sample.env --port 8010
```
-->

```
uvicorn --app-dir <path-to-piper-server> piper_server:app --env-file <path-to-piper-server>/config_sample.env --port=8010
```


___7.2 Access server___

Use your browser to go to http://127.0.0.1:8010/docs


___7.3 Audio and other output___

Output files will be in the `PIPER_OUTPUT_DIR` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* json – same as server response

There are currently three ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8010/static/AUDIOILE.wav` or `http://127.0.0.1:8010/static/latest.wav`
3. With a get request: `http://127.0.0.1:8010/synthesize/?voice=voice_name&input=input%20text%20to%20synthesize&input_type=mixed&return_type=wav`    
Example: [http://127.0.0.1:8010/synthesize/?voice=en_US-bryce-medium&input=hello%20my%20name%20is%20bryce%20with%20a%20get%20request&input_type=mixed&return_type=wav](http://127.0.0.1:8010/synthesize/?voice=en_US-bryce-medium&input=hello%20my%20name%20is%20bryce%20with%20a%20get%20request&input_type=mixed&return_type=wav)


Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).

