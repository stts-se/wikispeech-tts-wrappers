import librosa
import soundfile as sf

# source /some/.env/bin/activate
# uv pip install librosa

###################################################################
### possibly using ffmpeg + soundfile to save directly as opus:
# import subprocess

# # write to a pipe as WAV
# proc = subprocess.Popen(
#     ["ffmpeg", "-y", "-f", "wav", "-i", "pipe:0", "-c:a", "libopus", "output.opus"],
#     stdin=subprocess.PIPE
# )

# sf.write(proc.stdin, y_trimmed, sr, format="WAV")
# proc.stdin.close()
# proc.wait()
#######################################


def trim_silence(in_file: str, out_file: str, trailing: bool = True):
    y, sr = librosa.load(in_file, sr=None)
    if not out_file.endswith(".wav"):
        raise Exception(f"Invalid output file type: {out_file} (only wav is supported)")
    if trailing:
        yt, (start, end) = librosa.effects.trim(y, top_db=40)
        sf.write(out_file, yt, sr)
    else:
        _, (start, end) = librosa.effects.trim(y, top_db=40)
        # Keep everything from first non-silent sample onward
        y_leading_trimmed = y[start:]
        sf.write(out_file, y_leading_trimmed, sr)
