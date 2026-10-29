# vectors

Golden test vectors written by `py/gen_rtl_vectors.py` from the bit-exact integer model.

- `<algo>_W<bits>_<scenario>.vec` holds one sample per line as four hex words: x, d, the
  expected y and the expected e.
- `<algo>_W<bits>_<scenario>.w` holds the expected final weights, one per line.
- `rtl/` has the stress and corner-case sets used by the regression (short filters, extreme
  word lengths, saturation, freeze patterns). These also carry a `.flg` file with the expected
  sticky saturation flags.
- `power/` has the inputs for the gate-level power runs.
- `audio/` has two test WAV files for the simulation pipeline.

`tb/manifest.txt` lists which vector set goes with which core parameters.
