#!/usr/bin/env python3
import re
import os
import argparse
from collections import defaultdict
import subprocess
from subprocess import PIPE
import glob
import shutil
import filecmp
import json
import sys

src_test_dir = './test_files'
tmp_test_dir = '.test_files'

def compare_and_report(files, script):
    for file in files:
        log = dict()
        ref = f'{src_test_dir}/{file}'
        exp = f'{tmp_test_dir}/{file}'
        log['ref'], log['exp'] = ref, exp
        same = filecmp.cmp(ref, exp)
        log['result'] = 'pass' if same else 'fail'
        log['testing script'] = script
        json.dump(log, sys.stdout, indent=2)
        print('\n', flush=True)
        if not same:
            subprocess.run(['git', 'diff', '--no-index', ref, exp])
            sys.exit(-1)

def generate(sde, update):
    test_dir = src_test_dir if update else tmp_test_dir

    exe = f'{test_dir}/a.out'
    disasm = exe + '.disasm'
    sde_file = f'{test_dir}/a.err'
    json_file = sde_file + '.json'

    if update:
        source_path = f'{src_test_dir}/a.c'
        compiler_cmd = f'gcc -g {source_path} -o {exe}'
        subprocess.run(compiler_cmd.split(), check=True)
        with open(disasm, 'w') as f:
            subprocess.run(['objdump', '-d', exe], stdout=f, check=True)

        sde_path = os.path.abspath(sde)
        sde_cmd = f'{sde_path} -future -omix {sde_file} -top_blocks -1 -dynamic_stats_per_block -p -inline -p 0 -- {exe}'
        subprocess.run(sde_cmd.split(), stdout=PIPE, check=True)
    else:
        shutil.copytree(src_test_dir, tmp_test_dir, dirs_exist_ok=True)

    subprocess.run(['./sde2csv.py', sde_file, exe, '--items=PUSH,POP'], check=True)
    subprocess.run(['./csv2json.py'] + glob.glob(f'{sde_file}.*.csv'), check=True)
    subprocess.run(['./annotater.py', disasm, json_file], check=True)
    subprocess.run(['./bb2fline.py', f'{sde_file}.bb.csv', exe], check=True)

    if not update:
        compare_and_report(['a.err.bb.csv', 'a.err.insn.csv', 'a.err.global.csv'], 'sde2csv.py')
        compare_and_report(['a.err.json'], 'csv2json.py')
        compare_and_report(['a.out.disasm.annotated'], 'annotater.py')
        compare_and_report(['a.err.f.csv', 'a.err.line.csv'], 'bb2fline.py')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Simple tests')
    parser.add_argument('-u', '--update', action='store_true', help='Update the test files')
    parser.add_argument('--sde', action='store', help='path of SDE')
    args = parser.parse_args()
    if args.update:
        assert args.sde, 'path of SDE is needed when --update is on'
    generate(args.sde, args.update)
