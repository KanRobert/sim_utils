#!/usr/bin/env python3
import os, argparse, glob, subprocess, shutil, filecmp, json, sys
from subprocess import PIPE
from collections import defaultdict

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

    exe_name = 'a.out'
    sim_file_name = 'a.err'
    disasm_name = 'a.out.disasm'

    [exe, sim_file, disasm] = [f'{test_dir}/{x}' for x in [exe_name, sim_file_name, disasm_name]]

    json_file = f'{sim_file}.json'

    if update:
        source_path = f'{src_test_dir}/a.c'
        compiler_cmd = f'gcc -g {source_path} -o {exe}'
        subprocess.run(compiler_cmd.split(), check=True)
        with open(disasm, 'w') as f:
            subprocess.run(['objdump', '-d', exe], stdout=f, check=True)

        sde_path = os.path.abspath(sde)
        sde_cmd = f'{sde_path} -future -omix {sim_file} -top_blocks -1 -dynamic_stats_per_block -p -inline -p 0 -- {exe}'
        subprocess.run(sde_cmd.split(), stdout=PIPE, check=True)
    else:
        shutil.rmtree(tmp_test_dir, ignore_errors=True)
        os.makedirs(tmp_test_dir, exist_ok=True)
        for f in [f'{src_test_dir}/{x}' for x in [exe_name, sim_file_name, disasm_name]]:
            shutil.copy(f, tmp_test_dir)

    subprocess.run(['./sde2csv.py', sim_file, exe, '--items=PUSH,POP'], check=True)
    subprocess.run(['./csv2json.py'] + glob.glob(f'{sim_file}.*.csv'), check=True)
    subprocess.run(['./annotater.py', disasm, json_file], check=True)
    subprocess.run(['./bb2fline.py', f'{sim_file}.bb.csv', exe], check=True)

    if not update:
        compare_and_report(['a.err.bb.csv', 'a.err.insn.csv', 'a.err.global.csv'], 'sde2csv.py')
        compare_and_report(['a.err.json'], 'csv2json.py')
        compare_and_report(['a.err.annotated'], 'annotater.py')
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
