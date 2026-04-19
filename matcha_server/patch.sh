# PyTorch (Deep Phonemizer)
sed -i 's/checkpoint = torch.load(checkpoint_path, map_location=device)/checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.*/site-packages/dp/model/model.py
# MatchaTTS
sed -i 's/MatchaTTS.load_from_checkpoint(checkpoint_path, map_location=device)/MatchaTTS.load_from_checkpoint(checkpoint_path, map_location=device, weights_only=False)/' .venv/lib/python3.*/site-packages/matcha/cli.py
sed -i 's|\(plot_spectrogram_to_numpy.*\) f"{filename}.png")|\1 folder / f"{filename}.png")|' .venv/lib/python3.*/site-packages/matcha/cli.py
sed -i 's/w_ceil = torch.ceil(w) \* length_scale/w_ceil = torch.ceil(w) * length_scale\n        log.debug("trim_silence set to %s" % trim_silence)\n        if trim_silence:\n            w_ceil[:, :, 0] = 0   # remove leading silence, patched by STTS\n            w_ceil[:, :, -1] = torch.clamp(w_ceil[:, :, -1], max=3)  # trim trailing silence, patched by STTS/' .venv/lib/python3.*/site-packages/matcha/models/matcha_tts.py
sed -i 's/def synthesise(self, x, x_lengths, n_timesteps, temperature=1.0, spks=None, length_scale=1.0):/def synthesise(self, x, x_lengths, n_timesteps, temperature=1.0, spks=None, length_scale=1.0, trim_silence=False):/' .venv/lib/python3.*/site-packages/matcha/models/matcha_tts.py
