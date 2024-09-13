#!/usr/bin/env python3
import os, argparse, glob, csv, sys, re
from collections import defaultdict

# Extract from inrate/fprate/intspeed/fpspeed.bset in cpu2017/benchspec/CPU
# class field is for future usage
workload_class='''\
workload,class
500.perlbench_r,int_rate
502.gcc_r,int_rate
505.mcf_r,int_rate
520.omnetpp_r,int_rate
523.xalancbmk_r,int_rate
525.x264_r,int_rate
531.deepsjeng_r,int_rate
541.leela_r,int_rate
548.exchange2_r,int_rate
557.xz_r,int_rate

503.bwaves_r,fp_rate
507.cactuBSSN_r,fp_rate
508.namd_r,fp_rate
510.parest_r,fp_rate
511.povray_r,fp_rate
519.lbm_r,fp_rate
521.wrf_r,fp_rate
526.blender_r,fp_rate
527.cam4_r,fp_rate
538.imagick_r,fp_rate
544.nab_r,fp_rate
549.fotonik3d_r,fp_rate
554.roms_r,fp_rate

600.perlbench_s,int_speed
602.gcc_s,int_speed
605.mcf_s,int_speed
620.omnetpp_s,int_speed
623.xalancbmk_s,int_speed
625.x264_s,int_speed
631.deepsjeng_s,int_speed
641.leela_s,int_speed
648.exchange2_s,int_speed
657.xz_s,int_speed

603.bwaves_s,fp_speed
607.cactuBSSN_s,fp_speed
619.lbm_s,fp_speed
621.wrf_s,fp_speed
627.cam4_s,fp_speed
628.pop2_s,fp_speed
638.imagick_s,fp_speed
644.nab_s,fp_speed
649.fotonik3d_s,fp_speed
654.roms_s,fp_speed
'''

reader = csv.DictReader(workload_class.split('\n'))
workloads_classes = {}
for line in reader:
    workloads_classes[line['workload']] = line['class']

all_workloads = workloads_classes.keys()

def get_path(directory, size, label, num, workloads):
    cpu_dir = os.path.join(directory, 'benchspec/CPU')
    run_dir = f'run_base_{size}_{label}.{num}'
    speccmds_pattern = f'run/{run_dir}/speccmds.cmd'
    csv_dict_list = list(defaultdict(str))

    for workload in workloads:
        assert workload in all_workloads, f'unsupport workload {workload}'
        speccmds_path = os.path.join(cpu_dir, workload + '*', speccmds_pattern)
        speccmds_files = glob.glob(speccmds_path)
        if not speccmds_files:
            print(f'warning: cannot find speccmds.cmd for {workload} with input:{size}, label:{label}', file=sys.stderr)
            continue
        speccmds_abspath = os.path.abspath(speccmds_files[0])
        directory = os.path.dirname(speccmds_abspath)

        workload_dict = defaultdict(str)
        workload_dict['name'] = workload
        with open(speccmds_abspath, 'r') as speccmds_file:
            exe = None
            err_files = []
            # Assume SDE profiling data is writtern to stderr files.
            file_regex = re.compile(r'.*\s-e\s([\w\.-]+)\s.*'+ run_dir + r'/([\w\.-]+)')
            for line in speccmds_file:
                if matches := file_regex.match(line):
                    new_exe = os.path.basename(matches.group(2))
                    if exe:
                        assert new_exe == exe, 'more than 1 exe'
                    else:
                        exe = new_exe
                    err_files.append(os.path.join(directory, os.path.basename(matches.group(1))))

            assert exe, 'not found exe'
            assert err_files, 'not found err files'
            workload_dict['exe'] = os.path.join(directory, exe)
            workload_dict['sim_files'] = ','.join(err_files)

        csv_dict_list.append(workload_dict)

    return csv_dict_list

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get paths of binaries and SDE perf data for cpu2017 (version 1.1.8), assuming perf data is written to stderr, e.g. for sde, "-omix /dev/stderr -top_blocks -1 -dynamic_stats_per_block" is used in the submit')
    parser.add_argument('dir', help='directory of cpu2017')
    parser.add_argument('--size', choices=['test', 'train', 'ref'])
    parser.add_argument('--label', required=True, help='label used in cpu2017 config file')
    parser.add_argument('--num', default='0000', help='run number')
    parser.add_argument('--workloads', help='intersting workloads, which can be a subset {}'.format(','.join(all_workloads)))
    parser.add_argument('--filter', choices=['speed', 'rate'])
    parser.add_argument('-o', '--output', required=True, help='output CSV for the paths')
    args = parser.parse_args()

    workloads = args.workloads.split(',') if args.workloads else all_workloads
    if args.filter == 'speed':
        workloads = [workload for workload in workloads if workload.endswith('_s')]
    elif args.filter == 'rate':
        workloads = [workload for workload in workloads if workload.endswith('_r')]

    csv_dict_list = get_path(args.dir, args.size, args.label, args.num, workloads)
    with open(args.output, 'w') as csv_file:
        header = ['name', 'exe', 'sim_files']
        csv_writer = csv.DictWriter(csv_file, fieldnames=header)
        csv_writer.writeheader()
        for row in csv_dict_list:
            csv_writer.writerow(row)
