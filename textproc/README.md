# Server for tokenization and text processing

[![Textproc](https://github.com/stts-se/wikispeech-tts-wrappers/actions/workflows/textproc.yml/badge.svg)](https://github.com/stts-se/wikispeech-tts-wrappers/actions/workflows/textproc.yml)

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation) (optional)**


**2. Set up `venv` and install requirements**

```
uv venv 
source .venv/bin/activate
uv pip install -r requirements.txt
```


**3. Check config**

Verify paths and other config settings in `config_sample.env` / `config_sample.json`


**4. Start server** 

`uvicorn textproc_server:app --env-file config_sample.env --port 8011 [--reload]`



**5. Try it out** 

http://localhost:8011/docs


**6. API access** 

http://localhost:8011/proc/TEXTPROCNAME/TEXT

Example (requires `httpie`):
```
http "http://localhost:8011/phonemize/sv_se_1/god morgon" --response-charset=utf8
```
