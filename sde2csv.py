#!/usr/bin/env python3
import re, argparse, csv, os, subprocess
from subprocess import PIPE
from collections import defaultdict

record_regex = re.compile(r'^\*?((?:\w|-)+)\s+([0-9]+)')
block_regex = re.compile(r'^BLOCK:\s+([0-9]+)\s+PC:\s+([0-9a-f]+)\s+ICOUNT:\s+([0-9]+)\s+EXECUTIONS:\s+([0-9]+)')
xdis_regex = re.compile(r'^XDIS\s+([0-9a-f]+):')
imag_addr_regex = re.compile(r'(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)')

ilen_sets = ['ilen-' + str(i) for i in range(1, 16)]
roi = ['total','mem-read', 'mem-write', 'category-COND_BR', 'category-UNCOND_BR'] + ilen_sets

# https://software.intel.com/sites/landingpage/pintool/docs/98484/Pin/html/index.html
# pin use its own rules to form a basic block and this is not aligned with the compiler basic block definition. As a result, pin basic block guarantee only one thing and it is that each basic block has a single entry, single exit and always execute together. e.g.
#
# switch(i) {
#   case 4: total++;
#   case 3: total++;
#   case 2: total++;
#   case 1: total++;
#   case 0:
#   default: break;
# }
#
# It will generate instructions something like this
#
# .L7:
#         addl    $1, -4(%ebp)
# .L6:
#         addl    $1, -4(%ebp)
# .L5:
#         addl    $1, -4(%ebp)
# .L4:
#         addl    $1, -4(%ebp)
#
# In terms of classical basic blocks, each addl instruction is in a single instruction basic block. However as the different switch cases are executed, Pin will generate BBLs which contain all four instructions (when the .L7 case is entered), three instructions (when the .L6 case is entered), and so on. This means that counting Pin BBLs is unlikely to give the count you would expect if you thought that Pin BBLs were the same as the basic blocks in the text book. Here, for instance, if the code branches to .L7 you will count one Pin BBL, but there are four classical basic blocks executed.
#
# Hence an IP might be in more than one block, you need to add their execution count for the total execution of one IP.

def collect_metrics(metrics, matches):
    if matches and matches.group(1) in roi:
        key = matches.group(1)
        val = int(matches.group(2))
        metrics[key] = val

def update_bb_insn_info(line, metrics, icounts, image_addr_low, image_addr_high, image_first_load_addr, bb_writer):
    if matches := block_regex.match(line):
        if metrics:
            bb_writer.writerow(metrics)
            metrics.clear() # clear metrics for next bb
        entry = int(matches.group(2), 16)
        if entry < image_addr_low or entry > image_addr_high: # only collect interested data
            return
        metrics['entry'] = '{:x}'.format(entry - image_addr_low + image_first_load_addr)
        metrics['execution'] = int(matches.group(4))
    elif matches := xdis_regex.match(line):
        if 'entry' not in metrics:
            return
        addr = int(matches.group(1), 16)
        assert addr >= image_addr_low or addr <= image_addr_high, 'entry should be None'
        addr = addr - image_addr_low + image_first_load_addr
        icounts[f'{addr:x}'] += metrics['execution']
        metrics['exit'] = f'{addr:x}'
    elif matches := record_regex.match(line):
        if 'entry' not in metrics:
            return
        collect_metrics(metrics, matches)

def update_global_info(line, metrics):
    if matches := record_regex.match(line):
        collect_metrics(metrics, matches)

