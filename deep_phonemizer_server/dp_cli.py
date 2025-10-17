import argparse

from dp.phonemizer import Phonemizer

parser = argparse.ArgumentParser(
    prog='dp_cli',
    description='A simple deep phonemizer client',
)

parser.add_argument('model')
parser.add_argument('lang')
parser.add_argument('text')

args = parser.parse_args()

dp = Phonemizer.from_checkpoint(args.model)

result = dp(args.text.lower(), lang=args.lang)

print(result)
