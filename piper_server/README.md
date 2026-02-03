# Server for Piper TTS

Piper-TTS repo: [https://github.com/OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)    
Supported version 1.4.0

Useful docs for building voices:    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/BUILDING.md    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md    
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md    

**1. Installation**

___1.1 Install [uv](https://docs.astral.sh/uv/getting-started/installation) (optional)___

___1.2 Install piper-tts___

``` sh
uv venv
source .venv/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements.txt
```

___1.3 Workaround for PyTorch (Deep Phonemizer)___

``` sh
sed -i 's/checkpoint = torch.load(checkpoint_path, map_location=device)/checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.*/site-packages/dp/model/model.py
```


**2. Models**

___2.1 Download Piper models___

Replace `$HOME/.local/share/piper_tts` if you want to save your models elsewhere.

``` sh
mkdir -p $HOME/.local/share/piper_tts
cd $HOME/.local/share/piper_tts
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/bryce/medium/en_US-bryce-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/bryce/medium/en_US-bryce-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/norman/medium/en_US-norman-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/norman/medium/en_US-norman-medium.onnx.json
cd -
```

<!--
___2.2 Additional models___

For now, these models are only available for users approved by STTS. Some of these will be made publicly available once we sort out some licensing issues.

Download additional Piper + Deep Phonemizer models from :
-->

___2.2 Alignment patching___

```
python3 -m piper.patch_voice_with_alignment /path/to/model.onnx
```

Docs: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/ALIGNMENTS.md    



**3. Check config**

Verify paths and other config settings in `config_sample.json`


**4. Cmdline client**

`python piper_cli.py <onnx model> <input> <output file>`


**5. Server**

___5.1 Start server___


```
uvicorn piper_server:app --env-file config_sample.env --port 8010
```

___5.2 Access server___

Use your browser to go to http://127.0.0.1:8010/docs


___5.3 Audio and other output___

Output files will be in the `PIPER_OUTPUT_DIR` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* json – same as server response

There are currently three ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8010/static/AUDIOILE.wav` or `http://127.0.0.1:8010/static/latest.wav`
3. With a get request: `http://127.0.0.1:8010/synthesize/?voice=voice_name&input=input%20text%20to%20synthesize&input_type=mixed&return_type=wav`    
Example: [http://127.0.0.1:8010/synthesize/?voice=en_US-bryce-medium&input=hello%20my%20name%20is%20bryce%20with%20a%20get%20request&input_type=mixed&return_type=wav](http://127.0.0.1:8010/synthesize/?voice=en_US-bryce-medium&input=hello%20my%20name%20is%20bryce%20with%20a%20get%20request&input_type=mixed&return_type=wav)


Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).

