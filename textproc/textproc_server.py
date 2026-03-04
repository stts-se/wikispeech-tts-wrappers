# For usage info, se README.md

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel # data models for post requests
from dotenv import load_dotenv
import json, re

import textproc

json_config = os.getenv("TEXTPROC_CONFIG")  # Reads from .env file passed to uvicorn
if not json_config:
    raise RuntimeError("Config not provided. Start server with --env-file")

load_dotenv()

# Logging
import logging
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)

textprocs = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global textprocs
    textprocs = textproc.load_config(json_config)
    yield


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"tryItOutEnabled": True})

class UttRequest(BaseModel):
    name: str = "sv_se_1"
    input_type: str = "text"
    input: str = "jag föddes 1984 bl.a."

@app.post("/process_utt")
async def process_utt_as_post(request: UttRequest):
    if textprocs is None:
        raise Exception("textprocs not initialized")
    if not request.name in textprocs:
        msg = f"No such textproc: {request.name}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[request.name]
    res = comp.process_utt(request.input)
    return res


@app.get("/process_utt")
async def process_utt(name: str = "sv_se_1", input: str = "Karl XII, t.ex., kom på 2:a plats den 3 maj 1984 och vann 5986 kr"):
    if textprocs is None:
        raise Exception("textprocs not initialized")
    if not name in textprocs:
        msg = f"No such textproc: {name}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[name]
    res = comp.process_utt(input)
    return res


@app.get("/process_text")
async def process_text(
    name: str = "sv_se_1", input: str = "den 3 februari såg jag en häst"
):
    if textprocs is None:
        raise Exception("textprocs not initialized")
    if not name in textprocs:
        msg = f"No such textproc: {name}"
        logger.error(msg)
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
