import audio
#import uuid
from pathlib import Path

def test_trim_leading_and_trailing():
    fs = [
        "testdata/008_metadata_sv_1.opus",
        "testdata/038_metadata_sv_1.opus"
    ]
    for in_file in fs:
        #uid = uuid.uuid4()
        out_file = str(Path(in_file).with_suffix(".leading_trailing_trimmed.wav"))
        out_file = out_file.replace(".leading","_leading")
        print(in_file, "=>", out_file)
        audio.trim_silence(in_file, out_file, trailing=True)

        
def test_trim_leading():
    fs = [
        "testdata/008_metadata_sv_1.opus",
        "testdata/038_metadata_sv_1.opus"
    ]
    for in_file in fs:
        #uid = uuid.uuid4()
        out_file = str(Path(in_file).with_suffix(".leading_trimmed.wav"))
        out_file = out_file.replace(".leading","_leading")
        print(in_file, "=>", out_file)
        audio.trim_silence(in_file, out_file, trailing=False)
