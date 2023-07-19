import math
from fractions import Fraction
from decimal import *
import time
import argparse

kill = False


# define note prefixes
notePrefix = {
    'NM': '',
    'EX': 'x',
    'BR': 'b',
    'BX': 'bx'
}

# for slide patterns that can be defined immediately
patterns = {
    # 0: '<',
    # 1: '>',
    "SI_": '-',
    "SV_": 'v',
    "SF_": 'w',
    "SUR": 'q',
    "SUL": 'p',
    "SXL": 'pp',
    "SXR": 'qq',
    # 9: 'V',
    "SSL": 's',
    "SSR": 'z',
}

def ticktime(measure, tick, resolution=384):
    return int(measure) * resolution + int(tick)


def tapName(type: str, pos: int):
    #         [1-8]      [/x/bx/b]
    return f"{str(pos)}{notePrefix[type[0:2]]}"

def compDuration(pos: int, duration: int, bpm: list, resolution=384):
    end = pos + duration
    det = []
    for i in range(len(bpm) - 1):
        if ticktime(bpm[i][0], bpm[i][1]) < pos:
            continue
        print(i)
        elem = [i, min(ticktime(bpm[i + 1][0], bpm[i + 1][1]), end) \
                - max(ticktime(bpm[i][0], bpm[i][1]), pos)]
        det.append(elem)
    res = Fraction(0)
    org = bpm[det[0][0]][2]
    for item in det:
        if item[1] < 0:
            break
        res += Fraction(item[1], resolution) * Fraction(int(1000 * org), int(1000 * bpm[item[0]][2]))
    return res

def holdName(type: str, pos: int, dur: Fraction, resolution=384):
    duration = Fraction(dur, resolution)
    #         [1-8]      [/x/b/bx]              h[69                 :420]
    return f"{str(pos)}{notePrefix[type[0:2]]}h[{duration.denominator}:{duration.numerator}]"


def touchName(pos1: str, pos2: str, trigger: int):
    if pos2 == "C":
        if int(trigger) == 1:
            return "Cf"
        return "C"
    elif int(trigger) == 1:
        return str(pos2) + str(pos1) + "f"
    return str(pos2) + str(pos1)


def tHoldName(dur: int, trigger: int, resolution = 384):
    duration = Fraction(dur, resolution)
    if int(trigger) == 1:
        return f"Ch[{duration.denominator}:{duration.numerator}]f"
    return f"Ch[{duration.denominator}:{duration.numerator}]"


def bpmByPosition(measure: int, tick: int, bpmList: list, resolution=384):
    bpm = Decimal(bpmList[0][2])
    for item in bpmList:
        if int(measure) * int(resolution) + int(tick) < int(item[0]) * resolution + int(item[1]):
            break
        bpm = Decimal(item[2])
    return bpm


def slideParse(slideList: list, cursor: int) -> list:
    slide = []
    for i in range(cursor, len(slideList) + 1):
        slide.append(slideList[i])
        if i+1 > len(slideList) - 1:
            break
        if slideList[i + 1][0][2:] == "STR":
            break
    return slide


# fuck simai i am tired
ccw = {
    '<': [
        [2, 1], [2, 8], [2, 7], [2, 6], [2, 5], [2, 4], [2, 3],
        [1, 8], [1, 7], [1, 6], [1, 5], [1, 4], [1, 3], [1, 2],
        [8, 7], [8, 6], [8, 5], [8, 4], [8, 3], [8, 2], [8, 1],
        [7, 6], [7, 5], [7, 4], [7, 3], [7, 2], [7, 1], [7, 8]
    ],
    '>': [
        [6, 5], [6, 4], [6, 3], [6, 2], [6, 1], [6, 8], [6, 7],
        [5, 4], [5, 3], [5, 2], [5, 1], [5, 8], [5, 7], [5, 6],
        [4, 3], [4, 2], [4, 1], [4, 8], [4, 7], [4, 6], [4, 5],
        [3, 2], [3, 1], [3, 8], [3, 7], [3, 6], [3, 5], [3, 4]
    ],
}

