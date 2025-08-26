#!/usr/bin/env python3
# coding: utf-8

import sys
from pathlib import Path

class PhnMapper:
    phoneme_separator: str
    maptable = {}
    phns = []

    def __init__(self,phoneme_separator: str, maptable_file: str):
        self.phoneme_separator = phoneme_separator
        self.load_maptable(maptable_file)
    
    def load_maptable(self, f): 
        print(f"Loading maptable {f}", file=sys.stderr)
        for l in Path(f).read_text().split("\n"):
            if l.startswith("//"):
                continue
            fs = l.split("\t")
            phnFrom = fs[0]
            phnTo = ""
            if len(fs)==2:
                phnTo = fs[1]
            self.maptable[phnFrom] = phnTo
            if phnTo != "" and not phnTo in self.phns:
                for p in phnTo:
                    if p not in self.phns:
                        self.phns.append(p)
        print(f"Loaded {len(self.maptable)} symbols from maptable {f}", file=sys.stderr)

    # returns tuple: converted trans + error
    # if there is an error, the converted trans will be None
    def convert_trans(self, trans):
        t0 = trans
        if self.phoneme_separator == "":
            phonemes = list(trans)
        else:
            phonemes = trans.split(self.phoneme_separator)
        res = []
        for p in phonemes:
            if p in self.maptable:
                res.append(self.maptable[p])
            else:
                err = f"Cannot map phoneme /{p}/ in /{t0}/"
                return None, err
        return "".join(res), None
            
    
