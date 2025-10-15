# Server for Matcha-TTS

Wrapper for runtime use of the [Matcha-TTS](https://github.com/shivammehta25/Matcha-TTS) text-to-speech engine.

## Installation

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation)**

**2. Set up `venv` and install Matcha-TTS**

```
uv venv
source .venv/bin/activate
uv pip install -r ../deep_phonemizer_server/requirements.txt	
uv pip install Matcha-TTS==0.0.7.2
```

Supported Matcha version: [0.0.7.2](https://pypi.org/project/matcha-tts/0.0.7.2)

**3. Workarounds for PyTorch and MatchaTTS**

```
sed -i 's/checkpoint = torch.load(checkpoint_path, map_location=device)/checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.10/site-packages/dp/model/model.py

sed -i 's|\(plot_spectrogram_to_numpy.*\) f"{filename}.png")|\1 folder / f"{filename}.png")|' .venv/lib/python3.10/site-packages/matcha/cli.py

```

**4. Download models**

Replace `$HOME/.local/share/matcha_tts` if you want to save your models elsewhere. In that case, you also have to update `model_paths` in your config file (see below).

___4.1 Matcha models___

```
mkdir -p $HOME/.local/share/matcha_tts
cd $HOME/.local/share/matcha_tts
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/generator_v1 -o hifigan_T2_v1
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/g_02500000 -o hifigan_univ_v1
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/matcha_ljspeech.ckpt -o matcha_ljspeech.ckpt
curl -L https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/matcha_vctk.ckpt -o matcha_vctk.ckpt
cd -
```

___4.2 Additional models___

For now, these models are only available for users approved by STTS. Some of these will be made publicly available once we sort out some licensing issues.

Download additional Matcha models from [STTS Google Drive](https://drive.google.com/drive/folders/1g8tw6tKBd32gcgHbPSTPg5b8dFhQ8SOP?usp=sharing) and save to `$HOME/.local/share/matcha_tts`

Download Deep Phonemizer models from [STTS Google Drive](https://drive.google.com/drive/folders/1XAgg_fu7Ay4eEad0n5WW7m-IX1XKIXNz?usp=sharing) and save to `$HOME/.local/share/deep_phonemizer`

**5. Check config**

Verify paths and other config settings in `config_sample.json`. Please not that voices in the config file that are not enabled refer to models currently not publicly available (see also Additional models above).


**6. Cmdline client**

`python matcha_cli.py -h`

Check example commands in the top part of matcha_cli.py


**7. Server**

___7.1 Start server___

```
uvicorn matcha_server:app --env-file config_sample.env
```


___7.2 Access server___

Use your browser to go to http://127.0.0.1:8000/docs


___7.3 Audio and other output___

Output files will be in the `output_path` folder defined in the config file, default: `./audio_files`:

* wav – audio output
* png – spectrogram
* lab – word alignment (could be used as input in Audacity or other software)
* json – same as server response

There are currently two ways to listen to the generated audio:

1. Play the file `latest.wav` in your `output_path`
2. Use your browser to copy the `audio` path from the server response, and paste it in the browser's address field as `http://127.0.0.1:8000/static/AUDIOILE.wav` or `http://127.0.0.1:8000/static/latest.wav`

Please note that the server's default setting is to clear the `output_path` on startup. This can be configured in the config file (see `config_sample.json`).

Usage example for output_type=wav
http://localhost:8000/synthesize/?voice=sv_se_nst_STTS-test&input_type=mixed&input=s%C3%A5%20h%C3%A4r%20skickar%20man%20in%20[[bl%C2%B0and`ad]]%20input%20och%20f%C3%A5r%20en%20ljudfil%20direkt&speaking_rate=1&return_type=wav


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
