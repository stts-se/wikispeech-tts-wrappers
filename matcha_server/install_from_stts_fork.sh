set -e

deactivate || echo -n ""
rm -rf .venv || echo -n ""
uv venv --python 3.10
source .venv/bin/activate
git clone https://github.com/stts-se/Matcha-TTS ../../Matcha-TTS || echo "It's OK, Matcha-TTS is already checked out"
uv pip install -r requirements.txt
uv pip install -e ../../Matcha-TTS
bash patch.sh
#uvicorn matcha_server:app --env-file config_mvp2.env --port 8009
