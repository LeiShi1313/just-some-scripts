# just-some-scripts
Just some random scripts.

## encode.py
A script used streamline usage of vspipe and x264/x265, it can replace [Simple x264 launcher](https://github.com/lordmulder/Simple-x264-Launcher)

### Basic Usage

```shell
python encode.py -s vs.vpy -e x264 -p "--crf 18 --preset placebo --profile high --level 4.1 --bframes 12 --aq-mode 3 --aq-strength 0.80 --me umh --b-adapt 2 --direct auto --subme 11 --trellis 2 --no-dct-decimate --no-mbtree --colormatrix bt709 --colorprim bt709 --ipratio 1.30 --pbratio 1.20"
```

### Working with presets
You can have presets defined in `encodeconfig.py` and provide some extra parameters, the provided parameters will always the same parameters in presets
```shell
python encode.py -s vs.vpy -e x264 --preset PRESET1 -p "--crf 16"
```

### Provide encoder executable manually

The program will try to search `x264` for x264 and `x265` for x265 on Mac/Linux and `x264.exe`/`x264_x64.exe`/`x264_x86.exe` for x264 and `x265.exe`/`x265_x64.exe`/`x265_x86.exe` for x265 on Windows.

You can manually set encoder executable path by setting environment variables `X264PATH` or `X265PATH`.

```shell
X265PATH=/usr/local/bin/x265 python encode.py -s vapoursynth.vpy -e x265 -p "--crf 0"
```

### Batch encoding

#### Different scripts, different encoders, different parameters
```shell
python encode.py \
-s vs0.vpy -e x264 -p "--crf 16" \
-s vs1.vpy -e x265 -p "--crf 18"
```

#### Same script, different encoder, different parameters
```shell
python encode.py -s vs.vpy \
-e x264 -p "--crf 16" \
-e x265 -p "--crf 18"
```

#### Same script, same encoder, different parameters
```shell
python encode.py -e x264 -s vs.vpy \
-p "--crf 16" \
-p "--crf 18"
```

#### Different script, same encoder, same parameters
```shell
python encode.py -e x264 -p "--crf 18"
-s vs0.vpy -s vs1.vpy
```

#### Presets
```shell
python encode.py -s vs.vpy -e x265 --preset PRESET1 \
-p "--crf 18"
-p "--crf 19"
```