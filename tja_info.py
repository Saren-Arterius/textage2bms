#!/usr/bin/python3
from multiprocessing.pool import Pool
from fractions import Fraction, gcd
from binascii import crc32
from os.path import dirname, join, abspath
from enum import Enum
from re import findall, sub
from os import makedirs, listdir, name as osname

from math import floor


class TJAInfo(object):
    working_dir = dirname(abspath(__file__))
    executables_path = "executables"
    temp_path = "tmp"
    fonts_path = "fonts"
    donscore_helper_py = "get_donscore_png.py"
    font = "LiHei ProPC.ttf"

    def __init__(self, tja):
        self.tja = tja
        self.renda_hits_per_second = 18
        self.compress = False
        self.headers = self.__parse_headers()
        self.beatmaps = self.__parse_beatmaps()
        self.simulate_results = self.__simulate_play()
        self.headers["bpm_display"] = self.__get_bpm_display()

    def get_all_donscores(self):
        with Pool(processes = 5) as pool:
            return pool.map(self.get_donscore_png, range(0, 5))

    def get_donscore_png(self, course):
        if self.headers["LEVELS"][course] is None:
            return
        if self.simulate_results[course]["max_combo"] > 50000:
            raise Exception("Beatmap too long")
        from subprocess import call
        from shutil import copyfile, rmtree
        from PIL import Image, ImageFont, ImageDraw
        from io import BytesIO

        temp_working_dir = abspath(join(TJAInfo.working_dir, TJAInfo.temp_path,
                                        "{0}-{1}".format(str(crc32(self.headers["TITLE"].encode())), course)))
        temp_tja_path = abspath(join(temp_working_dir, "{0}.tja".format(course)))
        tools_path = abspath(join(TJAInfo.working_dir, TJAInfo.executables_path))

        try:
            makedirs(temp_working_dir)
        except FileExistsError:
            pass

        with open(temp_tja_path, "w+", errors = "ignore") as tmp_tja_file:
            temp_tja = self.get_specific_course_tja(course)
            tmp_tja_file.write(temp_tja)

        for file in listdir(tools_path):
            if osname == "nt":
                copyfile(join(tools_path, file), join(temp_working_dir, file))
            else:
                call(["ln", "-s", join(tools_path, file), join(temp_working_dir, file)])
        try:
            call(["python3", join(TJAInfo.working_dir, TJAInfo.donscore_helper_py), temp_working_dir, temp_tja_path])
        except FileNotFoundError:
            call(["python", join(TJAInfo.working_dir, TJAInfo.donscore_helper_py), temp_working_dir, temp_tja_path])

        donscore = Image.open(join(temp_working_dir, "convert.png"))

        try:
            rmtree(temp_working_dir)
        except IOError:
            pass

        for x in range(816):
            for y in range(60):
                donscore.putpixel((x, y), (204, 204, 204))
        draw = ImageDraw.Draw(donscore)
        title_font = ImageFont.truetype(join(TJAInfo.working_dir, TJAInfo.fonts_path, TJAInfo.font), 20)
        details_font = ImageFont.truetype(join(TJAInfo.working_dir, TJAInfo.fonts_path, TJAInfo.font), 18)
        draw.text((12, 9), self.headers["TITLE"], (0, 0, 0), font = title_font)
        draw.text((12, 37), self.__get_donscore_details_text(course), (0, 0, 0), font = details_font)

        buffer = BytesIO()
        donscore.save(buffer, "png")
        buffer.seek(0)

        return buffer

    def get_specific_course_tja(self, course):
        if self.headers["LEVELS"][course] is None:
            return None
        tja = ""
        for key, val in self.headers.items():
            if isinstance(val, list) or key[0].islower() or key.startswith("SUB"):
                continue
            tja += "{0}:{1}\n".format(key, val)
        tja += "COURSE:{0}\n".format(course)
        tja += "LEVEL:{0}\n".format(self.headers["LEVELS"][course])
        tja += "BALLOON:{0}\n".format(",".join([str(c) for c in self.headers["BALLOONS"][course]]))
        tja += "#START\n"
        for section in self.beatmaps[course]:
            if len(section) == 0:
                tja += str(NoteTypes.NONE.value)
            for note in section:
                if isinstance(note, NoteTypes):
                    tja += str(note.value)
                else:
                    tja += str(note)
            tja += ",\n"
        tja += "\n#END"
        tja = sub("\n+", "\n", tja)
        return tja

    def get_beautiful_tja(self):
        tja = ""
        head_keys = ["TITLE", "SUBTITLE", "WAVE", "BPM", "OFFSET"]

        for key in head_keys:
            if key in self.headers:
                tja += "{0}:{1}\n".format(key, self.headers[key])
        for key, val in self.headers.items():
            if isinstance(val, list) or key[0].islower() or key in head_keys:
                continue
            tja += "{0}:{1}\n".format(key, val)

        tja += "\n"

        for course, level in enumerate(self.headers["LEVELS"]):
            if level is None:
                continue
            tja += "COURSE:{0}\n".format(course)
            tja += "LEVEL:{0}\n".format(level)
            tja += "BALLOON:{0}\n".format(",".join([str(c) for c in self.headers["BALLOONS"][course]]))
            tja += "#START\n"
            current_measure = 1
            cut_interval = 16
            for section in self.beatmaps[course]:
                if self.compress:
                    section = TJAInfo.compress_section(section)
                pos = 0
                if len(section) == 0:
                    tja += str(NoteTypes.NONE.value)
                else:
                    note_len = 0
                    for note in section:
                        if isinstance(note, NoteTypes):
                            note_len += 1
                        elif isinstance(note, Measure):
                            current_measure = note.value
                    if note_len % int(16 * current_measure / 4 * 3) == 0:
                        cut_interval = 16 * current_measure / 4 * 3
                    else:
                        cut_interval = 16 * current_measure
                for index, note in enumerate(section):
                    if isinstance(note, NoteTypes):
                        tja += str(note.value)
                        pos += 1
                        if pos and pos % cut_interval == 0 and index + 1 != len(section):
                            tja += "\n"
                    else:
                        tja += str(note)
                tja += ",\n"
            tja += "\n#END\n"
        return tja

    def __get_donscore_details_text(self, course):
        course_text = ["かんたん", "ふつう", "むずかしい", "おに", "裏おに"]
        course_max_level = [5, 7, 8, 10, 12]
        level_star = "★"
        empty_star = "☆"
        course_level = (course, self.headers["LEVELS"][course])
        if self.headers["LEVELS"][course] in range(13):
            stars_text = level_star * course_level[1] if course_level[1] < course_max_level[
                course_level[0]] else level_star * course_max_level[course_level[0]]
            stars_text += empty_star * (course_max_level[course_level[0]] - course_level[1])
        else:
            stars_text = "{0} x {1}".format(level_star, self.headers["LEVELS"][course])
        return "{0} {1}".format(course_text[course_level[0]], stars_text)

    def __parse_headers(self):
        headers = {}
        for line in self.tja.splitlines():
            if not len(line):
                continue
            if not len(findall("[A-Z]", line[0])):
                continue
            keyval = findall("([A-Z]+):(.*)", line)[0]
            attr = TJAInfo.parse_attribute(keyval[0], keyval[1])
            if attr is not None:
                headers[keyval[0]] = attr
        return dict(list(headers.items()) + list(self.__parse_level_headers().items()) + list(
            self.__parse_balloon_headers().items()))

    def __parse_level_headers(self):
        levels = [None] * 5
        parse_course = None
        parse_level = None
        for line in self.tja.splitlines():
            if not len(line):
                continue
            if not len(findall("[A-Z]", line[0])):
                continue
            keyval = findall("([A-Z]+):(.*)", line)[0]
            if keyval[0] == "COURSE":
                parse_course = TJAInfo.parse_course(keyval[1])
            elif keyval[0] == "LEVEL":
                try:
                    parse_level = 1 if int(keyval[1]) < 1 else int(keyval[1])
                except ValueError:
                    parse_level = 1
            else:
                continue
            if parse_course is not None and parse_level is not None:
                levels[parse_course] = parse_level
                parse_course = None
                parse_level = None
        if parse_course is None and parse_level is not None:
            levels[3] = parse_level
        return {"LEVELS": levels}

    def __parse_balloon_headers(self):
        balloons = [[]] * 5
        parse_course = None
        parse_balloons = None
        for line in self.tja.splitlines():
            if not len(line):
                continue
            if not len(findall("[A-Z]", line[0])):
                continue
            keyval = findall("([A-Z]+):(.*)", line)[0]
            if keyval[0] == "BALLOON":
                try:
                    parse_balloons = [int(hit_count) for hit_count in str(keyval[1]).split(",")]
                except ValueError:
                    pass
            elif keyval[0] == "COURSE":
                parse_course = TJAInfo.parse_course(keyval[1])
            else:
                continue
            if parse_course is not None and parse_balloons is not None:
                balloons[parse_course] = parse_balloons
                parse_course = None
                parse_balloons = None
        if parse_course is None and parse_balloons is not None:
            balloons[3] = parse_balloons
        return {"BALLOONS": balloons}

    def __parse_beatmaps(self):
        beatmaps = [[]] * 5
        parse_beatmap = []
        section = []
        parse_course = None
        is_parsing = False
        in_renda = False
        for line in self.tja.splitlines():
            if not len(line):
                continue
            if line.startswith("/"):
                renda = findall("//RENDA\s*(.+)", line)
                if len(renda):
                    try:
                        self.renda_hits_per_second = float(renda[0])
                    except ValueError:
                        pass
                elif line.startswith("//COMPRESS"):
                    self.compress = True
                continue
            keyval = findall("([A-Z]+):(.*)", line)
            if len(keyval) and keyval[0][0] == "COURSE":
                parse_course = TJAInfo.parse_course(keyval[0][1])
                continue
            elif line.startswith("#START"):
                is_parsing = True
                continue
            elif line.startswith("#END"):
                if is_parsing:
                    if parse_course is None:
                        parse_course = 3
                    beatmaps[parse_course] = parse_beatmap.copy()
                    parse_beatmap.clear()
                    is_parsing = False
                continue
            if is_parsing:
                if "," in line:
                    try:
                        for note in findall("\d+", line)[0]:
                            try:
                                section.append(NoteTypes(int(note)))
                                if NoteTypes(int(note)) in [NoteTypes.RENDA_START, NoteTypes.BIG_RENDA_START, NoteTypes.BALLOON]:
                                    in_renda = True
                            except ValueError:
                                section.append(NoteTypes.RENDA_STOP)
                    except IndexError:
                        pass
                    parse_beatmap.append(section.copy())
                    section.clear()
                elif line.startswith("#"):
                    if line.startswith("#GOGOSTART"):
                        section.append(Gogotime(False))
                    elif line.startswith("#GOGOEND"):
                        section.append(Gogotime(True))
                    elif line.startswith("#BPMCHANGE"):
                        section.append(BPMChange(float(line.split(" ")[1])))
                    elif line.startswith("#SCROLL"):
                        section.append(ScrollChange(float(line.split(" ")[1])))
                    elif line.startswith("#MEASURE"):
                        measure = findall("(\d+)/(\d+)", line)[0]
                        section.append(Measure(Fraction(int(measure[0]), int(measure[1]))))
                else:
                    try:
                        for note in findall("\d+", line)[0]:
                            try:
                                section.append(NoteTypes(int(note)))
                                if NoteTypes(int(note)) in [NoteTypes.RENDA_START, NoteTypes.BIG_RENDA_START, NoteTypes.BALLOON]:
                                    in_renda = True
                            except ValueError:
                                section.append(NoteTypes.RENDA_STOP)
                    except IndexError:
                        pass

        if parse_course is None and parse_beatmap != []:
            beatmaps[3] = parse_beatmap
        for course, beatmap in enumerate(beatmaps):
            balloon_position = 0
            for index, section in enumerate(beatmap):
                for index2, note in enumerate(section):
                    if note == NoteTypes.BALLOON:
                        try:
                            beatmaps[course][index][index2] = Balloon(
                                self.headers["BALLOONS"][course][balloon_position])
                            balloon_position += 1
                        except IndexError:
                            beatmaps[course][index][index2] = Balloon(
                                self.headers["BALLOONS"][course][-1])
        return beatmaps

    def __simulate_play(self):
        results = [None] * 5
        for course, beatmap in enumerate(self.beatmaps):
            if not beatmap:
                continue
            result = {}
            current_time = 0
            max_combo = 0
            in_gogo = False
            current_bpm = self.headers["BPM"]
            current_measure = 1
            diff_ratio = 1
            init_times = 0
            diff_times = 0
            extra_scores = []
            renda_start = 0
            renda_type = None
            for section in beatmap:
                section_length = 0
                for note in section:
                    if isinstance(note, NoteTypes) or isinstance(note, Balloon):
                        section_length += 1
                for note in section:
                    if isinstance(note, BPMChange):
                        current_bpm = note.new_bpm
                    elif isinstance(note, Measure):
                        current_measure = note.value
                    elif isinstance(note, Gogotime):
                        in_gogo = not note.is_end
                    elif isinstance(note, NoteTypes) or isinstance(note, Balloon):
                        current_time += (60 / current_bpm) / (section_length / 4) * current_measure

                    if note in [NoteTypes.RED, NoteTypes.BLUE, NoteTypes.BIG_RED, NoteTypes.BIG_BLUE]:
                        max_combo += 1
                        diff_ratio = max_combo / 10 if max_combo % 10 == 0 and max_combo <= 100 else diff_ratio
                        factor = 1.2 if in_gogo else 1
                        if note in [NoteTypes.BIG_RED, NoteTypes.BIG_BLUE]:
                            factor *= 2
                        init_times += factor
                        diff_times += diff_ratio * factor
                    elif note in [NoteTypes.RENDA_START, NoteTypes.BIG_RENDA_START] or isinstance(note, Balloon):
                        renda_start = current_time
                        renda_type = note
                    elif note == NoteTypes.RENDA_STOP:
                        factor = 1.2 if in_gogo else 1
                        renda_hits = floor((current_time - renda_start) * self.renda_hits_per_second)
                        if renda_type == NoteTypes.RENDA_START:
                            extra_scores.append(renda_hits * 300 * factor)
                        elif renda_type == NoteTypes.BIG_RENDA_START:
                            extra_scores.append(renda_hits * 360 * factor)
                        elif isinstance(renda_type, Balloon):
                            if renda_type.count <= renda_hits:
                                extra_scores.append((renda_type.count * 300 + 5000) * factor)
                            else:
                                extra_scores.append(renda_hits * 300 * factor)
            result["max_combo"] = max_combo
            result["init_times"] = init_times
            result["diff_times"] = diff_times
            result["extra_scores"] = extra_scores
            result["beatmap_length"] = current_time
            result = dict(
                list(result.items()) + list(self.get_max_note_score(course, self.headers["LEVELS"][course], init_times,
                                                                    diff_times, sum(extra_scores)).items()))
            results[course] = result
        return results

    def __get_bpm_display(self):
        bpms = [self.headers["BPM"]]
        for beatmap in self.beatmaps[::-1]:
            if not len(beatmap):
                continue
            for section in beatmap:
                for note in section:
                    if isinstance(note, BPMChange):
                        bpms.append(note.new_bpm)
            highest_bpm = max(bpms)
            lowest_bpm = min(bpms)
            if highest_bpm == lowest_bpm:
                return round(highest_bpm) if highest_bpm.is_integer() else highest_bpm
            else:
                return "{0} - {1}".format(round(lowest_bpm) if lowest_bpm.is_integer() else lowest_bpm,
                                          round(highest_bpm) if highest_bpm.is_integer() else highest_bpm)

    @staticmethod
    def compress_section(section):
        new_section = []
        start_pos = 0
        distances = []
        note_pos = 0
        min_interval = len(section)
        for note in section:
            if note_pos != start_pos and isinstance(note, NoteTypes) and note != NoteTypes.NONE:
                distances.append(note_pos - start_pos)
                start_pos = note_pos
            if isinstance(note, NoteTypes):
                note_pos += 1
        if len(distances):
            min_interval = TJAInfo.multi_gcd(distances)
        note_pos = 0
        for note in section:
            if not isinstance(note, NoteTypes):
                new_section.append(note)
                continue
            if note_pos % min_interval == 0:
                new_section.append(note)
            if isinstance(note, NoteTypes):
                note_pos += 1
        return new_section

    @staticmethod
    def multi_gcd(i):
        if len(i) == 1:
            return i[0]
        while len(i) > 2:
            result = gcd(i[-1], i[-2])
            i.pop(len(i) - 1)
            i[-1] = result
        return gcd(i[0], i[1])

    @staticmethod
    def parse_course(course):
        try:
            return int(course)
        except ValueError:
            try:
                return ["e", "n", "h", "o", "c"].index(course[0].lower())
            except ValueError:
                pass
        return 3

    @staticmethod
    def parse_attribute(key, value):
        floats = ["BPM", "OFFSET", "DEMOSTART"]
        ints = ["SONGVOL", "SEVOL"]
        ignore = ["COURSE", "LEVEL", "BALLOON"]
        if key in floats:
            return float(value)
        if key in ints:
            return int(value)
        if key not in ignore:
            return value

    @staticmethod
    def get_max_note_score(course, level, init_times, diff_times, extra_score):
        scores = {}
        max_score = 0
        if course == 0:
            max_score = 280000 + level * 20000
        elif course == 1:
            max_score = 350000 + level * 50000
        elif course == 2:
            max_score = 500000 + level * 50000
        elif course >= 3:
            max_score = 650000 + level * 50000
            if level >= 10:
                max_score += 50000
        max_score -= extra_score
        for scale in range(300, 501, 1):
            scale *= 0.01
            y = max_score / ((init_times * scale) + diff_times)
            x = y * scale
            scores[(
                round(init_times * (round(x / 10) * 10) + diff_times * (round(y / 10) * 10)))] = [
                round(x / 10) * 10, round(y / 10) * 10]
        max_note_score = min(scores, key = lambda x: abs(x - max_score))
        return {"max_note_score": max_note_score, "score_init": scores[max_note_score][0],
                "score_diff": scores[max_note_score][1]}

        # Greatest common divisor of more than 2 numbers.  Am I terrible for doing it this way?


class NoteTypes(Enum):
    NONE = 0
    RED = 1
    BLUE = 2
    BIG_RED = 3
    BIG_BLUE = 4
    RENDA_START = 5
    BIG_RENDA_START = 6
    BALLOON = 7
    RENDA_STOP = 8


class BPMChange(object):
    def __init__(self, new_bpm):
        self.new_bpm = new_bpm

    def __str__(self):
        return "\n#BPMCHANGE {0}\n".format(self.new_bpm)


class ScrollChange(object):
    def __init__(self, new_hs):
        self.new_hs = new_hs

    def __str__(self):
        return "\n#SCROLL {0}\n".format(self.new_hs)


class Gogotime(object):
    def __init__(self, is_end):
        self.is_end = is_end

    def __str__(self):
        return "\n#GOGOEND\n" if self.is_end else "\n#GOGOSTART\n"


class Balloon(object):
    def __init__(self, count):
        self.count = count

    def __str__(self):
        return "7"


class Measure(object):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        if self.value.denominator < 4:
            magic = 4 / self.value.denominator
            den = round(self.value.denominator * magic)
            num = round(self.value.numerator * magic)
            return "\n#MEASURE {0}/{1}\n".format(num, den)
        return "\n#MEASURE {0}\n".format(self.value)