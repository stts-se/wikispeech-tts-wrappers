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
            rf = component["rules"]
            path = io.find_file(rf, resource_paths)
            if path is None:
                raise IOError(f"Failed to find textproc rules {rf}")
            with open(path, "r") as fh:
                rules = json.load(fh)
                rbnf_lang = rules["rbnf_lang"]
                if rules["sentence_split_re"]:
                    sentence_split_re = re.compile(rules["sentence_split_re"])
                token_split_re = re.compile(rules["token_split_re"])
                punctuation_re = re.compile(f"^((?:{rules['punctuation_re']})*)(.*?)((?:{rules['punctuation_re']})*)$")
                rewrite_rules = rules["rules"]
                for r in rewrite_rules:
                    if r.get("ignore_case",True): 
                        r["input_compiled"] = re.compile(r["input"],re.IGNORECASE)
                    else:
                        r["input_compiled"] = re.compile(r["input"])
                textprocs[name] = Textproc(
                    name,
                    lang,
                    rbnf_lang,
                    sentence_split_re,
                    token_split_re,
                    punctuation_re,
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
    punctuation_re: object
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
        logger.debug(f"textproc.process_text called with {text}")
        utts = []
        acc = text
        m = self.sentence_split_re.search(acc)
        while m:
            acc = self.sentence_split_re.sub("\t\\2", acc)
            m = self.sentence_split_re.match(acc)
        for utt in re.compile("\t").split(acc):
            utts.append(self.process_utt(utt))
        return utts

    def toksplit(self, utt: str):
        input_tokens = self.token_split_re.split(utt)
        res = []
        for t in input_tokens:
            m = self.punctuation_re.match(t)
            prepunct = m.group(1)
            word = m.group(2)
            word2, tags = self.process_numeral(word)
            postpunct = m.group(3)
            token = {
                "input": t,
                "word": word2
            }
            if tags is not None and len(tags) > 0:
                token["tags"] = tags
            if len(prepunct) > 0:
                token["prepunct"] = prepunct
            if len(postpunct) > 0:
                token["postpunct"] = postpunct
            res.append(token)
        return res           
    
    def process_numeral(self, s: str):
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
        return processed_token, tags
    
    def apply_rewrite_rule(self, rule, s: str):
        res = []
        rex = rule["input_compiled"]
        #print("rule", rule)
        #print("input", s)
        if rule["rule_type"] == "token":
            tokens = self.toksplit(s)
            for tok in tokens:
                m = rex.match(tok["input"])
                if m:
                    alias= rex.sub(rule["output"], tok["input"])
                    res.append({
                        "type": "alias",
                        "text": tok["input"],
                        "alias": alias
                    })
                else:
                    res.append({
                        "type": "text",
                        "text": tok["input"]
                    })
        else:
            matches = rex.finditer(s)
            i = 0
            rest = s
            for m in matches:
                span = m.span()
                res.append({
                    "type": "text",
                    "text": s[i:span[0]].strip()
                })
                text = s[span[0]:span[1]]
                rest = s[span[1]:len(s)]
                i = span[1]
                alias = rex.sub(rule["output"],text)
                res.append({
                    "type": "alias",
                    "text": text,
                    "alias": alias
                })
            if len(rest) > 0:
                end = {
                    "type": "text",
                    "text": rest.strip()
                }
                res.append(end)
        return res
        
    def apply_rewrite_rules(self, item: object):
        acc = [item]
        for r in self.rewrite_rules:
            acc0 = acc
            acc = []
            for item in acc0:
                if item["type"] == "text":
                    subitems = self.apply_rewrite_rule(r, item["text"])
                    acc.extend(subitems)
                    #print("with subitems", acc)
                elif item["type"] == "alias":
                    acc.append(item)
                elif item["type"] == "phonemes":
                    acc.append(item)
                else:
                    raise ValueError(item)
        return acc

    def process_utt(self, input: object, input_type="text"):
        logger.debug(f"textproc.process_utt called with {input}")
        items = []
        if input_type == "text":
            items = [{
                    "type": "text",
                    "text": input
                }]
        else:
            items = input
        res = []
        for item in items:
            if item["type"] == "text":
                subitems = self.apply_rewrite_rules(item)
                for i, item in enumerate(subitems):
                    if item["type"] == "text":
                        item["tokens"] = self.toksplit(item["text"])
                    elif item["type"] == "alias":
                        item["tokens"] = self.toksplit(item["alias"])
                    subitems[i] = item                    
                res.extend(subitems)
            elif item["type"] == "alias":
                if not "tokens" in item:
                    item["tokens"] = self.toksplit(item["alias"])
                res.append(item)
            elif item["type"] == "phonemes":
                item["tokens"] = []
                res.append(item)

        derived_input = []
        derived_output = ""
        for item in res:
            if "text" in item:
                derived_input.append(item["text"])
            for token in item["tokens"]:
                t = f"{token.get('prepunct','')}{token['word']}{token.get('postpunct','')}"
                # TODO: corner case with triple consonants here?
                derived_output = derived_output + t
                if not "nodelim" in token.get("tags",[]):
                    derived_output = derived_output + " "
        complete_res = {
            "input": input,
            "derived_input_text": " ".join(derived_input),
            "derived_output_text": derived_output.strip(),
            "tokens": res
        }
        print(complete_res)
        return complete_res
        
