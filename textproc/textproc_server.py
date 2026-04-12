# For usage info, se README.md

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel # data models for post requests
from dotenv import load_dotenv
import json, re

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from common import release, log

import textproc

json_config = os.getenv("TEXTPROC_CONFIG")  # Reads from .env file passed to uvicorn
if not json_config:
    raise RuntimeError("Config not provided. Start server with --env-file")

load_dotenv()

textprocs = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global textprocs, vInfo
    startedAt = release.genStartedAtString()
    vInfo = release.versionInfo("textproc",startedAt)
    textprocs = textproc.load_config(json_config)
    errs_total = []
    fail = False
    for tpname in textprocs:
        tp = textprocs[tpname]
        errs = tp.self_tests()
        if len(errs) > 0 and tp.fail_on_error:
            fail = True
        #print(errs)
    if fail:
        raise Exception("Server exit after textproc selftest errors")
        #sys.exit(1)
    yield


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"tryItOutEnabled": True})

class UttRequest(BaseModel):
    name: str = "sv_se_1"
    input_type: str = "tokens"
    input: list = [
        {'text': 'jag heter', 'type': 'text'},
        {'text': 'Karl XII', 'type': 'alias', 'alias': 'Karl den tolfte'},
        {'text': 'och jag är en', 'type': 'text'},
        {'text': 'apa', 'type': 'phonemes', 'phonemes': '"" A: . p a'}
    ]

    #input: str = "jag föddes på S/S Norrskär och S/S Storskär, 1984 bl.a. och det var kul sa Karl XII och Gustav XVI både 1:a och 2:a gången också!"

@app.post("/process_utt")
async def process_utt_as_post(request: UttRequest):
    if textprocs is None:
        raise Exception("textprocs not initialized")
    if not request.name in textprocs:
        msg = f"No such textproc: {request.name}"
        log.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[request.name]
    res = comp.process_utt(request.input,request.input_type)
    return res


@app.get("/process_utt")
async def process_utt(name: str = "sv_se_1", input: str = "Karl XII, t.ex., kom på 2:a plats den 3 maj 1984 och vann 5986 kr", input_type: str = "text"):
    if textprocs is None:
        raise Exception("textprocs not initialized")
    if not name in textprocs:
        msg = f"No such textproc: {name}"
        log.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[name]
    res = comp.process_utt(input,input_type)
    return res


@app.get("/process_text")
async def process_text(
    name: str = "sv_se_1", input: str = "den 3 februari såg jag en häst"
):
    if textprocs is None:
        raise Exception("textprocs not initialized")
    if not name in textprocs:
        msg = f"No such textproc: {name}"
        log.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[name]
    res = comp.process_text(input)
    return res


@app.get("/list")
async def list():
    if textprocs is None:
        raise Exception("textprocs not initialized")
    res = []
    for tp in textprocs.values():
        res.append(tp)
    return res

@app.get("/ping")
async def ping():
    return HTMLResponse(content="textproc", media_type="text")


@app.get('/version')
def version():
    resp = HTMLResponse("\n".join(vInfo), media_type="text")
    resp.headers["Content-type"] = "text/plain"
    return resp
