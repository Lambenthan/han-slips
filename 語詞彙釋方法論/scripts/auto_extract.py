"""
从 125 个 PDF 文本中自动批量提取语词卡片
策略：定位带简号的段落 → 抽取语词标题 → 抓取释义内容
"""
import os
import re
import json
from pathlib import Path

TXT_DIR = Path('/tmp/article_txt')
OUT_FILE = Path('/tmp/terms_raw_auto.jsonl')

# 简号模式（覆盖所有变体）
CODE_PATTERNS = [
    r'2010\s*CWJ1\s*[①②③①②③]\s*[：:]\s*\d+(?:-\d+)*',  # 2010CWJ1③：71-26
    r'CWJ1\s*[①②③①②③]\s*[：:]\s*\d+(?:-\d+)*',  # CWJ1③：71-26
    r'CWJ1\s*-\s*\d\s*[：:]?\s*\d+(?:-\d+)*',     # CWJ1-3:193
    r'J1\s*[③]\s*[：:]\s*\d+(?:-\d+)*',           # J1③：281-5
    r'CWJ\d+\s*[①②③]\s*[：:]\s*\d+(?:-\d+)*',
]
CODE_RE = re.compile('|'.join(f'(?:{p})' for p in CODE_PATTERNS))

# 移除字符间空格（很多 PDF 文本损坏，每字符间插空格）
SPACED_CHARS_RE = re.compile(r'(?<=[一-鿿])\s+(?=[一-鿿])')

def normalize_text(text: str) -> str:
    """规范化文本：去除汉字之间无意义的空格"""
    # 多次替换直到稳定
    prev = None
    while prev != text:
        prev = text
        text = SPACED_CHARS_RE.sub('', text)
    return text


# 学者+年份 简称提取（从文件名）
def extract_paper_meta(filename: str) -> dict:
    """从文件名提取作者和年份"""
    stem = filename.replace('.txt', '').replace('.pdf', '')
    # 模式 1: 2019-标题-作者
    m = re.match(r'^(\d{4})\s*-\s*(.+?)\s*-\s*(.+)$', stem)
    if m:
        year = m.group(1)
        title = m.group(2)
        author = m.group(3)
        return {'authors': author, 'year': int(year), 'title': title}
    # 模式 2: 标题_作者
    m = re.match(r'^(.+?)_(.+)$', stem)
    if m:
        title = m.group(1)
        author = m.group(2)
        return {'authors': author, 'year': None, 'title': title}
    # 模式 3: 全是标题
    return {'authors': 'Unknown', 'year': None, 'title': stem}


# 释义模式 1：训诂式 "X，Y也"
# 例："格殺，相拒而殺之曰格殺"
# 例："案，按也"
GLOSS_PATTERNS = [
    # X，Y也 (训诂)
    re.compile(r'[「【\["“]([一-鿿]{1,6})[」】\]"”]\s*[，,]\s*([^。，；]{5,100}也)'),
    # X：解释（行首）
    re.compile(r'^[「【\["“]?([一-鿿]{1,6})[」】\]"”]?[：:]\s*([^。\n]{10,200})', re.MULTILINE),
    # X[N]：解释 (选释/释译式)
    re.compile(r'([一-鿿]{1,10})\s*\[\s*(\d+)\s*\]\s*[：:]\s*([^[]{10,500})'),
]

