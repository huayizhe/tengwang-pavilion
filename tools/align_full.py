# -*- coding: utf-8 -*-
"""把 faster-whisper 的字级时间（assets/asr-words.json）对齐到《滕王阁序》全文，
生成 assets/narration-timing.json：

    {"source": "...", "duration": 250.29,
     "text": "豫章故郡，洪都新府。……",
     "chars": [{"ch": "豫", "t": 0.12}, ...]}   # 与 text 逐字一一对应（含标点、换行）

对齐方式：只拿汉字做 difflib 序列比对，比对上的字直接用 ASR 时间，
没比上的（识别错/漏字）按前后锚点线性插值；标点沿用前一个字的时间。
"""
import difflib
import json
import os
import re

from pypinyin import lazy_pinyin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
TEXT = os.path.join(ASSETS, 'tengwang-order.txt')
ASR = os.path.join(ASSETS, 'asr-words.json')
OUT = os.path.join(ASSETS, 'narration-timing.json')

HAN = re.compile(r'[\u4e00-\u9fff]')
PUNCT = set('，。；？！：、“”‘’（）《》「」…—·')


def pinyin_of(ch):
    """汉字 → 不带声调拼音（对齐用：同音字也能对上）"""
    return lazy_pinyin(ch)[0]


def main():
    with open(TEXT, 'r', encoding='utf-8') as f:
        text = f.read()
    text = text.strip() + '\n'
    with open(ASR, 'r', encoding='utf-8') as f:
        asr = json.load(f)
    duration = float(asr['duration'])

    # ---- ASR 字序列（只要汉字） -------------------------------------------
    asr_chars = []
    for word in asr['words']:
        han = [c for c in word['w'] if HAN.match(c)]
        if not han:
            continue
        span = max(.05, float(word['e']) - float(word['s']))
        for k, ch in enumerate(han):
            asr_chars.append((ch, float(word['s']) + span * k / len(han)))
    asr_text = ''.join(c for c, _ in asr_chars)

    # ---- 参考文本里的汉字位置 ---------------------------------------------
    ref_pos = [(i, ch) for i, ch in enumerate(text) if HAN.match(ch)]
    ref_chars = [ch for _, ch in ref_pos]
    ref_keys = [pinyin_of(c) for c in ref_chars]
    asr_keys = [pinyin_of(c) for c, _ in asr_chars]

    sm = difflib.SequenceMatcher(None, ref_keys, asr_keys, autojunk=False)
    times = [None] * len(ref_chars)
    matched = 0
    gaps = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                times[i1 + k] = asr_chars[j1 + k][1]
            matched += i2 - i1
        elif tag in ('replace', 'delete'):
            if i2 - i1 >= 6:
                gaps.append((i1, i2, asr_text[j1:j2][:24]))

    # ---- 未锚定的字用插值补齐 ---------------------------------------------
    anchors = [(i, t) for i, t in enumerate(times) if t is not None]
    rate = (anchors[-1][1] - anchors[0][1]) / max(1, anchors[-1][0] - anchors[0][0])
    filled = []
    ai = 0
    for i in range(len(times)):
        if times[i] is not None:
            filled.append(times[i])
            continue
        # 找左右锚点
        while ai + 1 < len(anchors) and anchors[ai][0] < i:
            ai += 1
        left = anchors[ai] if anchors[ai][0] < i else None
        right = next((a for a in anchors if a[0] > i), None)
        if left and right:
            span = right[0] - left[0]
            filled.append(left[1] + (right[1] - left[1]) * (i - left[0]) / max(1, span))
        elif left:
            filled.append(left[1] + rate * (i - left[0]))
        elif right:
            filled.append(right[1] - rate * (right[0] - i))
        else:
            filled.append(0.0)

    # ---- 单调 + 越界修正 ---------------------------------------------------
    for i in range(1, len(filled)):
        if filled[i] <= filled[i - 1]:
            filled[i] = filled[i - 1] + .02
    for i in range(len(filled)):
        filled[i] = min(max(0.0, filled[i]), duration - .2)

    # ---- 回填到全文（标点/换行沿前后字） ----------------------------------
    out = []
    last_t = 0.0
    ref_i = 0
    for i, ch in enumerate(text):
        if HAN.match(ch):
            t = filled[ref_i]
            ref_i += 1
            last_t = t
            out.append({'ch': ch, 't': round(t, 3)})
        else:
            out.append({'ch': ch, 't': round(min(duration - .1, last_t + .16), 3)})

    data = {
        'source': '13437801102582606_audio.m4a',
        'duration': round(duration, 3),
        'text': text,
        'chars': out
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f'[ok] 参考汉字 {len(ref_chars)} / ASR 汉字 {len(asr_chars)} / 命中 {matched} '
          f'({matched / max(1, len(ref_chars)) * 100:.1f}%)')
    print(f'[ok] 首字 {out[0]["ch"]} @ {out[0]["t"]}s   末字 @ {out[-1]["t"]}s   duration {duration:.2f}s')
    if gaps:
        print(f'[warn] 未对齐的大段落 {len(gaps)} 段（可能参考文本与朗读有出入）：')
        for i1, i2, hint in gaps:
            print(f'   ref[{i1}:{i2}] {"".join(ref_chars[i1:i2])[:28]}   || asr: {hint}')
    print(f'[ok] → {OUT}')


if __name__ == '__main__':
    main()
