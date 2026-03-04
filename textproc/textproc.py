import os
import sys
import json
import re
from unicode_rbnf import RbnfEngine, FormatPurpose

# Logging
import logging
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from tools import io

int_re = re.compile("^[0-9]+$")
roman_re = re.compile("^[XIV]+$")
year_re = re.compile("^1[0-9]{3}$")
float_re = re.compile("^[0-9]+[.][0-9]+$")
comma_float_re = re.compile("^[0-9]+[,][0-9]+$")
roman_re = re.compile("^[XIVMCLD]+$")

def roman2int(s):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for ch in reversed(s):
        val = values[ch]
        result += val if val >= prev else -val
        prev = val
    return result

def load_config(json_config):
    textprocs = {}
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
                    rewrite_rules = rewrite_rules + rr_data["rules"]
            textprocs[name] = Textproc(
                name,
                lang,
                rbnf_lang,
                sentence_split_re,
                token_split_re,
                rewrite_rules,
                True,
            )
    return textprocs

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
        utts = []
        acc = text
        m = self.sentence_split_re.search(acc)
        while m:
            acc = self.sentence_split_re.sub("\t\\2", acc)
            m = self.sentence_split_re.match(acc)
        for utt in re.compile("\t").split(acc):
            utts.append(self.process_utt(utt))
        return utts

    def apply_rewrite_rules(self, utt: str):
        acc = utt
        for r in self.rewrite_rules:
            if r["rule_type"] == "token":
                tokens = self.token_split_re.split(acc) # TODO: keep delimiters
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
        acc = []
        text = ""
        tokens = self.apply_rewrite_rules(utt)
        for i, s in enumerate(tokens):
            fs = s.split("|||",maxsplit=1)
            s = fs[0]
            tags = []
            if len(fs) > 1:
                tags = fs[1].split("|||")
            formatPurpose = None
            if "ordinal" in tags:
                formatPurpose = FormatPurpose.ORDINAL
            if "year" in tags:
                formatPurpose = FormatPurpose.YEAR
            prev = None
            next = None
            if i > 0:
                prev = tokens[i - 1]
            if i < len(tokens) - 1:
                next = tokens[i + 1]
            processed_token = s
            if len(s) > 1 and roman_re.match(s):
                i = roman2int(s)
                processed_token = self.rbnfify(i, formatPurpose)
            elif year_re.match(s):
                i = int(s)
                if formatPurpose is None:
                    formatPurpose = FormatPurpose.YEAR
                    processed_token = self.rbnfify(i, formatPurpose)
                else:
                    processed_token = self.rbnfify(i, formatPurpose)
            elif int_re.match(s):
                i = int(s)
                processed_token = self.rbnfify(i, formatPurpose)
            elif float_re.match(s):
                f = float(s)
                processed_token = self.rbnfify(f, formatPurpose)
            elif comma_float_re.match(s):
                f = float(s.replace(",", "."))
                processed_token = self.rbnfify(f, formatPurpose)
            acc.append({
                "input": s,
                "converted": processed_token,
                "tags": tags
            })
            text = text + processed_token
            if not "nbsp" in tags and i < len(tokens)-1:
                text = text + " "
        res = {
            "converted_text": text,
            "tokens": acc
        }
        return res
        # res = []
        # i = 0
        # while i < len(acc)-1:
        #     t1 = acc[i]
        #     t2 = acc[i+1]
        #     if "nbsp" in t1["tags"]:
        #         print(tok)
        #         tok["input"] = tok["input"] + " " + acc[i+1]["input"]
        #         tok["converted"] = tok["converted"] + acc[i+1]["converted"]
        #         tok["tags"].remove("nbsp")
        #         tok["tags"] = tok["tags"] + acc[i+1]["tags"]
        #         res.append(tok)
        #         #i=i+1
        #     else:
        #         res.append(tok)
            
        # return res

