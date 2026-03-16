import argparse
import os
import sys
import json
import re

from unicode_rbnf import RbnfEngine, FormatPurpose

parser = argparse.ArgumentParser(
    prog='rbnf'
)

parser.add_argument('-l', '--lang', default="sv")
parser.add_argument('-f', '--format-purpose', default="cardinal")
parser.add_argument('input', type=str, help="Input string")

args = parser.parse_args()

rbnf = RbnfEngine.for_language(args.lang)

format_purpose = FormatPurpose.CARDINAL
if args.format_purpose.lower() == "ordinal":
    format_purpose = FormatPurpose.ORDINAL
elif args.format_purpose.lower() == "year":
    format_purpose = FormatPurpose.YEAR
else:
    print(f"Cannot convert format-purpose {args.format_purpose} to rbnf type. Try cardina, ordinal or year", file=sys.stderr)
rbnfed = rbnf.format_number(args.input,format_purpose)

print(type(rbnfed))

print(rbnfed)
