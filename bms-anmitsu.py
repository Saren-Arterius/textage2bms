#!/usr/bin/env python3
from math import floor
from os.path import splitext
import sys

process_channels = {11, 12, 13, 14, 15, 16,
                    18, 19, 21, 22, 23, 24, 25, 26, 28, 29}
ts_map = {}
sect_first_obj_map = {}
time_sig_mul = 1
extra_line = []
jacks = 0
nices = 0


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def do_anmitsu(line):
    global nices, jacks
    line = line.strip()
    if line.startswith('#TITLE'):
        return line + ' (Anmitsu)'
    try:
        p = int(line[1:6])
    except:
        return line
    channel = p % 100
    if channel not in process_channels:
        return line

    sec_ch, objs_str = line.split(':')
    objs = [objs_str[i * 2] + objs_str[(i * 2) + 1]
            for i in range(int(len(objs_str) / 2))]
    time_sig = ts_map[sec_ch[:4]] if sec_ch[:4] in ts_map else 1
    time_sig *= time_sig_mul
    max_objs = int(16 * time_sig)
    anmitsu_objs = ['00'] * max_objs

    if sect_first_obj_map[sec_ch] != objs[0]:
        eprint(
            sec_ch, f'Replaced 1st object from 00 to {sect_first_obj_map[sec_ch]}')
        anmitsu_objs[0] = sect_first_obj_map[sec_ch]

    def handle_defer():
        global extra_line
        ns_num = (p // 100) + 1
        nsch_str = f'#{ns_num:03}{channel:02}'
        if nsch_str not in sect_first_obj_map:
            eprint(sec_ch, rel_pos, obj, nearest, j,
                   n_j, 'Deferred to next empty section', nsch_str)
            extra_line.append(f';{nsch_str}:{obj}')
            return True
        if sect_first_obj_map[nsch_str] == '00':
            eprint(sec_ch, rel_pos, obj, nearest, j,
                   n_j, 'Deferred to next section', nsch_str)
            sect_first_obj_map[nsch_str] = obj
            return True
        eprint(sec_ch, rel_pos, obj, nearest, j,
               n_j, 'Could not defer to next section', nsch_str, sect_first_obj_map[nsch_str])
        return False

    for i, obj in enumerate(objs):
        if obj == '00':
            continue
        rel_pos = i / len(objs)
        miss = True
        for div, mul in [[8, 2], [16, 1]]:
            nearest = round((rel_pos / (1 / div)) * time_sig) * mul
            if mul == 1:
                transpose = [0, -1, 1] if nearest % 4 == 0 else [-1, 1, 0]
            else:
                transpose = [0]
            for j in transpose:
                n_j = nearest + j
                if n_j == max_objs:
                    if handle_defer():
                        miss = False
                        nices += 1
                        break
                # reduce jack
                if n_j >= 0 and n_j < max_objs and anmitsu_objs[n_j] == '00':
                    if len(transpose) > 1:
                        if n_j % 2 == 0:
                            msg = 'Nice'
                            nices += 1
                        else:
                            msg = 'Jack!'
                            jacks += 1
                        eprint(sec_ch, rel_pos, obj, nearest, j, n_j, msg)
                    anmitsu_objs[n_j] = obj
                    miss = False
                    break
            if not miss:
                break
        if miss:
            eprint(sec_ch, objs)
            eprint('A', anmitsu_objs)
            raise Exception('Miss note, try target higher BPM')
    el = ''
    if len(extra_line):
        el = extra_line.pop()
        eprint(el)
    return sec_ch + ':' + ''.join(anmitsu_objs) + el


def calc_ts_map(lines):
    for l in lines:
        if '02:' in l:
            tmp = l.split('02:')
            ts_map[tmp[0]] = float(tmp[1])


def calc_sect_first_obj_map(lines):
    for l in lines:
        try:
            p = int(l[1:6])
        except:
            continue
        channel = p % 100
        if channel not in process_channels:
            continue
        sect_first_obj_map[l[:6]] = l.split(':')[1][:2]


def calc_target_time_sig_mul(lines):
    bpm = None
    for l in lines:
        l = l.strip()
        if l.startswith('#BPM'):
            bpm = float(l.split(' ')[1])
            break
    try:
        tmp = float(sys.argv[2])
        if tmp > 10:
            return bpm, tmp / bpm
        return bpm, tmp
    except:
        return bpm, 1

if __name__ == "__main__":
    with open(sys.argv[1], encoding='shift-jis') as f:
        lines = f.readlines()
    calc_ts_map(lines)
    calc_sect_first_obj_map(lines)
    bpm, time_sig_mul = calc_target_time_sig_mul(lines)
    lines = [ll for l in map(do_anmitsu, lines) for ll in l.split(';')]
    new_fp = splitext(sys.argv[1])[0] + '.anmitsu.bme'
    with open(new_fp, 'w', encoding='shift-jis') as f:
        for l in lines:
            f.write(l + '\r\n')
    eprint()
    eprint(f'Target 8th notes BPM: {bpm * time_sig_mul} ({time_sig_mul})')
    if jacks + nices > 0:
        eprint(f'Jack ratio: {jacks}/{jacks + nices} = {jacks / (jacks + nices)}')
    else:
        eprint(f'No jack/nice')
