# Server for deep phonemizer models

Deep Phonemizer URL: https://github.com/spring-media/DeepPhonemizer

Supported version 0.0.19

## Installation

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation)**

**2. Set up `venv` and install requirements**

```
uv venv 
source .venv/bin/activate
uv pip install -r requirements.txt
```

**3. Workaround for PyTorch**

```
sed -i 's/checkpoint = torch.load(checkpoint_path, map_location=device)/checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.10/site-packages/dp/model/model.py
```


**4. Fetch models**

```
mkdir -p $HOME/.local/share/deep_phonemizer
cd $HOME/.local/share/deep_phonemizer
wget https://public-asai-dl-models.s3.eu-central-1.amazonaws.com/DeepPhonemizer/en_us_cmudict_ipa_forward.pt
wget https://morf.se/~hanna/deep_phonemizer/models/forward_singlechar/sv_se_best_model_20250331_forward_singlechar.pt
cd -
```

**5. Check config**

Verify paths and other config settings in `config_sample.env`

**6. Start server** 

`uvicorn dp_server:app --env-file config_sample.env [--reload]`



**7. Try it out** 

http://localhost:8000/docs


**8. API access** 

http://localhost:8000/phonemize/MODELNAME/TEXT

Example (requires `httpie`):
```
http "http://localhost:8000/phonemize/sv_se_nst/god morgon" --response-charset=utf8
```
