# -*- coding: utf-8 -*-
"""用 faster-whisper 转写原始朗诵录音，输出字级时间戳缓存 assets/asr-words.json。

只跑一次；之后对文本的调整只需重跑 tools/align_full.py（读缓存，很快）。
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, 'assets', 'narration.m4a')
OUT = os.path.join(ROOT, 'assets', 'asr-words.json')
_FFMPEG_FALLBACK = r'D:\Tools\ffmpeg\bin\ffmpeg.exe'
FFMPEG = os.environ.get('FFMPEG') or (_FFMPEG_FALLBACK if os.path.exists(_FFMPEG_FALLBACK) else 'ffmpeg')
SR = 16000


def load_audio(path):
    """用 ffmpeg 解码成 16k 单声道 float32（绕开 PyAV 版本兼容问题）"""
    cmd = [FFMPEG, '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768.0


def main():
    from faster_whisper import WhisperModel
    t0 = time.time()
    model = WhisperModel('base', device='cpu', compute_type='int8')
    print(f'[model] base int8 加载 {time.time() - t0:.1f}s', flush=True)
    audio = load_audio(AUDIO)
    print(f'[audio] {len(audio) / SR:.2f}s', flush=True)

    segments, info = model.transcribe(
        audio,
        language='zh',
        beam_size=5,
        vad_filter=False,
        word_timestamps=True,
        condition_on_previous_text=False,
        initial_prompt='滕王阁序，王勃。豫章故郡，洪都新府。',
    )
    print(f'[audio] {info.duration:.2f}s', flush=True)

    words = []
    for seg in segments:
        for w in (seg.words or []):
            text = (w.word or '').strip()
            if not text:
                continue
            words.append({'w': text, 's': round(float(w.start), 3), 'e': round(float(w.end), 3)})
        print(f'  seg {seg.end:6.1f}s  {seg.text.strip()[:24]}', flush=True)

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'duration': round(float(info.duration), 3), 'words': words}, f, ensure_ascii=False)
    print(f'[ok] {len(words)} words → {OUT}  用时 {time.time() - t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
