#!/usr/bin/env python3
import argparse, csv, os, subprocess, glob
from subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_file(repo, sub_dir, sim_file, exe_path, items, disasm, args):
    # X -> Y means X relies on Y
    # annotater -> csv2json -> sde2csv
    #           -> objdump
    #
    # bb2fline -> sde2csv
    sim_file_path = os.path.join(sub_dir, sim_file)
    subprocess.run([os.path.join(repo, 'sde2csv.py'), sim_file_path, exe_path, f'--items={items}'], check=True)
    csv_files = glob.glob(f'{sim_file_path}.*.csv')
    subprocess.run([os.path.join(repo, 'csv2json.py')] + csv_files, check=True)
    annotater_popen = subprocess.Popen([os.path.join(repo, 'annotater.py'), disasm, f'{sim_file_path}.json'])
    bb2fline_popen = subprocess.Popen([os.path.join(repo, 'bb2fline.py'), f'{sim_file_path}.bb.csv', exe_path, '--addr2line', args.addr2line])
    return [annotater_popen, bb2fline_popen]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Process all the files in the directory by running sde2csv, csv2json, annotater, bb2fline on them. The mapping from workloads to files is described by a csv file, where name, exe, sim_files are required.')
    parser.add_argument('dir', help='directory of the inputs')
    parser.add_argument('--csv', required=True, help='csv file to describe the mappings')
    parser.add_argument('--items', help='extra interesting items in sim_files')
    parser.add_argument('--objdump', default='objdump', help='path to objdump (this is needed if instruction in binary is not supported by system objdump)')
    parser.add_argument('--addr2line', default='addr2line', help='path of addr2line (this is needed if dwarf format of binary is not supported by system addr2line)')
    args = parser.parse_args()

    repo = os.path.dirname(os.path.realpath(__file__))
    dir_path = args.dir
    items = args.items if args.items else ''

    with open(args.csv, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        futures = []
        popen_objs = []

        with ThreadPoolExecutor() as executor:
            for row in reader:
                name = row['name']
                exe = row['exe']
                sim_files = row['sim_files'].split(',')
                sub_dir = os.path.join(dir_path, name)
                exe_path = os.path.join(sub_dir, exe)

                disasm = exe_path + '.disasm'
                dump = subprocess.run([f'{args.objdump}', '-d', exe_path], stdout=PIPE, check=True)
                with open(disasm, 'w') as disasm_file:
                    disasm_file.write(dump.stdout.decode('utf-8'))
                    os.fsync(disasm_file.fileno())

                for sim_file in sim_files:
                    future = executor.submit(process_file, repo, sub_dir, sim_file, exe_path, items, disasm, args)
                    futures.append(future)

            for future in as_completed(futures):
                popen_objs.extend(future.result())

        [obj.wait() for obj in popen_objs]
