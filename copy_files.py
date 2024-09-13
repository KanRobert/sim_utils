#!/usr/bin/env python3
import os, argparse, csv, shutil

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Copy files by the CSV output of a collector, where name, exe, sim_files are required')
    parser.add_argument('dst', help='destination directory')
    parser.add_argument('--csv', required=True, help='input CSV file describing the mappings')
    parser.add_argument('-o', '--output', required=True, help='simplified CSV file by removing the dir name of files')
    args = parser.parse_args()

    with open(args.csv, 'r') as csv_file, open(args.output, 'w') as output_file:
        csv_reader = csv.DictReader(csv_file)
        csv_writer = csv.DictWriter(output_file, fieldnames=['name', 'exe', 'sim_files'])
        csv_writer.writeheader()
        exe_from_to = {}
        for row in csv_reader:
            name = row['name']
            exe = row['exe']
            sim_files = row['sim_files'].split(',')

            new_row = {}
            new_row['name'] = name
            new_row['exe'] = os.path.basename(exe)
            new_row['sim_files'] = ','.join([os.path.basename(sim_file) for sim_file in sim_files])

            sub_dir = os.path.join(args.dst, name)
            if os.path.isdir(sub_dir):
                 shutil.rmtree(sub_dir)
            os.mkdir(sub_dir)
            to_exe = os.path.join(sub_dir, os.path.basename(exe))
            # Avoid duplicated copies
            if exe in exe_from_to:
                os.link(exe_from_to[exe], to_exe)
            else:
                shutil.copyfile(exe, to_exe)
                exe_from_to[exe] = to_exe

            for sim_file in sim_files:
                shutil.copy(sim_file, sub_dir)

            csv_writer.writerow(new_row)
