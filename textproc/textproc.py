import os
import sys
import json
import re
from unicode_rbnf import RbnfEngine, FormatPurpose, FormatOptions
from typing import Final

# Logging
import logging
logger = logging.getLogger("textproc")
logger.setLevel(logging.DEBUG)

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, parentdir)
from common import io

INT_RE: Final[str] = re.compile("^[0-9]+$")
FLOAT_RE: Final[str] = re.compile("^[0-9]+[.][0-9]+$")
ROMAN_RE: Final[str] = re.compile("^[XIVMCLD]+$")
YEAR_RE: Final[str] = re.compile("^1[0-9]{3}$")
COMMA_FLOAT_RE: Final[str] = re.compile("^[0-9]+[,][0-9]+$")

def roman2int(s):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for ch in reversed(s):
        val = values[ch]
        result += val if val >= prev else -val
        prev = val
    return result

def load_nested_files(rules, resource_paths):
    res = []
    for r in rules:
        if r["rule_type"] == "file":
            path = io.find_file(r["file"], resource_paths)
            if path is None:
                raise IOError(f"Failed to find nexted textproc rules {r['file']}")
            with open(path, "r") as fh:
                rules = json.load(fh)
                res.extend(rules)
        else:
            res.append(r)
    return res

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
                p_re = f"^((?:{rules['punctuation_re']})*)(.*?)((?:{rules['punctuation_re']})*)$"
                punctuation_re = re.compile(p_re)
                punctuation_after_match = re.compile(f"^((?:{rules['punctuation_re']})+)( |$)")
                rewrite_rules = load_nested_files(rules["rules"], resource_paths)
                for id, r in enumerate(rewrite_rules,start=1):
                    if r.get("rule_type","") == "file":
                        raise IOError(f"A nested rule file cannot contain nested rule files: {r}")
                    r["id"] = id
                    if r.get("ignore_case",True): 
                        r["input_compiled"] = re.compile(r["input"],re.IGNORECASE)
                    else:
                        r["input_compiled"] = re.compile(r["input"])
                textprocs[name] = Textproc(
                    name = name,
                    lang = lang,
                    rbnf_lang = rbnf_lang,
                    sentence_split_re = sentence_split_re,
                    token_split_re = token_split_re,
                    punctuation_re = punctuation_re,
                    punctuation_after_match = punctuation_after_match,
                    rbnf_compound_delimiter = rules.get("rbnf_compound_delimiter",None),
                    rewrite_rules = rewrite_rules,
                    tests = rules["tests"],
                    enabled = rules.get("enabled",True),
                    fail_on_error = rules.get("fail_on_error",True)
                )
                logger.info(f"Loaded textproc {name} with {len(rules['tests'])} rules")
    return textprocs

from dataclasses import dataclass, asdict

SOFT_HYPHEN: Final[str] = "\u00AD"

