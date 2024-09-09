#!/usr/bin/env python3
import argparse, csv, os, subprocess, glob
from subprocess import PIPE


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Combine *.global.csv for all workloads')
    parser.add_argument('dir', help='directory of the inputs')
    parser.add_argument('--csv', required=True, help='csv file to describe the mappings')
    parser.add_argument('-o', '--output', required=True, help='output file')

    args = parser.parse_args()

    with open(args.csv, 'r') as csv_file, open(args.output, 'w') as out_file:
        reader = csv.DictReader(csv_file)
        writer = None
        dir_path = args.dir
        for row in reader:
            name = row['name']
            sim_file_names = row['sim_files'].split(',')
            sub_dir = os.path.join(dir_path, name)
            for sim_file_name in sim_file_names:
                sim_file_abspath = os.path.join(sub_dir, sim_file_name)
                global_csv_file_abspath = f'{sim_file_abspath}.global.csv'
                with open(global_csv_file_abspath, 'r') as global_csv_file:
                    global_csv_file_reader = csv.DictReader(global_csv_file)
                    if not writer:
                        header = ['name'] + global_csv_file_reader.fieldnames
                        writer = csv.DictWriter(out_file, fieldnames = header)
                        writer.writeheader()

                    global_data_dict = next(global_csv_file_reader)
                    workload_name = name if len(sim_file_names) == 1 else '{}.{}'.format(name, sim_file_name.split('.')[0])
                    global_data_dict = {'name': workload_name} | global_data_dict
                    writer.writerow(global_data_dict)


