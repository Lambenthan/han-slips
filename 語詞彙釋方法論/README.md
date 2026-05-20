# 語詞彙釋方法論

本目錄收錄一套用於從多篇學術論文聚合生成「語詞彙釋」工具書的方法論與可執行 pipeline。

範本來源：徐碩《长沙五一广场东汉简牍（壹）-（肆）》语词汇释（吉林大学硕士学位论文，2023）。

## 為什麼有這個方法論

前期已嘗試過兩套做法：

1. **單論文逐條提取**（最初做法）— 每篇論文獨立整理為一組詞條。問題：同一個字在十位學者那裡的不同看法無法聚合到一處。
2. **學習材料風格直接複製**（中期做法）— 按學習材料.docx的「一術語一詞條」粒度排列。問題：學習材料只有 13 條，不是工具書級別。

徐碩硕士論文採用的是真正的「工具書」做法：**跨論文聚合**。把分散在 200 篇論文中對同一字詞的所有解讀，全部聚合到一個辭條下，按學者發表時間排序，形成 506 頁的完整工具書。本目錄即用於復刻這套方法論。

## 文件結構

```
語詞彙釋方法論/
├── README.md                  本說明
├── 方法論.md                  完整方法論文檔（即 skill）
├── scripts/
│   ├── build_glossary.py      聚合 pipeline 主腳本
│   └── render_docx.js         Word 排版腳本
└── 示範/
    ├── README.md              示範說明
    ├── papers_codebook.json   論文簡稱表
    ├── terms_raw.jsonl        語詞原始卡片
    ├── glossary.json          聚合輸出
    ├── glossary.md            Markdown 版
    └── 示範·語詞彙釋.docx     Word 成稿
```

## 跑通示範

```bash
cd 示範

# 安裝依賴
pip install pypinyin
npm install -g docx

# 聚合
python ../scripts/build_glossary.py \
    --codebook papers_codebook.json \
    --raw terms_raw.jsonl \
    --out glossary.json \
    --md glossary.md

# 渲染
NODE_PATH=$(npm root -g) node ../scripts/render_docx.js \
    --glossary glossary.json \
    --out 示範·語詞彙釋.docx \
    --title "示範·語詞彙釋"
```

示範產出 20 條辭條（從 6 篇論文聚合），體現了「多家解讀同字」的工具書範式。

## 核心方法論

### 凡例（必須遵循）

1. **辭條標注**：用 `[字]` 形式
2. **音序排列**：A-Z 拼音音序，同字母下按音節細分
3. **簡號**：每辭條下列出 1-3 條簡號 + 形制（木牘/竹簡/木兩行/封檢等）
4. **解讀排序**：按學者發表時間先後
5. **學者簡稱**：用 `【作者+年份】` 格式（如 `【姚遠2022A】`）
6. **頁碼**：每條解讀末尾 `（XX 頁）`
7. **繁體字**：辭條、釋文均用繁體
8. **按語**：個別處可加 `【按】` 或 `【碩按】`

### Pipeline 流程

```
論文 PDF 集合
    ↓ (對每篇論文用 Read PDF 多模態抽取討論的語詞)
語詞原始卡片 terms_raw.jsonl
    ↓ (build_glossary.py 按 term 聚合，去重簡號，按時序排序)
聚合辭條 glossary.json
    ↓ (render_docx.js 按徐碩範式排版)
語詞彙釋.docx
```

### 完整工具書還需要

本示範僅含正文 20 條辭條，要復刻徐碩 506 頁完整版還需：

- **緒論**（20-30 頁）：出土公布情況、簡牘性質、專題研究綜述
- **附錄五項**：辭條索引、新舊簡號對照表、綴合補表、文書編聯統計、地名整理表
- **參考文獻**：按專著、學位論文、期刊、會議、報紙、網絡分類

詳細範式見 `方法論.md`。

## 全局可用的 skill

本方法論已封裝為 Claude Code skill：`bamboo-slips-lexical-glossary`

未來在任何項目中，用戶提到「語詞彙釋」「徐碩範式」「跨論文聚合辭條」等關鍵詞時，skill 自動觸發。
