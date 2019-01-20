#!/usr/bin/env python3
from tja_info import *
from sys import argv, stderr

if __name__ == '__main__':
    info = None
    parse_level = 3

    try:
        parse_level = TJAInfo.parse_course(argv[2])
    except:
        pass

    for codec in ['utf-8', 'shift-jis', 'gbk']:
        try:
            with open(argv[1], encoding='gbk') as d:
                info = TJAInfo(d.read())
                break
        except:
            pass

    if not info:
        print('Could not parse', argv[1], file=stderr)
        exit(1)
    print(f'Parse level {parse_level} of {argv[1]}', file=stderr)
    headers = {
        '#PLAYER': '1',
        '#RANK': '3',
        '#DIFFICULTY': '4',
        '#STAGEFILE': '',
        '#GENRE': info.headers['SUBTITLE'],
        '#TITLE': '[TJA] ' + info.headers['TITLE'],
        '#ARTIST': 'TJA',
        '#BPM': info.headers['BPM'],
        '#PLAYLEVEL': info.headers['LEVELS'][3],
        '#WAV02': 'out.wav',
        '#WAVDD': 'dong.wav',
        '#WAVCC': 'ka.wav',
    }
    print('*---------------------- HEADER FIELD')
    for k, v in headers.items():
        print(k, v)
    print('\n*---------------------- MAIN DATA FIELD\n#00001:02\n')
    section_seconds = 4 * (60 / float(info.headers['BPM']))
    measure_seconds = section_seconds / 192
    stop_count = round(-float(info.headers['OFFSET']) / measure_seconds) - (2 * 192)
    print(f'#STOP01 {stop_count}')
    print(f'#00009:01')
    
    small_notes_counter = 0
    for s_num, s in enumerate(info.beatmaps[parse_level]):
        s_num = s_num + 2
        notes = tuple(filter(lambda o: isinstance(o, NoteTypes), s))
        rr_notes = ['00'] * len(notes)
        rl_notes = ['00'] * len(notes)
        br_notes = ['00'] * len(notes)
        bl_notes = ['00'] * len(notes)
        
        for t, n in enumerate(notes):
            if n == NoteTypes.BIG_RED:
                rr_notes[t], rl_notes[t] = 'DD', 'DD'
            elif n == NoteTypes.BIG_BLUE:
                br_notes[t], bl_notes[t] = 'CC', 'CC'
            else:
                sel_notes = None
                if n == NoteTypes.RED:
                    sel_notes = rr_notes if small_notes_counter % 2 == 0 else rl_notes
                elif n == NoteTypes.BLUE:
                    sel_notes = br_notes if small_notes_counter % 2 == 0 else bl_notes
                else:
                    continue
                sel_notes[t] = 'DD' if n == NoteTypes.RED else 'CC'
                small_notes_counter += 1
        m = {12: bl_notes, 13: rl_notes, 15: rr_notes, 18: br_notes}
        # print(m)
        for channel, ch_notes in m.items():
            if not len(ch_notes) or all(map(lambda n: n == '00', ch_notes)):
                continue
            print('#{:03d}{}:{}'.format(s_num, channel, ''.join(ch_notes)))
        # print(s_num, notes, file=stderr)

    current_measure = 1
    bpm_change_counter = 1
    for s_num, s in enumerate(info.beatmaps[parse_level]):
        s_num = s_num + 2
        non_notes = tuple(filter(lambda o: not isinstance(o, NoteTypes), s))
        measures = tuple(filter(lambda o: isinstance(o, Measure), non_notes))
        if len(measures):
            current_measure = measures[0].value.numerator / measures[0].value.denominator
        if current_measure != 1:
            print('#{:03d}02:{}'.format(s_num, current_measure))

        bpm_changes = tuple(filter(lambda o: isinstance(o, BPMChange), non_notes))
        bpm_channel_notes = []
        for c in bpm_changes:
            print('#BPM{:02d}:{}'.format(bpm_change_counter, c.new_bpm))
            bpm_channel_notes.append('{:02d}'.format(bpm_change_counter))
            bpm_change_counter += 1
        if bpm_channel_notes:
            print('#{:03d}08:{}'.format(s_num, ''.join(bpm_channel_notes)))
