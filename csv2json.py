#!/usr/bin/env python3

import argparse
import csv
import json
import os
from collections import defaultdict

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def remove_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text

def covert_csv_to_json(csv_files):
    common_prefix = os.path.commonprefix(csv_files)
    with open(common_prefix.rstrip('.')+'.json', 'w') as json_file:
        json_dict = defaultdict(list)
        for csv_file in sorted(csv_files):
            name = remove_prefix(csv_file, common_prefix)
            name = remove_suffix(name, '.csv')
            if name not in ['bb', 'insn', 'global']:
                continue
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    json_dict[name].append(row)
        json.dump(json_dict, json_file, indent=2)
        json_file.write('\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert CSV files to a single JSON file.')
    parser.add_argument('csv_file', action='store', nargs='+', help='Input CSV files')
    args = parser.parse_args()
    csv_files = args.csv_file
    covert_csv_to_json(csv_files)
