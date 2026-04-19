set -e

deactivate || echo -n ""
rm -rf .venv || echo -n ""
uv venv --python 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install Matcha-TTS==0.0.7.2
bash patch.sh
#uvicorn matcha_server:app --env-file config_mvp2.env --port 8009
