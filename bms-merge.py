#!/usr/bin/env python3
from fractions import Fraction
from sys import argv, stderr
import math

PLAYABLE_CHANNELS = [16, 11, 12, 13, 14, 15,
                     18, 19, 56, 51, 52, 53, 54, 55, 58, 59]
HIDDEN_DIFF = 20
LN_DIFF = 40
BGM_START = 60


def lcm(a, b):
    return abs(a*b) // math.gcd(a, b)


def channel_rel_position(c):
    if c == 16:
        return 5
    if c >= BGM_START:
        return c - (BGM_START - 10)
    if c >= 50:
        return c - LN_DIFF
    if c >= 30:
        return 999999
    if c == 18:
        return 16
    if c == 19:
        return 17
    return c


def to_objects_array(data, length=-1):
    a = [data[i:i + 2] for i in range(0, len(data), 2)]
    if length == -1:
        return a
    objects = []
    for i in range(length):
        tmp = i * len(a)
        if tmp % length == 0:
            v = a[tmp // length]
            objects.append(v)
        else:
            objects.append('00')
    return objects


def shorten(data):
    a = to_objects_array(data, -1)
    length = 0
    for i, v in enumerate(a):
        if v == '00':
            continue
        f = Fraction(i, len(a))
        if f.denominator > length:
            length = f.denominator
    short = to_objects_array(data, length)
    return ''.join(short)


def retain_bms_headers(fp):
    lines = []
    with open(fp, encoding='shift-jis', errors='replace') as bms:
        for line in bms.readlines():
            line = line.strip()
            try:
                int(line[1:4]), int(line[4:6]), line[7:]
                return lines
            except:
                lines.append(line)
    return lines


def read_bms(fp):
    sc_map = {}
    data_channels = 0
    with open(fp, encoding='shift-jis', errors='replace') as bms:
        for line in bms.readlines():
            line = line.strip()
            try:
                section, channel, data = int(
                    line[1:4]), int(line[4:6]), line[7:]
                if section not in sc_map:
                    sc_map[section] = {}
                if channel == 1:
                    channel = BGM_START + data_channels
                    data_channels += 1
                else:
                    data_channels = 0
                sc_map[section][channel] = data
            except:
                pass
    """
    for s, channel_map in sc_map.items():
        print('Section', s, file=stderr)
        for c, data in channel_map.items():
            print(c, data, file=stderr)
        print(file=stderr)
    """
    return sc_map


def find_closest_channel(c, candidates):
    min_dist = 99999
    closest_channel = None
    for can in candidates:
        dist = abs(channel_rel_position(can) - channel_rel_position(c))
        if dist < min_dist:
            min_dist = dist
            closest_channel = can
    return closest_channel


def send_to_bgm(from_channel, t, channel_map):
    for apc in range(BGM_START, BGM_START + 33):
        if apc not in channel_map:
            channel_map[apc] = to_objects_array(
                '00', len(channel_map[from_channel]))
            print(f't={t} APC created!!! {apc}', file=stderr)
        if channel_map[apc][t] == '00':
            channel_map[apc][t] = channel_map[from_channel][t]
            channel_map[from_channel][t] = '00'
            print(
                f't={t} Moved {from_channel} to {apc} (autoplay)', file=stderr)
            break
    else:
        raise Exception('All APC used? WTF?')


if __name__ == '__main__':
    keysound, ks_less = read_bms(argv[1]), read_bms(argv[2])
    read_bms(argv[1])
    try:
        section_offset = int(argv[3])
    except:
        section_offset = 0

    for chart in [keysound, ks_less]:
        for s in range(len(chart)):
            if chart == ks_less:
                s += section_offset
            if s not in chart:
                chart[s] = {}
            channel_map = chart[s]
            for c, data in channel_map.items():
                chart[s][c] = shorten(data)

    for s in range(len(keysound)):
        channel_map = keysound[s]
        denominator = 1
        if s + section_offset not in ks_less:
            ks_less[s + section_offset] = {}
        note_channels = set(PLAYABLE_CHANNELS)
        note_channels |= set(channel_map.keys())
        note_channels |= set(ks_less[s + section_offset].keys())
        note_channels -= set([2])  # Some floating point channel?
        for c in note_channels:
            for chart in [keysound, ks_less]:
                sec = s + (section_offset if chart == ks_less else 0)
                if c not in chart[sec] or not chart[sec][c]:
                    chart[sec][c] = '00'
                data = chart[sec][c]
                interval = int(len(data) / 2)
                denominator = lcm(interval, denominator)
        print(f'Common denominator for #{s}: {denominator}', file=stderr)
        for c in note_channels:
            keysound[s][c] = to_objects_array(keysound[s][c], denominator)
            if c not in ks_less[s + section_offset]:
                ks_less[s + section_offset][c] = '00'
            ks_less[s + section_offset][c] = to_objects_array(
                ks_less[s + section_offset][c], denominator)
    for s in range(len(keysound)):
        channel_map = keysound[s]
        print('Section', s, file=stderr)
        intervals = len(channel_map[PLAYABLE_CHANNELS[0]])
        for t in range(intervals):
            altering = {'add': set(), 'move': set()}
            for c in PLAYABLE_CHANNELS:
                ks_note, ksl_note = channel_map[c][t], ks_less[s +
                                                               section_offset][c][t]
                if ks_note == '00' and ksl_note != '00':
                    altering['add'].add(c)
                elif ks_note != '00' and ksl_note == '00':
                    altering['move'].add(c)
            if altering['add'] or altering['move']:
                print(f't={t}', altering, file=stderr)
            for from_channel in altering['move']:
                # Move notes to the closest position that wants a note added
                to_channel = find_closest_channel(
                    from_channel, altering['add'])
                if to_channel:
                    assert channel_map[to_channel][t] == '00'
                    channel_map[to_channel][t] = channel_map[from_channel][t]
                    channel_map[from_channel][t] = '00'
                    altering['add'].remove(to_channel)
                    print(
                        f't={t} Moved {from_channel} to {to_channel}', file=stderr)
                else:
                    # Nowhere to move, move note to autoplay instead
                    send_to_bgm(from_channel, t, channel_map)
            for to_channel in altering['add']:
                # Look for a note from BGM
                candidates = list(filter(
                    lambda ch: ch >= BGM_START and channel_map[ch][t] != '00', channel_map.keys()))
                from_channel = find_closest_channel(to_channel, candidates)
                if from_channel:
                    channel_map[to_channel][t] = channel_map[from_channel][t]
                    channel_map[from_channel][t] = '00'
                    print(
                        f't={t} Moved c={from_channel} to c={to_channel}', file=stderr)
                else:
                    # Lookback sound search
                    sound = 'ZZ'
                    if to_channel + HIDDEN_DIFF in channel_map:
                        for st in range(t, 0, -1):
                            tmp_s = channel_map[to_channel + HIDDEN_DIFF][st]
                            if tmp_s != '00':
                                sound = tmp_s
                                break
                    channel_map[to_channel][t] = sound
                    print(
                        f't={t} Added sound={sound} to c={to_channel}', file=stderr)
    for s in range(len(keysound)):
        channel_map = keysound[s]
        intervals = len(channel_map[PLAYABLE_CHANNELS[0]])
        no_touch = set()
        for t in range(intervals):
            # Prefer LN over duplicated normal notes
            for c in filter(lambda c: c > 50, PLAYABLE_CHANNELS):
                if channel_map[c][t] != '00':
                    if c == 56:
                        # What the hell?
                        if (s, c, t) in no_touch:
                            continue
                        # BSS...
                        # Remove scratch and replace the start keysound
                        channel_map[c][t] = channel_map[c - LN_DIFF][t]
                        channel_map[c - LN_DIFF][t] = '00'
                        # ln end most go before scratch, wtf are these...
                        ns_channel_map = keysound[s + 1]
                        check_poses = (channel_map[c][intervals - 1],
                                       channel_map[c - LN_DIFF][intervals - 1],
                                       ns_channel_map[c - LN_DIFF][0],
                                       ns_channel_map[c][0]
                                       )
                        if check_poses[1] != '00':
                            channel_map[c][intervals - 1] = check_poses[1]
                            ns_channel_map[c - LN_DIFF][0] = check_poses[3]
                            print(f'BSS Fix s={s} c={c}',
                                  check_poses, file=stderr)
                            channel_map[c - LN_DIFF][intervals - 1] = '00'
                            ns_channel_map[c][0] = '00'
                            no_touch.add((s, c, intervals - 1))
                    else:
                        if channel_map[c - LN_DIFF][t] != '00':
                            send_to_bgm(c - LN_DIFF, t, channel_map)
                        # Forward search to ensure no normal notes come before LN end
                        ln_end = intervals
                        for ft in range(t + 1, intervals):
                            if channel_map[c][ft] != '00':
                                ln_end = ft
                                break
                        for st in range(t, ln_end):
                            if channel_map[c - LN_DIFF][st] != '00':
                                print(
                                    f'send_to_bgm {c - LN_DIFF} {st}', file=stderr)
                                send_to_bgm(c - LN_DIFF, st, channel_map)
    bms = retain_bms_headers(argv[1])
    for s, channel_map in keysound.items():
        for c, ar in channel_map.items():
            if c >= BGM_START:
                c = 1
            data = shorten(''.join(ar))
            if data:
                bms.append(f'#{s:03}{c:02}:{data}')
        bms.append('')
    print('\n'.join(bms))