cw = {
    '<': [
        [3, 4], [3, 5], [3, 6], [3, 7], [3, 8], [3, 1], [3, 2],
        [4, 5], [4, 6], [4, 7], [4, 8], [4, 1], [4, 2], [4, 3],
        [5, 6], [5, 7], [5, 8], [5, 1], [5, 2], [5, 3], [5, 4],
        [6, 7], [6, 8], [6, 1], [6, 2], [6, 3], [6, 4], [6, 5]
    ],
    '>': [
        [7, 8], [7, 1], [7, 2], [7, 3], [7, 4], [7, 5], [7, 6],
        [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 6], [8, 7],
        [1, 2], [1, 3], [1, 4], [1, 5], [1, 6], [1, 7], [1, 8],
        [2, 3], [2, 4], [2, 5], [2, 6], [2, 7], [2, 8], [2, 1]
    ]
}

def rearrangeCNS(slides: list):
    # there are two factors to connect a slide
    # (1): same endpoint as startpoint of previous slide
    # (2): timing starts as soon as the previous slide finishes
    # note: slide can have exact same parameters, so mark the slide segments with indexes

    # mark normal slides first
    nm = []
    cn = []
    for i in range(len(slides)):
        if slides[i][0][0:2] == "NM" or slides[i][0][0:2] == "BR":
            nm.append(i)
        # ends once it hits a CN slide
        if slides[i][0][0:2] == "CN":
            break
            # no need to record this since NM slides are always put first, then a list of CN slides follows
    nm.pop(0)
    if len(nm) <= 1:
        return slides
    startPos = max(nm)
    order = []
    used = []
    for item in nm:
        used.append(item)
    for nms in nm:
        tmp = []
        tmp.append(slides[nms])
        for i in range(startPos, len(slides)):
            if slides[i][3] == tmp[len(tmp) - 1][6] \
                    and ticktime(slides[i][1], slides[i][2]) == ticktime(tmp[len(tmp) - 1][1], tmp[len(tmp) - 1][2]) \
                    + int(tmp[len(tmp) - 1][4]) + int(tmp[len(tmp) - 1][5]) \
                    and i not in used:
                used.append(i)
                tmp.append(slides[i])
        order.append(tmp)
    final = [slides[0]]
    for item in order:
        for sub in item:
            final.append(sub)
    return final


def cwDir(startPos: int, endPos: int, dir: str) -> str:
    if startPos == endPos:
        # the slide direction depends solely on the startPos and direction
        # SCL: ccw, SCR: cw
        if dir[2:] == "SCL":
            if int(startPos) in [1, 2, 7, 8]:
                return '<'
            else:
                return '>'
        else:
            if int(startPos) in [1, 2, 7, 8]:
                return '>'
            else:
                return '<'
    else:
        if dir[2:] == "SCL":
            if [int(startPos), int(endPos)] in ccw['<']:
                return '<'
            else:
                return '>'
        else:
            if [int(startPos), int(endPos)] in cw['<']:
                return '<'
            else:
                return '>'


def vAnchor(startPos: int, endPos: int, dir: str):
    if dir[2:] == "SLL":
        pad = int(startPos) - 2
        if pad < 1:
            pad += 8
    else:
        pad = int(startPos) + 2
        if pad > 8:
            pad -= 8
    return str(pad)


