#!/usr/bin/env python3

import argparse, csv, os, json, tempfile, subprocess

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Show difference between all *.f.csv for interesting items')
    parser.add_argument('ref', help='reference directory')
    parser.add_argument('exp', help='experiment directory')
    parser.add_argument('--ref_csv', required=True, help='csv file to describe the mappings for ref')
    parser.add_argument('--exp_csv', required=True, help='csv file to describe the mappings for exp')
    parser.add_argument('--items', required=True, help='items to compare')
    parser.add_argument('-o', '--output', required=True, help='output json file')
    args = parser.parse_args()

    repo = os.path.dirname(os.path.realpath(__file__))
    out_dict = {}
    with open(args.ref_csv, 'r') as ref_csv_file, open(args.exp_csv, 'r') as exp_csv_file:
        ref_reader = csv.DictReader(ref_csv_file)
        exp_reader = csv.DictReader(exp_csv_file)
        for ref_row, exp_row in zip(ref_reader, exp_reader):
            name = ref_row['name']
            assert name == exp_row['name'], 'name mismatch'
            ref_sim_files = ref_row['sim_files'].split(',')
            exp_sim_files = exp_row['sim_files'].split(',')
            assert len(ref_sim_files) == len(exp_sim_files), 'sim_files mismatch'
            for ref_sim_file, exp_sim_file in zip(ref_sim_files, exp_sim_files):
                ref_f_file_path = os.path.join(args.ref, name, f'{ref_sim_file}.f.csv')
                exp_f_file_path = os.path.join(args.exp, name, f'{exp_sim_file}.f.csv')
                tmp = tempfile.NamedTemporaryFile(delete=False)
                subprocess.run([os.path.join(repo, 'diff_csv_for_f.py'), ref_f_file_path, exp_f_file_path, f'--items={args.items}', '-o', tmp.name], check=True)
                with open(tmp.name, 'r') as tmp_file:
                    json_dict = json.load(tmp_file)
                    workload_name = name if len(ref_sim_files) == 1 else '{}.{}'.format(name, ref_sim_file.split('.')[0])
                    out_dict[workload_name] = json_dict
                os.unlink(tmp.name)

    with open(args.output, 'w') as out_file:
        json.dump(out_dict, out_file, indent=2)
        out_file.write('\n')
