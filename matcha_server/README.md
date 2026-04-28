# Server for Matcha-TTS

Wrapper for runtime use of the [Matcha-TTS](https://github.com/shivammehta25/Matcha-TTS) text-to-speech engine.
Supported version: [STTS fork of Matcha-TTS](https://github.com/stts-se/Matcha-TTS).
<!--Supported version: master (commit [0.0.7.2](https://pypi.org/project/matcha-tts/0.0.7.2)-->

[![Matcha server](https://github.com/stts-se/wikispeech-tts-wrappers/actions/workflows/matcha-server.yml/badge.svg)](https://github.com/stts-se/wikispeech-tts-wrappers/actions/workflows/matcha-server.yml)

**1. Installation**

___1.1 Install [uv](https://docs.astral.sh/uv/getting-started/installation) (optional)___

___1.2 Set up `venv` and install Matcha-TTS___


``` sh
uv venv --python 3.13
source .venv/bin/activate
uv pip install -r requirements.txt
git clone https://github.com/stts-se/Matcha-TTS ../../Matcha-TTS_fork
uv pip install -e ../../Matcha-TTS_fork
bash patch.sh
```


**2. Models**

Follow instructions for Matcha and Deep Phonemizer on this page: https://stts-se.github.io/wikispeech/wikispeech1.html under <em>1.2&nbsp;Language&nbsp;models</em>

**3. Check config**

Verify paths and other config settings in `config_sample.json`. Please not that voices in the config file that are not enabled refer to models currently not publicly available.


**4. Cmdline client**

`python matcha_cli.py -h`

Check example commands in the top part of matcha_cli.py


**5. Server**

___5.1 Start server___

``` sh
uvicorn matcha_server:app --env-file config_sample.env --port 8009
```


___5.2 Access server___

Use your browser to go to http://127.0.0.1:8009/docs


___5.3 Audio and other output___

Output files will be in the `output_path` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* png – spectrogram
* lab – word alignment (could be used as input in Audacity or other software)
* json – same as server response

There are currently two ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8009/static/AUDIOILE.wav` or `http://127.0.0.1:8009/static/latest.wav`

Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).

Usage example for output_type=wav: 
http://localhost:8009/synthesize/?voice=sv_se_nst_STTS-test&input_type=mixed&input=s%C3%A5%20h%C3%A4r%20skickar%20man%20in%20[[bl%C2%B0and`ad]]%20input%20och%20f%C3%A5r%20en%20ljudfil%20direkt&speaking_rate=1&return_type=wav

