#!/usr/bin/env python3
# coding: utf-8


# CMDLINE USAGE
# python phn_mapper_main.py -o 1 -p 7 braxen2ipa_singlechar.txt metadata_endast_text_sardinproc_manuell_fix.txt

import sys, os
import re
import argparse
from pathlib import Path

import phn_mapper

def convert_datafiles(mper,files):
    for f in files:
        li=0
        print(f"Loading data file {f}", file=sys.stderr)
        lines = []
        if f.endswith(".gz"):
            import gzip
            with gzip.open(f,'rt') as fin:
                for line in fin:
                    line = line.strip()
                    lines.append(line)
        else:
            lines = Path(f).read_text().strip().split("\n")
        for l in lines:
            li+=1
            if l.startswith("------"):
                print(l)
                continue
            if l.startswith("INDEX"):
                print(l)
                continue
            if l == "" :
                continue
            fs = l.split(args.field_separator)
            if len(fs) <= args.phoneme_index:
                raise Exception(f"Invalid input line # {li}: {l}")
            if len(fs) <= args.orth_index:
                raise Exception(f"Invalid input line # {li}: {l}")

            orth = fs[args.orth_index]
            for ch in orth:
                if not ch in chars:
                    chars.append(ch)
            trans = fs[args.phoneme_index]
            trans = re.sub(r"\"", "\" ", trans)
            trans = re.sub(r"'", "' ", trans)
            trans = re.sub(r",", ", ", trans)
            trans = re.sub(r"  +"," ",trans)
            converted, error = mper.convert_trans(trans)
            if error is not None:
                print(f"SKIPPING LINE {li} (MAP ERROR FOR {orth})\t{error}\t{l}", file=sys.stderr)
            else:
                if args.keep_transcription:
                    fs.insert(args.phoneme_index+1, converted)
                else:
                    fs[args.phoneme_index] = converted
                print("\t".join(fs))
    

chars = []
cmd = os.path.basename(sys.argv[0])
parser = argparse.ArgumentParser(prog=cmd, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-f", "--field_separator", default="\t", help = "field separator for data files (default: tab))")
parser.add_argument("-o", "--orth_index", type=int, default=0, help = "column index in data file to convert (default: 0)")
parser.add_argument("-p", "--phoneme_index", type=int, default=1, help = "column index in data file to convert (default: 1)")
parser.add_argument("-s", "--phoneme_separator", default=" ", help = "phoneme separator in transcriptions (default: ' ')")
parser.add_argument("-k", "--keep_transcription", action='store_true', help = "keep input transcription (default: off)")
parser.add_argument("maptable", help = "tab separated phoneme map table")
parser.add_argument("data", nargs="+", help = "tab separated data file(s) to convert")

try:
    args = parser.parse_args()
except Exception as ex:
    print(f"Error: {ex}", file=sys.stderr)
    sys.exit(1)

def __main__():
    mapper = phn_mapper.PhnMapper(args.phoneme_separator,args.maptable)
    convert_datafiles(mapper,args.data)
    chars.sort()
    phns = mapper.phns
    phns.sort()
    print(f"text_symbols: \"{''.join(chars)}\"", file=sys.stderr)
    print(f"phoneme_symbols: {phns}", file=sys.stderr)
    
__main__()

