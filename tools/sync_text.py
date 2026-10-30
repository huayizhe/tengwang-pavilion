# -*- coding: utf-8 -*-
"""把全文时间轴与完整朗诵音频同步进 index.html：

  1) 替换页面里的  const NARRATION = {...};   （NARRATION_TIMING 的旧行也兼容）
  2) 替换 <script id="narrationB64"> 里的 base64 音频（assets 缺失时的离线兜底）
  3) 把 <audio id="narration" src="..."> 指向 assets/narration.m4a

音频改了就跑： python tools/align_full.py && python tools/sync_text.py
"""
import base64
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'index.html')
TIMING = os.path.join(ROOT, 'assets', 'narration-timing.json')
AUDIO = os.path.join(ROOT, 'assets', 'narration.m4a')


def main():
    with open(HTML, 'r', encoding='utf-8') as f:
        html = f.read()
    with open(TIMING, 'r', encoding='utf-8') as f:
        timing = json.load(f)
    compact = json.dumps(timing, ensure_ascii=False, separators=(',', ':'))

    start = -1
    for head in ('const NARRATION = ', 'const NARRATION_TIMING = '):
        start = html.find(head)
        if start >= 0:
            break
    if start < 0:
        raise SystemExit('[FAIL] 找不到 NARRATION 定义行')
    end = html.find(';\n', start)
    if end < 0:
        raise SystemExit('[FAIL] NARRATION 行没有收尾')
    html = html[:start] + 'const NARRATION = ' + compact + html[end:]

    with open(AUDIO, 'rb') as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode('ascii')
    wrapped = '\n'.join(b64[i:i + 1200] for i in range(0, len(b64), 1200))
    match = re.search(r'(<script id="narrationB64"[^>]*>)(.*?)(</script>)', html, re.S)
    if not match:
        raise SystemExit('[FAIL] 找不到 narrationB64 块')
    html = html[:match.start(2)] + '\n' + wrapped + '\n' + html[match.end(2):]

    html = re.sub(
        r'<audio id="narration"[^>]*>',
        '<audio id="narration" src="assets/narration.m4a" preload="auto" loop playsinline aria-hidden="true">',
        html, count=1)

    with open(HTML, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print(f'[ok] 时间轴 {timing["duration"]}s / 字数 {len(timing["chars"])} / '
          f'音频 {len(audio_bytes)} 字节（base64 {len(b64)} 字符）已同步')


if __name__ == '__main__':
    main()
