#!/usr/bin/env python3

import argparse, csv, subprocess
from collections import defaultdict
from subprocess import PIPE

def bb_to_fline(bb_csv, binary, addr2line):
    assert bb_csv.endswith('bb.csv'), 'not normalized name'
    f_csv = bb_csv[:-6] + 'f.csv'
    line_csv = bb_csv[:-6] + 'line.csv'
    with open(bb_csv, 'r') as bb_csv_file, open(f_csv, 'w') as f_csv_file, open(line_csv, 'w') as line_csv_file:
        bb_reader = csv.DictReader(bb_csv_file)
        fieldnames = bb_reader.fieldnames.copy()
        for name in ['entry', 'execution', 'exit']:
            fieldnames.remove(name)

        f_fieldnames = fieldnames.copy()
        line_fieldnames = fieldnames.copy()
        f_fieldnames.insert(0, 'name')
        line_fieldnames.insert(0, 'source_line')

        fs_metrics = defaultdict(lambda:defaultdict(int))
        lines_metrics = defaultdict(lambda:defaultdict(int))

        for bb in bb_reader:
            entry = bb['entry']
            addr2line_cmd = f'{addr2line} -e {binary} -a {entry} -f'
            fline = subprocess.run(addr2line_cmd.split(), stdout=PIPE, stderr=PIPE, check=True)
            # Assume output looks like:
            #
            # 0x00000000004011a4
            # main
            # a.c:11
            fline = fline.stdout.decode('utf-8').strip()
            lines = fline.splitlines()
            name = lines[1].strip()
            source_line = lines[2].strip()
            f_metrics = fs_metrics[name]
            line_metrics = lines_metrics[source_line]
            f_metrics['name'] = name
            line_metrics['source_line'] = source_line

            for key, val in bb.items():
                if key in f_fieldnames:
                    f_metrics[key] += int(val or 0)
                if key in line_fieldnames:
                    line_metrics[key] += int(val or 0)

        f_writer = csv.DictWriter(f_csv_file, fieldnames=f_fieldnames)
        f_writer.writeheader()
        for key, val in fs_metrics.items():
            f_writer.writerow(val)

        line_writer = csv.DictWriter(line_csv_file, fieldnames=line_fieldnames)
        line_writer.writeheader()
        for key, val in lines_metrics.items():
            line_writer.writerow(val)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get function & line profiling info from basic block info (CSV format), where entry, execution, exit are required')
    parser.add_argument('bb_csv', help='input bb CSV file')
    parser.add_argument('binary', help='profiled binary')
    parser.add_argument('--addr2line', default='addr2line', help='path of addr2line (this is needed if dwarf format of binary is not supported by system addr2line)')
    args = parser.parse_args()
    bb_csv = args.bb_csv
    binary = args.binary
    addr2line = args.addr2line
    bb_to_fline(bb_csv, binary, addr2line)
