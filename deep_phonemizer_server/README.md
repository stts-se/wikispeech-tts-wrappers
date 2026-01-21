# Server for deep phonemizer models

Deep Phonemizer URL: https://github.com/spring-media/DeepPhonemizer

Supported version 0.0.19

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation) (optional)**

**2. Set up `venv` and install requirements**


___2.1 For running the server___
```
uv venv 
source .venv/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements.txt
```

___2.1 For training deep phonemizer models___
```
uv venv 
source .venv/bin/activate
uv pip install -r requirements.txt
```


**3. Workaround for PyTorch**

```
sed -i 's/checkpoint = torch.load(checkpoint_path, map_location=device)/checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.*/site-packages/dp/model/model.py
```


**4. Fetch models and maptables**

```
mkdir -p $HOME/.local/share/deep_phonemizer
cd $HOME/.local/share/deep_phonemizer
wget https://public-asai-dl-models.s3.eu-central-1.amazonaws.com/DeepPhonemizer/en_us_cmudict_ipa_forward.pt
cd -
```

<!-- Download additional models from [STTS Google Drive](https://drive.google.com/drive/folders/1XAgg_fu7Ay4eEad0n5WW7m-IX1XKIXNz?usp=sharing) -->

**5. Check config**

Verify paths and other config settings in `config_sample.env` / `config_sample.json`

**6. Start server** 

`uvicorn dp_server:app --env-file config_sample.env --port 8008 [--reload]`



**7. Try it out** 

http://localhost:8008/docs


**8. API access** 

http://localhost:8008/phonemize/MODELNAME/TEXT

Example (requires `httpie`):
```
http "http://localhost:8008/phonemize/sv_se_nst/god morgon" --response-charset=utf8
```