def get_image_first_load_addr(binary):
    pg_header = subprocess.run(['readelf', '-l', binary], stdout=PIPE, check=True)
    # Assume the program headers looks like:
    #
    # Program Headers:
    #   Type           Offset             VirtAddr           PhysAddr
    #                  FileSiz            MemSiz              Flags  Align
    #   PHDR           0x0000000000000040 0x0000000000400040 0x0000000000400040
    #                  0x00000000000002d8 0x00000000000002d8  R      0x8
    #   INTERP         0x0000000000000318 0x0000000000400318 0x0000000000400318
    #                  0x000000000000001c 0x000000000000001c  R      0x1
    #   LOAD           0x0000000000000000 0x0000000000400000 0x0000000000400000
    #                  0x0000000000000660 0x0000000000000660  R      0x1000
    #   LOAD           0x0000000000001000 0x0000000000401000 0x0000000000401000
    #                  0x0000000000000215 0x0000000000000215  R E    0x1000
    pg_header = pg_header.stdout.decode('utf-8').strip()
    for line in pg_header.splitlines():
        if 'LOAD' in line:
            return int(line.strip().split()[2], 16)

def convert_sde_prof_to_csv(sde_file, binary):
    bb_header = ['entry', 'execution', 'exit'] + roi
    insn_header = ['pc', 'execution']
    global_header = roi

    with open(sde_file, 'r') as prof, open(sde_file+'.bb.csv', 'w') as bb_csv, open(sde_file+'.insn.csv', 'w') as insn_csv, open(sde_file+'.global.csv', 'w') as global_csv:
        bb_writer = csv.DictWriter(bb_csv, fieldnames=bb_header)
        insn_writer = csv.DictWriter(insn_csv, fieldnames=insn_header)
        global_writer = csv.DictWriter(global_csv, fieldnames=global_header)

        metrics = defaultdict(int)
        icounts = defaultdict(int)
        find_image_addr_beg = find_image_addr_end = find_global_count_beg = find_global_count_end = find_top_block_beg = find_top_block_end = None
        image_addr_low = image_addr_high = None
        image_first_load_addr = get_image_first_load_addr(os.path.abspath(binary))
        assert image_first_load_addr, 'not found first load address of image'

        for line in prof:
            if 'EMIT_IMAGE_ADDRESSES' in line:
                find_image_addr_beg = True
            elif 'END_IMAGE_ADDRESSES' in line:
                find_image_addr_end = True
            elif 'EMIT_TOP_BLOCK_STATS' in line:
                assert image_addr_low, 'not found low addr of image'
                assert image_addr_high, 'not found high addr of image'
                find_top_block_beg = True
                bb_writer.writeheader() # row is written when a new bb is found
            elif 'END_TOP_BLOCK_STATS' in line and not find_top_block_end: # SDE emits this twice, one for thread, one for global
                find_top_block_end = True
                assert find_top_block_beg, 'not found top block begin yet'
                insn_writer.writeheader()
                for key, val in icounts.items():
                    row = dict(zip(insn_header, [key, val]))
                    insn_writer.writerow(row)
            elif "global-dynamic-counts" in line:
                find_global_count_beg = True
                assert find_top_block_end, 'not found top block end yet'
                global_writer.writeheader()
                metrics.clear()
            elif "END_GLOBAL_DYNAMIC_STATS" in line:
                find_global_count_end = True
                assert find_global_count_beg, 'not found global count begin yet'
                global_writer.writerow(metrics)

            if find_image_addr_beg and not find_image_addr_end:
                if match := imag_addr_regex.match(line):
                    if os.path.basename(binary) in match.group(1):
                        image_addr_low = int(match.group(2), 16)
                        image_addr_high = int(match.group(3), 16)
            elif find_top_block_beg and not find_top_block_end:
                update_bb_insn_info(line, metrics, icounts, image_addr_low, image_addr_high, image_first_load_addr, bb_writer)
            elif find_global_count_beg and not find_global_count_end:
                update_global_info(line, metrics)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert profile data from SDE format to CSV format (only supports single-threaded programs currently).')
    parser.add_argument('sde_file', action='store', help='Input SDE file')
    parser.add_argument('binary', action='store', help='Interesting binary')
    parser.add_argument('--items', type=str, help='Extra interesting items in profile data')
    args = parser.parse_args()
    items = [s.strip() for s in args.items.split(',')] if args.items else None
    if items:
        roi += items
    convert_sde_prof_to_csv(args.sde_file, args.binary)
