"""
语词汇释 pipeline 主脚本

输入：
  - papers_codebook.json    论文简称表
  - terms_raw.jsonl         逐篇抽取的语词卡片（每行一条）

处理：
  1. 按 term 聚合
  2. 按学者发表时间排序
  3. 按拼音音序对辞条排序
  4. 输出聚合后的 JSON 与 markdown

用法：
  python build_glossary.py \
      --codebook papers_codebook.json \
      --raw terms_raw.jsonl \
      --out glossary.json \
      --md glossary.md
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from pypinyin import lazy_pinyin, Style
except ImportError:
    print("需要安装 pypinyin: pip install pypinyin", file=sys.stderr)
    sys.exit(1)


def get_pinyin(term: str) -> tuple[str, str]:
    """返回 (无声调拼音, 带声调拼音) 用于排序"""
    no_tone = ''.join(lazy_pinyin(term))
    with_tone = ''.join(lazy_pinyin(term, style=Style.TONE3))
    return no_tone.lower(), with_tone.lower()


def normalize_term(term: str) -> str:
    """规范化辞条：去除通假/异体符号、空白"""
    # 去掉 (xx) （）注释
    t = re.sub(r'[（(][^）)]*[）)]', '', term)
    t = re.sub(r'\s+', '', t)
    return t.strip()


def aggregate(codebook_path: Path, raw_path: Path) -> list[dict]:
    """聚合按辞条"""
    # 读论文简称表
    with open(codebook_path, 'r', encoding='utf-8') as f:
        codebook = json.load(f)
    scholar_year = {s['abbrev']: s['year'] for s in codebook['scholars']}

    # 读原始卡片
    groups = defaultdict(list)
    with open(raw_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            card = json.loads(line)
            key = normalize_term(card['term'])
            groups[key].append(card)

    # 聚合为辞条
    entries = []
    for term_key, cards in groups.items():
        # 用第一张卡片的 term 原文（保留繁体）
        term_display = cards[0]['term']

        # 简号列表去重
        seen_codes = set()
        codes = []
        for c in cards:
            code = c.get('code', '').strip()
            if code and code != '—' and code not in seen_codes:
                seen_codes.add(code)
                codes.append({
                    'id': code,
                    'shape': c.get('shape', ''),
                    'vol_num': c.get('vol_num', ''),
                })

        # 解读按发表时间排序
        cards_sorted = sorted(
            cards,
            key=lambda c: (scholar_year.get(c['paper_abbrev'], 9999), c['paper_abbrev'])
        )

        # 拼音排序键
        no_tone, with_tone = get_pinyin(term_key)

        entries.append({
            'term': term_display,
            'sort_key_no_tone': no_tone,
            'sort_key_with_tone': with_tone,
            'first_letter': no_tone[0].upper() if no_tone else 'Z',
            'codes': codes,
            'interpretations': [
                {
                    'paper_abbrev': c['paper_abbrev'],
                    'text': c['interpretation'],
                    'page': c.get('page', ''),
                }
                for c in cards_sorted
            ]
        })

    # 按拼音音序排序
    entries.sort(key=lambda e: (e['sort_key_no_tone'], e['sort_key_with_tone']))
    return entries


def to_markdown(entries: list[dict]) -> str:
    """渲染为 markdown（按字母分组）"""
    lines = ['# 語詞彙釋', '']
    current_letter = None

    for e in entries:
        if e['first_letter'] != current_letter:
            current_letter = e['first_letter']
            lines.append('')
            lines.append(f'## {current_letter}')
            lines.append('')

        lines.append(f"### [{e['term']}]")
        lines.append('')
        lines.append('**編號：**')
        for c in e['codes']:
            label = f"{c['vol_num']} " if c['vol_num'] else ''
            shape = f"  {c['shape']} " if c['shape'] else ''
            lines.append(f"- {label}{shape}{c['id']}")
        lines.append('')
        for interp in e['interpretations']:
            page = f"（{interp['page']} 頁）" if interp['page'] else ''
            lines.append(f"{interp['paper_abbrev']} {interp['text']}{page}")
            lines.append('')
        lines.append('')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description="聚合语词卡片为汇释辞条")
    ap.add_argument('--codebook', type=Path, required=True)
    ap.add_argument('--raw', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--md', type=Path, default=None)
    args = ap.parse_args()

    entries = aggregate(args.codebook, args.raw)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"输出：{args.out}（{len(entries)} 条辞条）")

    if args.md:
        with open(args.md, 'w', encoding='utf-8') as f:
            f.write(to_markdown(entries))
        print(f"Markdown：{args.md}")


if __name__ == '__main__':
    main()