def extract_codes_and_terms(text: str, paper_meta: dict, abbrev: str):
    """从文本中提取语词卡片"""
    cards = []
    text = normalize_text(text)

    # 找出所有简号
    code_matches = list(CODE_RE.finditer(text))

    # 模式 1: 训诂式 "X，Y也"
    for m in GLOSS_PATTERNS[0].finditer(text):
        term = m.group(1).strip()
        interp = m.group(2).strip()
        if 2 <= len(term) <= 6 and 5 <= len(interp) <= 100:
            # 寻找附近简号
            pos = m.start()
            nearby_code = ''
            for cm in code_matches:
                if abs(cm.start() - pos) < 500:
                    nearby_code = cm.group(0).strip()
                    break
            cards.append({
                'paper_abbrev': abbrev,
                'term': term,
                'code': nearby_code,
                'shape': '',
                'vol_num': '',
                'interpretation': f'{term}，{interp}',
                'page': '',
                '_pattern': 'gloss-A',
            })

    # 模式 3: 编号注释 X[N]：Y
    for m in GLOSS_PATTERNS[2].finditer(text):
        term = m.group(1).strip()
        # 清理 term：去掉前面句号、空格等
        term = re.sub(r'^[，。、；：\s]+', '', term)
        term = term[-6:] if len(term) > 6 else term  # 最后 6 字
        interp = m.group(3).strip()[:500]
        if 1 <= len(term) <= 8 and 10 <= len(interp) <= 500:
            pos = m.start()
            nearby_code = ''
            for cm in code_matches:
                if abs(cm.start() - pos) < 1000:
                    nearby_code = cm.group(0).strip()
                    break
            cards.append({
                'paper_abbrev': abbrev,
                'term': term,
                'code': nearby_code,
                'shape': '',
                'vol_num': '',
                'interpretation': interp,
                'page': '',
                '_pattern': 'bracket-N',
            })

    # 模式 2: 行首 "X：释义" (谨慎，限制术语长度短)
    for m in GLOSS_PATTERNS[1].finditer(text):
        term = m.group(1).strip()
        interp = m.group(2).strip()
        # 排除"如：""即：""注：""见："等无意义模式
        if term in ('如', '即', '注', '见', '見', '若', '又', '故', '蓋', '如','例','按'):
            continue
        if 1 <= len(term) <= 5 and 10 <= len(interp) <= 200:
            pos = m.start()
            nearby_code = ''
            for cm in code_matches:
                if abs(cm.start() - pos) < 1000:
                    nearby_code = cm.group(0).strip()
                    break
            cards.append({
                'paper_abbrev': abbrev,
                'term': term,
                'code': nearby_code,
                'shape': '',
                'vol_num': '',
                'interpretation': interp,
                'page': '',
                '_pattern': 'colon-line',
            })

    return cards


# 主流程
def main():
    all_cards = []
    paper_metas = {}
    paper_count = 0

    for txt_file in sorted(TXT_DIR.glob('*.txt')):
        text = txt_file.read_text(encoding='utf-8', errors='ignore')
        if len(text) < 100:
            continue  # 跳过空文件

        meta = extract_paper_meta(txt_file.name)
        # 创建简称
        if meta['year']:
            abbrev = f"【{meta['authors']}{meta['year']}】"
        else:
            abbrev = f"【{meta['authors']}】"
        paper_metas[abbrev] = meta

        cards = extract_codes_and_terms(text, meta, abbrev)
        if cards:
            all_cards.extend(cards)
            paper_count += 1

    # 去重相同 (abbrev, term, code, interp[:50])
    seen = set()
    deduped = []
    for c in all_cards:
        key = (c['paper_abbrev'], c['term'], c['code'], c['interpretation'][:50])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    print(f"扫描 PDF 文本: {len(list(TXT_DIR.glob('*.txt')))} 个")
    print(f"有效论文数: {paper_count}")
    print(f"原始卡片数: {len(all_cards)}")
    print(f"去重后: {len(deduped)}")

    # 按 term 统计聚合数
    from collections import Counter
    term_counts = Counter(c['term'] for c in deduped)
    multi_paper_terms = {t for t, n in term_counts.items() if n >= 2}
    print(f"独立辞条数: {len(term_counts)}")
    print(f"多论文聚合辞条数: {len(multi_paper_terms)}")

    # 输出
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        for c in deduped:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    print(f"\n输出: {OUT_FILE}")

    # 同时输出简称表
    codebook = {
        'source_volumes': [
            {"abbrev": "【簡報】", "title": "湖南長沙五一廣場東漢簡牍發掘簡報", "year": 2013},
            {"abbrev": "【選釋】", "title": "長沙五一廣場東漢簡牍選釋", "year": 2015},
            {"abbrev": "【壹】", "title": "長沙五一廣場東漢簡牍（壹）", "year": 2018},
            {"abbrev": "【貳】", "title": "長沙五一廣場東漢簡牍（貳）", "year": 2018},
            {"abbrev": "【叄】", "title": "長沙五一廣場東漢簡牍（叄）", "year": 2019},
            {"abbrev": "【肆】", "title": "長沙五一廣場東漢簡牍（肆）", "year": 2019},
            {"abbrev": "【伍】", "title": "長沙五一廣場東漢簡牍（伍）", "year": 2020},
            {"abbrev": "【陸】", "title": "長沙五一廣場東漢簡牍（陸）", "year": 2020},
        ],
        'scholars': [
            {'abbrev': k, 'authors': v['authors'], 'year': v['year'] or 2099,
             'title': v['title'], 'venue': ''}
            for k, v in paper_metas.items()
        ]
    }
    cb_path = OUT_FILE.parent / 'codebook_auto.json'
    with open(cb_path, 'w', encoding='utf-8') as f:
        json.dump(codebook, f, ensure_ascii=False, indent=2)
    print(f"简称表: {cb_path}")
    print(f"共 {len(paper_metas)} 位学者/论文")

if __name__ == '__main__':
    main()
