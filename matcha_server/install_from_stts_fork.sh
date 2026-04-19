set -e

deactivate || echo -n ""
rm -rf .venv || echo -n ""
uv venv --python 3.10
source .venv/bin/activate
if [ -e ../../Matcha-TTS_fork ]; then
    cd ../../Matcha-TTS_fork
    git pull
    cd -
else
    git clone https://github.com/stts-se/Matcha-TTS ../../Matcha-TTS_fork
fi    
uv pip install -r requirements.txt
uv pip install -e ../../Matcha-TTS_fork
bash patch.sh
uvicorn matcha_server:app --env-file config_mvp2.env --port 8009
