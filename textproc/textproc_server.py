# For usage info, se README.md

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import json, re
from unicode_rbnf import RbnfEngine, FormatPurpose

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from tools import io

json_config = os.getenv("TEXTPROC_CONFIG")  # Reads from .env file passed to uvicorn
if not json_config:
    raise RuntimeError("Config not provided. Start server with --env-file")

load_dotenv()

# Logging
import logging

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)

int_re = re.compile("^[0-9]+$")
roman_re = re.compile("^[XIV]+$")
year_re = re.compile("^[0-9]{4}$")
float_re = re.compile("^[0-9]+[.][0-9]+$")
comma_float_re = re.compile("^[0-9]+[,][0-9]+$")
roman_re = re.compile("^[XIVMCLD]+$")
# other_num_re = re.compile("[0-9]")

textprocs = {}


def roman2int(s):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for ch in reversed(s):
        val = values[ch]
        result += val if val >= prev else -val
        prev = val
    return result


from dataclasses import dataclass, asdict


@dataclass
class Textproc:
    name: str
    lang: str
    rbnf_lang: str
    sentence_split_re: object
    token_split_re: object
    rewrite_rules: list
    enabled: bool

    def __post_init__(self):
        self.loaded = False
        self.rbnf = RbnfEngine.for_language(self.rbnf_lang)

    def __str__(self):
        dict = asdict(self)
        return f"{dict}"

    def rbnfify(self, number, fmt=None):
        if fmt is None:
            rbnfed = self.rbnf.format_number(number)
            return rbnfed.text
        else:
            rbnfed = self.rbnf.format_number(number, fmt)
            return rbnfed.text

    def process_text(self, text: str):
        res = []
        for utt in self.sentence_split_re.split(text):  # TODO: more advanced splitting
            res.append(self.process_utt(utt))
        return res

    def apply_rewrite_rules(self, utt: str):
        acc = utt
        for r in self.rewrite_rules:
            if r["rule_type"] == "token":
                tokens = self.token_split_re.split(acc)
                t2s = []
                for tok in tokens:
                    rex = re.compile(r["input"])
                    t2 = rex.sub(r["output"], tok)
                    t2s.append(t2)
                acc = " ".join(t2s)
            else:
                rex = re.compile(r["input"])
                acc = rex.sub(r["output"], acc)
        return self.token_split_re.split(acc)

    def process_utt(self, utt: str):
        res = []
        tokens = self.apply_rewrite_rules(utt)
        for i, s in enumerate(tokens):
            fs = s.split("|||")
            tag = ""
            if len(fs) > 1:
                s = fs[0]
                tag = fs[1]
            formatPurpose = None
            if tag == "ordinal":
                formatPurpose = FormatPurpose.ORDINAL
            if tag == "year":
                formatPurpose = FormatPurpose.YEAR
            prev = None
            next = None
            if i > 0:
                prev = tokens[i - 1]
            if i < len(tokens) - 1:
                next = tokens[i + 1]
            if roman_re.match(s):
                i = roman2int(s)
                rbnfed = self.rbnfify(i, formatPurpose)
                res.append(rbnfed)
            elif year_re.match(s):
                i = int(s)
                if formatPurpose is None:
                    rbnfed = self.rbnfify(i, FormatPurpose.YEAR)
                else:
                    rbnfed = self.rbnfify(i, formatPurpose)
                res.append(rbnfed)
            elif int_re.match(s):
                i = int(s)
                rbnfed = self.rbnfify(i, formatPurpose)
                res.append(rbnfed)
            elif float_re.match(s):
                f = float(s)
                rbnfed = self.rbnfify(f, formatPurpose)
                res.append(rbnfed)
            elif comma_float_re.match(s):
                f = float(s.replace(",", "."))
                rbnfed = self.rbnfify(f, formatPurpose)
                res.append(rbnfed)
            else:
                res.append(s)
        return res


def load_config():
    with open(json_config, "r") as file:
        data = json.load(file)
        resource_paths = [os.path.expandvars(x) for x in data["resource_paths"]]
        for component in data["textprocs"]:
            name = component["name"]
            enabled = component["enabled"]
            if not enabled:
                continue
            lang = component["lang"]
            rbnf_lang = component["rbnf_lang"]
            sentence_split_re = re.compile(component["sentence_split_re"])
            token_split_re = re.compile(component["token_split_re"])
            logger.debug(f"Dict loading is not implemented")
            rewrite_rules = []
            for f in component["rewrite_rules"]:
                path = io.find_file(f, resource_paths)
                if path is None:
                    raise IOError(f"Failed to find rewrite rules {f}")
                with open(path, "r") as fh:
                    rr_data = json.load(fh)
                    rewrite_rules = rewrite_rules + rr_data
            textprocs[name] = Textproc(
                name,
                lang,
                rbnf_lang,
                sentence_split_re,
                token_split_re,
                rewrite_rules,
                True,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    yield


app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"tryItOutEnabled": True})


@app.get("/process_utt")
async def process_utt(name: str = "sv_se_1", input: str = "hej då 17"):
    if not name in textprocs:
        msg = f"No such textproc: {name}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[name]
    res = comp.process_utt(input)

    # assert engine.format_number(1234).text == "one thousand two hundred thirty-four"
    return res


@app.get("/process_text")
async def process_text(
    name: str = "sv_se_1", input: str = "den 3 februari såg jag en häst"
):
    if not name in textprocs:
        msg = f"No such textproc: {name}"
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)
    comp = textprocs[name]
    res = comp.process_text(input)

    # assert engine.format_number(1234).text == "one thousand two hundred thirty-four"
    return res
