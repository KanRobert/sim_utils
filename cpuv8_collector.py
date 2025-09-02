#!/usr/bin/env python3
import os, argparse, glob, csv, sys, re, subprocess
from collections import defaultdict

# Extract from inrate/fprate/intspeed/fpspeed.bset in cpu2017/benchspec/CPU
# class field is for future usage
workload_class='''\
workload,class

706.stockfish_r,int_rate 
707.ntest_r,int_rate     
708.sqlite_r,int_rate    
710.omnetpp_r,int_rate   
714.cpython_r,int_rate   
721.gcc_r,int_rate       
723.llvm_r,int_rate      
727.cppcheck_r,int_rate  
729.abc_r,int_rate       
734.vpr_r,int_rate       
735.gem5_r,int_rate      
750.sealcrypto_r,int_rate
753.ns3_r,int_rate       
760.rocksdb_r,int_rate   
777.zstd_r,int_rate    

709.cactus_r,fp_rate  
722.palm_r,fp_rate    
731.astcenc_r,fp_rate 
736.ocio_r,fp_rate    
737.gmsh_r,fp_rate    
748.flightdm_r,fp_rate
749.fotonik3d_r"
752.whisper_r,fp_rate 
765.roms_r,fp_rate    
766.femflow_r,fp_rate 
767.nest_r,fp_rate    
772.marian_r,fp_rate  
782.lbm_r,fp_rate  

801.xz_s,int_speed      
807.ntest_s,int_speed   
817.flac_s,int_speed    
821.gcc_s,int_speed     
823.llvm_s,int_speed    
827.cppcheck_s,int_speed
829.abc_s,int_speed     
834.vpr_s,int_speed     
835.gem5_s,int_speed    
838.diamond_s,int_speed 
846.minizinc_s,int_speed
853.ns3_s,int_speed     
854.graph500_s,int_speed 

800.pot3d_s,fp_speed     
803.sph_exa_s,fp_speed   
809.cactus_s,fp_speed    
811.tealeaf_s,fp_speed   
816.nab_s,fp_speed       
820.cloverleaf_s,fp_speed
822.palm_s,fp_speed      
849.fotonik3d_s,fp_speed 
852.whisper_s,fp_speed   
857.namd_s,fp_speed      
865.roms_s,fp_speed      
867.nest_s,fp_speed      
872.marian_s,fp_speed    
881.neutron_s,fp_speed 
'''

reader = csv.DictReader(workload_class.split('\n'))
workloads_classes = {}
for line in reader:
    workloads_classes[line['workload']] = line['class']

all_workloads = workloads_classes.keys()
wl_error_state = {}

def get_workload_status(workload, log_dir, label):
    label_filter = f"Label.*=.*{label}"
    filter_grep = f'grep -r --include="*.log" {label_filter} {log_dir}'
    filter_res=subprocess.run(filter_grep, shell=True, capture_output=True, text=True)
    filenames_str = None
    if filter_res.stderr:
        print(filter_res.stderr)
        return None
    if filter_res.stdout:
        filenames = [line.split(':')[0] for line in filter_res.stdout.splitlines()]
        filenames_str = ' '.join(filenames)

    command = f'echo {filenames_str} | xargs grep -r --include="*.log" "Error.*"'
    res=subprocess.run(command, shell=True, capture_output=True, text=True)

    if res.stderr:
        print(res.stderr)
        return None

    if res.stdout:
        bench_pattern = '[78]\d{2}\.[a-zA-Z0-9]+_[rs]' 
        BE_reg = f'Error building.*({bench_pattern})'
        SE_reg = f'Error during.*setup for({bench_pattern})'
        RE_reg = f'Error ({bench_pattern}).*errorcode=RE'
        VE_reg = f'Error ({bench_pattern}).*errorcode=VE'

        BE_benches = {match for match in re.findall(BE_reg, res.stdout)}
        BE_benches = list(BE_benches)
        SE_benches = {match for match in re.findall(SE_reg, res.stdout)}
        SE_benches = list(SE_benches)
        RE_benches = {match for match in re.findall(RE_reg, res.stdout)}
        RE_benches = list(RE_benches)
        VE_benches = {match for match in re.findall(VE_reg, res.stdout)}
        VE_benches = list(VE_benches)

        for b in BE_benches:
            wl_error_state[b] = 'BE (build error)'
        for b in SE_benches:
            wl_error_state[b] = 'SE (setup error)'
        for b in RE_benches:
            wl_error_state[b] = 'RE (runtime error)'
        for b in VE_benches:
            wl_error_state[b] = 'VE (validation error)'

        if workload in wl_error_state.keys():
            return wl_error_state[workload]

    return 'Success'

def get_path(directory, size, label, num, classes, workloads):
    cpu_dir = os.path.join(directory, 'benchspec/CPU')
    run_dir = f'run_base_{size}_{label}.{num}'
    log_dir = f'{directory}/result'
    speccmds_pattern = f'run/{run_dir}/speccmds.cmd'
    csv_dict_list = list(defaultdict(str))

    if not os.path.exists(log_dir):
        print(f'Error: cannot find last run result for {label}', file=sys.stderr)
        return None

    for workload in workloads:
        assert workload in all_workloads, f'unsupport workload {workload}'
        
        workload_dict = defaultdict(str)
        workload_dict['name'] = workload
	
        wl_state = get_workload_status(workload, log_dir, label)
        workload_dict['status'] = wl_state
        if classes:
            workload_dict['class'] = workloads_classes[workload]
        if not wl_state:
            print(f'warning: error searching run logs for {workload} {label}')
        elif wl_state != 'Success':
            print(f'warning: benchmark {workload} {label} failed: {wl_state}',
            file=sys.stderr)
            csv_dict_list.append(workload_dict)
            continue
        speccmds_path = os.path.join(cpu_dir, workload + '*', speccmds_pattern)
        speccmds_files = glob.glob(speccmds_path)
        if not speccmds_files:
            print(f'warning: cannot find speccmds.cmd for {workload} with input:{size}, label:{label}', file=sys.stderr)
            continue
        speccmds_abspath = os.path.abspath(speccmds_files[0])
        directory = os.path.dirname(speccmds_abspath)

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
    parser.add_argument('--classes', action='store_true', help='add class info: int_rate, fp_rate, int_speed, fp_speed')
    parser.add_argument('-o', '--output', required=True, help='output CSV for the paths')
    args = parser.parse_args()

    workloads = args.workloads.split(',') if args.workloads else all_workloads
    if args.filter == 'speed':
        workloads = [workload for workload in workloads if workload.endswith('_s')]
    elif args.filter == 'rate':
        workloads = [workload for workload in workloads if workload.endswith('_r')]

    csv_dict_list = get_path(args.dir, args.size, args.label, args.num, args.classes, workloads)
    if csv_dict_list:
        with open(args.output, 'w') as csv_file:
            header = csv_dict_list[0].keys()
            csv_writer = csv.DictWriter(csv_file, fieldnames=header)
            csv_writer.writeheader()
            for row in csv_dict_list:
                csv_writer.writerow(row)