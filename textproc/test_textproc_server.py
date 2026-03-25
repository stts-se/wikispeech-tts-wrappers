# uv pip install httpx
# uv pip install pytest

# Run using the pytest command:
# pytest test_textproc_server.py


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