@dataclass
class Textproc:
    name: str
    lang: str
    rbnf_lang: str
    sentence_split_re: object
    token_split_re: object
    punctuation_re: object
    punctuation_after_match: object
    rbnf_compound_delimiter: str or None
    rewrite_rules: list
    tests: list
    fail_on_error: bool
    enabled: bool

    def __post_init__(self):
        self.loaded = False
        self.rbnf = RbnfEngine.for_language(self.rbnf_lang)

    def __str__(self):
        dict = asdict(self)
        return f"{dict}"

    def rbnfify(self, number, fmt=None):
        opts = FormatOptions.PRESERVE_SOFT_HYPENS
        res = number
        if fmt is None:
            rbnfed = self.rbnf.format_number(number=number, options=opts)
            res = rbnfed.text
        else:
            rbnfed = self.rbnf.format_number(number=number, purpose=fmt, options=opts)
            res = rbnfed.text
        if self.rbnf_compound_delimiter is not None:
            res = res.replace(SOFT_HYPHEN, self.rbnf_compound_delimiter)
        return res

    def process_text(self, text: str):
        #logger.debug(f"textproc.process_text called with {text}")
        utts = []
        acc = text
        m = self.sentence_split_re.search(acc)
        while m:
            acc = self.sentence_split_re.sub("\t\\2", acc)
            m = self.sentence_split_re.match(acc)
        for utt in re.compile("\t").split(acc):
            utts.append(self.process_utt(utt))
        return utts

    def toksplit(self, utt: str, process_numeral=True):
        input_tokens = self.token_split_re.split(utt)
        res = []
        for t in input_tokens:
            m = self.punctuation_re.match(t)
            if m is None:
                raise Exception(f"Expected token '{t}' to match punctuation_re /{self.punctuation_re.pattern}/")
            prepunct = m.group(1)
            word = m.group(2)
            if process_numeral:
                word2, tags = self.process_numeral(word)
            else:
                word2, tags = word, []
            postpunct = m.group(3)
            word = {
                "input": t,
                "word": word2
            }
            if tags is not None and len(tags) > 0:
                word["tags"] = tags
            if len(prepunct) > 0:
                word["prepunct"] = prepunct
            if len(postpunct) > 0:
                word["postpunct"] = postpunct
            res.append(word)
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
        if len(s) > 1 and ROMAN_RE.match(s):
            i = roman2int(s)
            processed_token = self.rbnfify(i, formatPurpose)
        elif ROMAN_RE.match(s) and "roman" in tags:
            i = roman2int(s)
            processed_token = self.rbnfify(i, formatPurpose)
        elif ROMAN_RE.match(s) and "ordinal" in tags:
            i = roman2int(s)
            processed_token = self.rbnfify(i, formatPurpose)
        elif YEAR_RE.match(s):
            i = int(s)
            if formatPurpose is None:
                formatPurpose = FormatPurpose.YEAR
                processed_token = self.rbnfify(i, formatPurpose)
            else:
                processed_token = self.rbnfify(i, formatPurpose)
        elif INT_RE.match(s):
            i = int(s)
            processed_token = self.rbnfify(i, formatPurpose)
        elif FLOAT_RE.match(s):
            f = float(s)
            processed_token = self.rbnfify(f, formatPurpose)
        elif COMMA_FLOAT_RE.match(s):
            f = float(s.replace(",", "."))
            processed_token = self.rbnfify(f, formatPurpose)
        return processed_token, tags
    
    def apply_rewrite_rule(self, rule, s: str):
        res = []
        rex = rule["input_compiled"]
        if rule["rule_type"] == "token":
            tokens = self.toksplit(s)
            for tok in tokens:
                m = rex.match(tok["input"])
                if m:
                    alias = ""
                    try:
                        alias = rex.sub(rule["output"], tok["input"])
                    except Exception as e:
                        logger.error(f"Couldn't replace {tok['input']} to {rule['output']} with rule {rule}")
                        raise e
                    res.append({
                        "type": "alias",
                        "text": tok["input"],
                        "alias": alias
                    })
                else:
                    m = rex.match(tok["word"])
                    if m:
                        alias= tok.get("prepunct","")+rex.sub(rule["output"], tok["word"])+tok.get("postpunct","")
                        text = tok["input"]
                        t2 = {
                            "type": "alias",
                            "text": text,
                            "alias": alias
                        }
                        res.append(t2)
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
                alias = alias.replace("  "," ")
                mx = self.punctuation_after_match.match(rest)
                if mx:
                    n = len(mx.group(1))
                    rest = s[span[1]+n:len(s)]
                    alias = alias+mx.group(1)
                    if rule.get("strip",False):
                        alias = alias.strip()
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
                elif item["type"] == "alias":
                    acc.append(item)
                elif item["type"] == "phonemes":
                    acc.append(item)
                else:
                    raise ValueError(item)
        return acc

    def process_utt(self, input: object, input_type="text"):
        logger.info(f"textproc.process_utt called with {input} / {input_type}")
        print(f"textproc.process_utt called with {input} / {input_type}")        
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
                        item["words"] = self.toksplit(item["text"])
                    elif item["type"] == "alias":
                        item["words"] = self.toksplit(item["alias"])
                    elif item["type"] == "phonemes":
                        item["words"] = [
                            {
                                "orth": item["text"],
                                "phonemes": item["phonemes"]
                            }
                        ]
                    subitems[i] = item                    
                res.extend(subitems)
            elif item["type"] == "alias":
                if not "tokens" in item:
                    item["words"] = self.toksplit(item["alias"])
                res.append(item)
            elif item["type"] == "phonemes":
                i = {
                    "text": item["text"],
                    "type": item["type"],
                    "words": [
                        {
                            "word": item["text"],
                            "phonemes": item["phonemes"]
                        }
                    ]
                }
                res.append(i)


        # TODO: merge words with nodelim
        # for t in res:
        #     wds = []
        #     accWs = []
        #     for i, w0 in enumerate(t["words"]):
        #         print(w0)
        #         accWs.append(w0)
        #         if "tags" in w0 and "nodelim" in w0["tags"]:
        #             print(accWs)
        #             accWs = []
            

        derived_input = []
        derived_output = ""
        for item in res:
            if "text" in item:
                derived_input.append(item["text"])

            # for punctuation on its own, we use the word attribute
            for token in item["words"]:
                if token.get("word","") == "":
                    pre = token.get("prepunct","")
                    post = token.get("postpunct","")
                    punct = pre+post
                    token["word"] = punct
                    if "prepunct" in token:
                        token.pop("prepunct")
                    if "postpunct" in token:
                        token.pop("postpunct")                    

                t = f"{token.get('prepunct','')}{token['word']}{token.get('postpunct','')}"
                derived_output = derived_output + t
                if not "nodelim" in token.get("tags",[]):
                    derived_output = derived_output + " "
        derived_output = derived_output.replace("  "," ")
        complete_res = {
            "input": input,
            "derived_input_text": " ".join(derived_input),
            "derived_output_text": derived_output.strip(),
            "tokens": res
        }
        return complete_res

    def self_tests(self):
        errs = []
        nOK = 0
        for test in self.tests:
            input = test["from"]
            expect = test["to"]
            result = self.process_utt(input)
            result_text = result["derived_output_text"]
            if expect == result_text:
                logger.debug(f"textproc selftest {self.name} COMBINED | {input} -> {expect} | OK")
                nOK+=1
            else:
                err = f"textproc selftest {self.name} COMBINED | {input} -> expected: <{expect}> got: <{result_text}> | FAILED"
                logger.error(err)
                errs.append(err)
        for r in self.rewrite_rules:
            for test in r.get("test",r.get("tests",[])):
                input = test["from"]
                expect = test["to"]
                result = self.apply_rewrite_rule(r, input)
                for i, item in enumerate(result):
                    if item["type"] == "text":
                        item["tokens"] = self.toksplit(item["text"], process_numeral=False)
                    elif item["type"] == "alias":
                        item["tokens"] = self.toksplit(item["alias"], process_numeral=False)
                    result[i] = item                    

                result_text = ""
                for item in result:
                    for token in item["tokens"]:
                        t = f"{token.get('prepunct','')}{token['word']}{token.get('postpunct','')}"
                        result_text = result_text + t
                        if not "nodelim" in token.get("tags",[]):
                            result_text = result_text + " "
                result_text = result_text.strip()
                result_text = result_text.replace("  "," ")
                if expect == result_text:
                    logger.debug(f"textproc selftest {self.name} rule #{r['id']} | {input} -> {expect} | OK")
                    nOK+=1
                else:
                    err = f"textproc selftest {self.name} rule #{r['id']} | {input} -> expected: <{expect}> got: <{result_text}> | FAILED"
                    logger.error(err)
                    errs.append(err)
                            
        logger.info(f"textproc selftests {self.name}: {nOK} OK, {len(errs)} failed")
        return errs
        
