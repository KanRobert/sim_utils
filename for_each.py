#!/usr/bin/env python3
import argparse, csv, os, subprocess, glob
from subprocess import PIPE

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Process all the files in the directory by running sde2csv, csv2json, annotater, bb2fline on them. The mapping from workloads to files is described by a csv file, where name, exe, sim_files are required.')
    parser.add_argument('dir', help='directory of the inputs')
    parser.add_argument('--csv', required=True, help='csv file to describe the mappings')
    parser.add_argument('--items', help='Extra interesting items in sim_files')
    parser.add_argument('--objdump', default='objdump', help='path to objdump (this is needed if instruction in binary is not supported by system objdump)')
    parser.add_argument('--addr2line', default='addr2line', help='path of addr2line (this is needed if dwarf format of binary is not supported by system addr2line)')
    args = parser.parse_args()

    repo = os.path.dirname(os.path.realpath(__file__))
    popen_objs = []
    with open(args.csv, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        dir_path = args.dir
        items = args.items if args.items else ''
        for row in reader:
            name = row['name']
            exe = row['exe']
            sim_files = row['sim_files'].split(',')
            sub_dir = os.path.join(dir_path, name)
            exe_path = os.path.join(sub_dir, exe)

            disasm = exe_path + '.disasm'
            dump = subprocess.run([f'{args.objdump}', '-d', exe_path], stdout=PIPE, check=True)
            dump = dump.stdout.decode('utf-8')
            with open(disasm, 'w') as disasm_file:
                disasm_file.write(dump)

            for sim_file in sim_files:
                sim_file_path = os.path.join(sub_dir, sim_file)
                subprocess.run([os.path.join(repo, 'sde2csv.py'), sim_file_path, exe_path, f'--items={items}'], check=True)
                subprocess.run([os.path.join(repo, 'csv2json.py')] + glob.glob(f'{sim_file_path}.*.csv'), check=True)
                annoator_popen = subprocess.Popen([os.path.join(repo, 'annotater.py'), disasm, f'{sim_file_path}.json'])
                bb2fline_popen = subprocess.Popen([os.path.join(repo, 'bb2fline.py'), f'{sim_file_path}.bb.csv', exe_path, '--addr2line', args.addr2line])
                popen_objs += [annoator_popen, bb2fline_popen]

    for obj in popen_objs:
        obj.wait()
