#!/usr/bin/env python3

import argparse, csv, os, json
from collections import defaultdict

def extract_items(csv_reader, to_dict, items):
    for row in csv_reader:
        name = row['name']
        for key, val in row.items():
            if key in items:
                to_dict[name][key] = val

def diff_csv(ref, exp, items, output):
    with open(ref, 'r') as ref_file, open(exp, 'r') as exp_file, open(output, 'w') as json_file:
        ref_reader = csv.DictReader(ref_file)
        exp_reader = csv.DictReader(exp_file)
        ref_dict = defaultdict(lambda:defaultdict(str))
        exp_dict = defaultdict(lambda:defaultdict(str))
        extract_items(ref_reader, ref_dict, items)
        extract_items(exp_reader, exp_dict, items)

        json_dict = defaultdict(lambda:defaultdict(lambda:defaultdict(str)))
        for name, _ in ref_dict.items():
            for key in _.keys():
                ref_val = ref_dict[name][key]
                exp_val = exp_dict[name][key]
                if exp_val != ref_val:
                    json_dict[name]['ref'][key] = ref_val
                    json_dict[name]['exp'][key] = exp_val

        json.dump(json_dict, json_file, indent=2)
        json_file.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Show difference between *.f.csv for interesting items')
    parser.add_argument('ref', help='reference *.f.csv')
    parser.add_argument('exp', help='experiment *.f.csv')
    parser.add_argument('--items', required=True, help='items to compare')
    parser.add_argument('-o', '--output', required=True, help='output json file')
    args = parser.parse_args()
    diff_csv(args.ref, args.exp, args.items.split(','), args.output)
