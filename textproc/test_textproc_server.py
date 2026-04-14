# uv pip install httpx
# uv pip install pytest

# Run using the pytest command:
# pytest test_textproc_server.py

# Reading config env file defined in conftest.py

import pytest

def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 404

def test_read_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200
    
def test_single_word(client):
    response = client.get("/process_text?name=sv_se_1&input=hej")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    
    item = data[0]
    assert item["input"] == "hej"
    assert item["derived_input_text"] == "hej"
    assert item["derived_output_text"] == "hej"
    
    tokens = item["tokens"]
    assert len(tokens) == 1
    assert tokens[0]["type"] == "text"
    assert tokens[0]["text"] == "hej"
    
    words = tokens[0]["words"]
    assert len(words) == 1
    assert words[0]["input"] == "hej"
    assert words[0]["word"] == "hej"

def test_single_word_post(client):
    payload = {
        "name": "sv_se_1",
        "input_type": "tokens",
        "input": [
            {'text': 'jag heter', 'type': 'text'},
            {'text': 'Karl XII', 'type': 'alias', 'alias': 'Karl den tolfte'},
            {'text': 'och jag är en', 'type': 'text'},
            {'text': 'apa', 'type': 'phonemes', 'phonemes': '"" A: . p a'}
        ]
    }
    
    response = client.post("process_utt", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4

    tokens = data["tokens"]
    #assert tokens == expect
    assert len(tokens) == 8

    assert tokens[0]["text"] == "jag"

    assert tokens[2]["text"] == "Karl XII"
    assert tokens[2]["type"] == "alias"
    assert tokens[2]["alias"] == "Karl den tolfte"

    assert tokens[7]["text"] == "apa"
    assert tokens[7]["type"] == "phonemes"
    assert tokens[7]["words"][0]["phonemes"] == "\"\" A: . p a"


def test_orphan_punct(client):
    converted_ssml_input = [{'text': '"', 'type': 'text'}, {'text': 'All', 'type': 'phonemes', 'phonemes': '" o: l'}, {'text': 'Apologies" hamnade på plats sju över de ', 'type': 'text'}, {'text': '20', 'type': 'alias', 'alias': 'tjugo'}, {'text': 'mest spelade Nirvana-låtarna.', 'type': 'text'}]
    expect = [
        {'type': 'text', 'text': '"', 'words': [{
            'input': '"', 'word': '"'}]},
        {'text': 'All', 'type': 'phonemes', 'words':
         [{'word': 'All', 'phonemes': '" o: l'}]},
        {'type': 'text', 'text': 'Apologies"', 'words':
         [{'input': 'Apologies"', 'word': 'Apologies', 'postpunct': '"'}]},
        {'type': 'text', 'text': 'hamnade', 'words':
         [{'input': 'hamnade', 'word': 'hamnade'}]},
        {'type': 'text', 'text': 'på', 'words':
         [{'input': 'på', 'word': 'på'}]},
        {'type': 'text', 'text': 'plats', 'words':
         [{'input': 'plats', 'word': 'plats'}]},
        {'type': 'text', 'text': 'sju', 'words':
         [{'input': 'sju', 'word': 'sju'}]},
        {'type': 'text', 'text': 'över', 'words':
         [{'input': 'över', 'word': 'över'}]},
        {'type': 'text', 'text': 'de', 'words':
         [{'input': 'de', 'word': 'de'}]},
        {'text': '20', 'type': 'alias', 'alias': 'tjugo', 'words':
         [{'input': 'tjugo', 'word': 'tjugo'}]},
        {'type': 'text', 'text': 'mest', 'words':
         [{'input': 'mest', 'word': 'mest'}]},
        {'type': 'text', 'text': 'spelade', 'words':
         [{'input': 'spelade', 'word': 'spelade'}]},
        {'type': 'text', 'text': 'Nirvana-låtarna.', 'words':
         [{'input': 'Nirvana-låtarna.', 'word': 'Nirvana-låtarna', 'postpunct': '.'}]
         }
    ]
    payload = {
        "name": "sv_se_1",
        "input_type": "ssml",
        "input": converted_ssml_input,
    }
    response = client.post("process_utt", json=payload)
    assert response.status_code == 200
    data = response.json()
    tokens = data["tokens"]
    assert tokens == expect


# sv. "e.kr."
# cirka år 400 e.Kr. till 1500 e.Kr.
def test_sv_ekr(client):
    response = client.get("/process_text?name=sv_se_1&input=cirka år 400 e.Kr. till 1500 e.Kr.")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    toks = data[0]["tokens"]
    assert len(toks) == 9
    assert data[0]["derived_output_text"] == "cirka år fyra-hundra efter Kristus till femton-hundra efter Kristus."
