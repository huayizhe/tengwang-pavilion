# -*- coding: utf-8 -*-
"""抽出 index.html 里的 <script type="module">，做 node --check 语法自检（临时文件用完即删）。"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'index.html')
OUT = os.path.join(ROOT, 'tools', '_extracted.mjs')


def main():
    with open(HTML, 'r', encoding='utf-8') as f:
        html = f.read()
    m = re.search(r'<script type="module">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit('[FAIL] 找不到 module script')
    code = m.group(1)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'extracted {len(code)} chars')
    try:
        proc = subprocess.run(['node', '--check', OUT], capture_output=True)
        sys.stdout.write(proc.stdout.decode('utf-8', 'replace'))
        sys.stdout.write(proc.stderr.decode('utf-8', 'replace'))
        print('syntax:', 'OK' if proc.returncode == 0 else 'FAIL')
        if proc.returncode != 0:
            raise SystemExit(1)
    finally:
        # 自检用的临时文件不留痕
        if os.path.exists(OUT):
            os.remove(OUT)


if __name__ == '__main__':
    main()
