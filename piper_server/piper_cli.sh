#!/bin/bash

set -e

cmd=`basename $0`

if [ $# -eq 3 ]; then
    model=$1
    input=$2
    output=$3
    python3 -m piper -m $model -f $output -- $input
elif [ $# -eq 2 ]; then
    model=$1
    input=$2
    output=$3
    python3 -m piper -m $model -- $input
else
    echo "Usage: $cmd <onnx model> <input text or phonemes> <output file (optional)>" 1>&2
    exit 1
fi
