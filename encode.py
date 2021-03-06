import os
import re
import sys
import time
import shutil
import logging
import argparse
import platform
import subprocess
from enum import Enum
from typing import List
from io import StringIO
from pathlib import Path
from collections import defaultdict


class EncoderChoice(Enum):
    X264 = 'x264'
    X265 = 'x265'


class Encoder:
    def __init__(self, encoder: EncoderChoice, executable_path: Path):
        self.encoder = encoder
        self.executable_path = executable_path


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    green = "\x1b[32;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(asctime)s][%(levelname)s] - %(message)s"
    is_windowns = platform.system() == 'Windows'
    FORMATS = {
        logging.DEBUG: grey + format + reset if not is_windowns else format,
        logging.INFO: green + format + reset if not is_windowns else format,
        logging.WARNING: yellow + format + reset if not is_windowns else format,
        logging.ERROR: red + format + reset if not is_windowns else format,
        logging.CRITICAL: bold_red + format + reset if not is_windowns else format
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)


class Encode:

    def __init__(self, script: Path, vspipe: Path, encoder: Encoder, param: str):
        self.script = script
        self.vspipe = vspipe
        self.encoder = encoder
        self.param = param
        self.proc = None

    def __repr__(self):
        return f"\nEncoder: {self.encoder.encoder.name}\nScript:  {self.script}\nParam:   {self.param}"

    def _execute(self, cmd):
        extra_args = {}
        if platform.system() == 'Windows':
            from subprocess import STARTUPINFO
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.BELOW_NORMAL_PRIORITY_CLASS
            extra_args['startupinfo'] = startupinfo
        self.proc = subprocess.Popen(cmd, shell=True, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     universal_newlines=True, **extra_args)
        for stdout in iter(self.proc.stdout.readline, ""):
            yield stdout
        self.proc.stdout.close()
        self.return_code = self.proc.wait()
        if self.return_code:
            self.logger.error(f"{cmd} failed with return code {self.return_code}")
    
    def _set_logger(self):
        fh = logging.FileHandler(f'{self.output_path.absolute()}.log', mode='a', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        self.logger = logging.getLogger(self.output_path.name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)
        self.logger.info(str(self) + '\n')

    def _write_info(self):
        cmd = f'"{self.vspipe.absolute()}" --info "{self.script.absolute()}" -'
        out = subprocess.run(cmd, shell=True, capture_output=True).stdout.decode('utf-8')
        self.logger.info(out)
        logger.info('\n' + out)

    def run(self):
        max_num = -1
        for f in os.listdir(self.script.parents[0]):
            if m := re.match(fr"{self.script.name[:-4]}_{self.encoder.encoder.value}_([\d]+)", f):
                if m.group(1).isdigit() and int(m.group(1)) > max_num:
                    max_num = int(m.group(1))

        self.output_path = self.script.parents[0].joinpath(
            f"{self.script.name[:-4]}_{self.encoder.encoder.value}_{max_num+1}")
        
        self._set_logger()
        self._write_info()
        cmd = (f'"{self.vspipe.absolute()}" "{self.script.absolute()}" - --y4m '
               f'| "{self.encoder.executable_path.absolute()}" '
               f"{'--demuxer y4m' if self.encoder.encoder == EncoderChoice.X264 else '--y4m'} "
               f"{self.param} "
               f"-o \"{self.output_path.absolute()}.{'hevc' if self.encoder.encoder == EncoderChoice.X265 else 'mkv'}\" -")
        self.logger.info(f"Built command: \n{cmd}\n")
        prev = ''
        for out in self._execute(cmd):
            out = out.strip()
            if re.sub('\d', '', out) != re.sub('\d', '', prev):
                self.logger.info(out)
                print(out)
            else:
                print(out, end='\r')
            sys.stdout.flush()
            prev = out
        return self.return_code


def find_vspipe():
    if p := os.environ.get(f'VSPIPEPATH'):
        return Path(p)
    if platform.system() == 'Windows':
        if p := shutil.which('vspipe.exe'):
            return Path(p)
    else:
        if p := shutil.which('vspipe'):
            return Path(p)
    return None


def find_encoders(encoder: EncoderChoice):
    if p := os.environ.get(f'{encoder.name}PATH'):
        return Path(p)
    if platform.system() == 'Windows':
        possible_executables = map(lambda s: encoder.value + s, ['.exe', '_x64.exe', '_x86.exe'])
    else:
        possible_executables = map(lambda s: encoder.value + s, [''])

    for e in possible_executables:
        if p := shutil.which(e):
            return Path(p)
    logger.warning(f"Cannot find {encoder.value} encoder, please put the executable in Path or set {encoder.name}PATH")
    return None


def encode(encodes: List[Encode]) -> defaultdict(int):
    logger.debug(f"Queueing {len(encodes)} encode tasks: {''.join(map(lambda e: str(e), encodes))}")
    return_codes = defaultdict(int)
    for encode in encodes:
        logger.info("\n===========================================")
        logger.info(f"Executing encode tasks: {encode}")
        return_codes[encode.run()] += 1
    logger.info(f"Success: {return_codes[0]}. Failed: {sum(return_codes.values()) - return_codes[0]}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Vapoursynth help script.')
    parser.add_argument('-s', '--script', action='extend', nargs='+', help='The path to the vpy script', required=True)
    parser.add_argument('-e', '--encoder', action='extend', nargs='+', type=EncoderChoice,
                        help='The encoder to use for the vpy script', required=True)
    parser.add_argument('-p', '--param', action='extend', nargs='+', help='The encoder parameters for each script',
                        required=True)
    parser.add_argument('--preset', action='extend', nargs='+', help='The preset defined in encodeconfig',
                        required=False)
    args = parser.parse_args()

    max_len = max(len(args.encoder), len(args.script), len(args.param))
    if len(args.script) < max_len:
        args.script += [args.script[-1]] * (max_len - len(args.script))
    if len(args.encoder) < max_len:
        args.encoder += [args.encoder[-1]] * (max_len - len(args.encoder))
    if len(args.param) < max_len:
        args.param += [args.param[-1]] * (max_len - len(args.param))
    if args.preset:
        if len(args.preset) < max_len:
            args.preset += [args.preset[-1]] * (max_len - len(args.preset))
    else:
        args.preset = [''] * max_len

    vspipe = find_vspipe()
    if vspipe is None:
        logger.error("Cannot find vspipe, please put the executable in Path or set VSPIPEPATH")
        sys.exit(1)

    scripts = list(zip(args.script, args.encoder, args.param, args.preset))
    encodes = []
    encoders = {}
    for script, encoder, param, preset in scripts:
        print(preset)
        if not os.path.isfile(script):
            logger.warning(f"Script not found! Skipping: {script}")
            continue
        elif script[-4:] != '.vpy':
            logger.warning(f"Not a Vapoursynth script! Skipping: {script}")
            continue
        if preset:
            import encodeconfig
            if preset_params := encodeconfig.encoder[encoder.value]['presets'].get(preset):
                param = preset_params + ' ' + param
            else:
                logger.warning(f"Not found preset {preset}")
        if encoder in encoders:
            encodes.append((Encode(Path(script), vspipe, encoders.get(encoder), param)))
        elif e := find_encoders(encoder):
            encoders[encoder] = Encoder(encoder, e)
            encodes.append((Encode(Path(script), vspipe, encoders[encoder], param)))

    if len(encodes) <= 0:
        logger.error(f"No encode task found, aborting...")
        sys.exit(1)
    encode(encodes)