def makeSlide(slide: list, bpm: list, resolution=384):
    slideStr = ""
    # count the amount of slides that sprout from one star
    sprout = [0]
    sumStart = 0
    sumEnd = 0
    star = 0
    for i in range(2, len(slide)):
        if slide[i][0][0:2] in ["NM", "BR"]:
            sprout.append(i)
    sprout.append(len(slide))
    for i in range(len(slide)):
        if i in sprout and i != 0:
            slideStr += "*"
        if slide[i][0][2:] == "STR":
            slideStr += tapName(slide[i][0][0:2], slide[i][3])
        elif slide[i][0][2:] in ["SCL", "SCR"]:
            slideStr += cwDir(slide[i][3], slide[i][6], slide[i][0]) + str(slide[i][6])
        elif slide[i][0][2:] in ["SLL", "SLR"]:
            slideStr += "V" + vAnchor(slide[i][3], slide[i][6], slide[i][0]) + str(slide[i][6])
        else:
            slideStr += patterns[slide[i][0][2:]] + str(slide[i][6])
        # slide duration
        if i+1 in sprout or i+1 == len(slide):
            # sum everything up to the last sprout point
            for pt in sprout:
                if pt > sumEnd:
                    sumEnd = pt
                    break
            duration = 0
            for items in slide[sumStart+1:sumEnd]:
                duration += int(items[5])
            duration = Fraction(duration, resolution)
            # ah yes, delayed sliders
            if int(slide[sumStart+1][4]) != resolution // 4:
                duration /= int(int(slide[sumStart+1][4]) // (resolution / 4))
                slideStr += \
                    f"[{Decimal(bpmByPosition(slide[sumStart][1], slide[sumStart][2], bpm)) / int(int(slide[sumStart-1][4]) // (resolution / 4))}" \
                            f"\u0023\u0023{duration.denominator}:{duration.numerator}] "
            else:

                slideStr += f"[{duration.denominator}:{duration.numerator}]"
            sumStart = sumEnd-1
            # break slide
            if slide[star+1][0][0:2] == "BR":
                slideStr += "b"
                star = sumStart
    return slideStr


start = time.time()
# file path, defaults to chart.ma2 if not defined
filePath = "chart.ma2"
# number of decimal points used when defining bpm, defaults to 3
decimals = 3
getcontext().prec = decimals
f = open(filePath, encoding='utf-8')
# get chart version - line 1
# ends immediately if version != 1.04.00
ver = (f.readline().split())[2]
print(f"Chart version: {ver}")
if ver != "1.04.00":
    print(f"Expected chart version: 1.04.00. Found: {ver}. The script will now terminate.")
    kill = True
# get chart resolution - line 4
if not kill:
    for i in range(3):
        f.readline()
    resolution = (f.readline()).split()[1]
    # get bpm list
    # note: MET aka time signature doesn't mean shit in simai
    bpm = []
    # measure, ticks, bpm
    for i in range(3):
        f.readline()
    while True:
        entry = f.readline().split()
        if entry[0] == "MET":
            break
        else:
            bpm.append(entry[1:])
    # seek the file until a blank line
    while True:
        tmp = f.readline()
        if tmp == "\n":
            break
    # get notes
    notes = {
        0: []
    }
    while True:
        line = f.readline().split()
        if len(line) == 0:
            break
        if int(line[1]) not in notes:
            notes[int(line[1])] = []
        tgt = notes[int(line[1])]
        tgt.append(line)
        notes[int(line[1])] = tgt
    # reformat all button pos
    for key in notes:
        old = notes[key]
        for i in range(len(old)):
            # not slide: 1 position to fix
            if old[i][0][2:] == "TAP" or old[i][0][2:] == "HLD" or old[i][0][2:] == "STR"\
                    or old[i][0][2:] == "TTP" or old[i][0][2:] == "THO":
                old[i][3] = int(old[i][3]) + 1
            else:
                old[i][3] = int(old[i][3]) + 1
                old[i][6] = int(old[i][6]) + 1
        notes[key] = old
    # add bpm as part of note too
    for item in bpm:
        tgt = notes[int(item[0])]
        tgt.append(["BPM", item[0], item[1], item[2]])
    # slide lists
    slides = []
    cnSlides = []
    for key in notes:
        for item in (notes[key]):
            if item[0][2] == "S" and item[0][0] != 'C':
                slides.append(item)
            elif item[0][2] == "S" and item[0][0] == 'C':
                cnSlides.append(item)
    slideList = []
    for item in cnSlides:
        targetTime = ticktime(int(item[1]), int(item[2]))
        for i in range(len(slides)):
            if len(slides[i]) == 7 and ticktime(int(slides[i][1]), int(slides[i][2])) \
                    + int(slides[i][4]) + int(slides[i][5]) == targetTime\
            and int(item[3]) == int(slides[i][6]):
                slides.insert(i+1, item)
                break
    cursor = 0

    while True:
        next = slideParse(slides, cursor)
        slideList.append(next)
        cursor += len(next)
        if cursor >= len(slides):
            break
    # try rearranging slides
    for i in range(len(slideList)):
        (slideList[i]).sort(key=lambda x: int(x[1]))
    # run rearrangeCNS over all slides
    for i in range(len(slideList)):
        slideList[i] = rearrangeCNS(slideList[i])
    events = {
        0: []
    }
    # add non-slides to event list
    for key in notes:
        tgt = []
        for item in notes[key]:
            if int(item[1]) not in events:
                events[int(item[1])] = []
            # tap
            if item[0][2:] == "TAP":
                tgt.append([int(item[2]), tapName(item[0], item[3])])
            # hold
            elif item[0][2:] == "HLD":
                tgt.append([int(item[2]), holdName(item[0], item[3], int(item[4]))])
            # touch
            elif item[0][2:] == "TTP":
                tgt.append([int(item[2]), touchName(item[3], item[4], item[5])])
            # touch hold
            elif item[0][2:] == "THO":
                tgt.append([int(item[2]), tHoldName(int(item[4]), item[6])])
            elif item[0] == "BPM":
                tgt.append([int(item[2]), f"({item[3]})"])
        events[key] = tgt
    # add slides
    slideCnt = 0
    for item in slideList:
        tgt = events[int(item[0][1])]
        tgt.append([int(item[0][2]),makeSlide(item, bpm)])
        events[int(item[0][1])] = tgt
        slideCnt += 1
    # total note count
    noteCnt = 0
    for key in events:
        noteCnt += len(events[key])
    # get the unique divisor for each measure
    div = {
        0: 1,
    }
    # fill non-measures with note that do nuthing
    for i in range(max(list(events))):
        if i not in events:
            events[i] = [[0, '']]
    events = dict(sorted(events.items()))
    for key in events:
        divC = 384
        for item in events[key]:
            if item[0] == 0:
                divC = math.gcd(384, divC)
            else:
                divC = math.gcd(int(item[0]), divC)
        div[key] = 384 // divC
    # events too
    f = open("simai.txt", "w")
    # start writing now
    for key in events:
        line = []
        if key == 0:
            f.write(f"({bpmByPosition(0, 0, bpm)})\u007b{div[key]}\u007d")
        elif div[key] != div[key-1]:
            f.write(f"\u007b{div[key]}\u007d")
        # traverse the list
        for cursor in range (0, int(resolution)+1, int(resolution) // div[key]):
            obj = []
            for items in events[key]:
                #print(items, cursor)
                if items[0] == cursor:
                    obj.append(items[1])
            obj.sort()
            if not obj:
                noteStr = ""
            else:
                noteStr = ""
                nonBpm = 0
                for note in obj:
                    if note == '':
                        pass
                    elif note[0] != '(':
                        nonBpm += 1
                if len(obj) - nonBpm == 1:
                    noteStr += obj[0]
                    if len(obj) > 1:
                        for i in range(1, len(obj), 1):
                            noteStr += f"{obj[i]}/"
                else:
                    for i in range(0, len(obj), 1):
                        noteStr += f"{obj[i]}/"
                # trim just in case...
                if noteStr:
                    if noteStr[len(noteStr)-1] == '/':
                        noteStr = noteStr[0: len(noteStr)-1]
            line.append(noteStr)
        f.write(','.join(line))
        f.write("\n")
    f.write("E")
    f.close()
    end = time.time()
    print(f"Finished in {1000 * (end-start)}ms")