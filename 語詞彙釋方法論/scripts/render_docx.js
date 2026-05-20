/**
 * 把聚合后的 glossary.json 渲染为符合徐碩范式的 Word 文档
 *
 * 用法：
 *   NODE_PATH=$(npm root -g) node render_docx.js \
 *       --glossary glossary.json \
 *       --out glossary.docx \
 *       --title "《长沙五一广场东汉简牍（壹）-（陆）》语词汇释"
 */
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, PageBreak,
  HeadingLevel,
} = require('docx');
const fs = require('fs');
const path = require('path');

function parseArgs() {
  const args = {};
  for (let i = 2; i < process.argv.length; i++) {
    const a = process.argv[i];
    if (a.startsWith('--')) {
      args[a.slice(2)] = process.argv[++i];
    }
  }
  return args;
}

const args = parseArgs();
const entries = JSON.parse(fs.readFileSync(args.glossary, 'utf-8'));
const title = args.title || '語詞彙釋';

// 范本字体（与徐碩论文一致：宋体五号，kern=2）
const FONT = { ascii: '宋体', hAnsi: '宋体', eastAsia: '宋体' };
const SIZE = 21; // 五号 10.5pt

function para(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.BOTH,
    children: [
      new TextRun({
        text,
        font: FONT,
        size: SIZE,
        kern: 2,
        ...opts.run,
      }),
    ],
    ...opts.paragraph,
  });
}

function blank() {
  return new Paragraph({ children: [] });
}

function letterHeading(letter) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 400, after: 200 },
    children: [
      new TextRun({
        text: letter,
        font: FONT,
        size: 36, // 18pt
        bold: true,
      }),
    ],
  });
}

const children = [];

// 标题页
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 2000, after: 400 },
  children: [
    new TextRun({ text: title, font: FONT, size: 44, bold: true })
  ],
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 按字母分组
let currentLetter = null;
for (const e of entries) {
  if (e.first_letter !== currentLetter) {
    currentLetter = e.first_letter;
    children.push(letterHeading(currentLetter));
  }

  // 辞条标题 [词]
  children.push(new Paragraph({
    spacing: { before: 240, after: 80 },
    keepNext: true,
    children: [
      new TextRun({ text: `[${e.term}]`, font: FONT, size: SIZE, bold: true })
    ],
  }));

  // 编号：行
  children.push(para('編號：'));

  for (const c of e.codes) {
    const parts = [];
    if (c.vol_num) parts.push(c.vol_num);
    if (c.shape) parts.push(c.shape);
    parts.push(c.id);
    children.push(para(parts.join('  ')));
  }

  if (e.codes.length === 0) {
    children.push(para('（無）'));
  }

  // 各家解读
  for (const interp of e.interpretations) {
    const pageMark = interp.page ? `（${interp.page} 頁）` : '';
    children.push(new Paragraph({
      alignment: AlignmentType.BOTH,
      spacing: { before: 80, after: 80 },
      children: [
        new TextRun({
          text: interp.paper_abbrev,
          font: FONT,
          size: SIZE,
          bold: true,
          kern: 2,
        }),
        new TextRun({
          text: ` ${interp.text}${pageMark}`,
          font: FONT,
          size: SIZE,
          kern: 2,
        }),
      ],
    }));
  }

  children.push(blank());
}

const doc = new Document({
  creator: '语词汇释生成器',
  title,
  styles: {
    default: {
      document: { run: { font: FONT, size: SIZE, kern: 2 } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, bottom: 1440, left: 1800, right: 1800, header: 851, footer: 992 },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(args.out, buf);
  console.log(`输出：${args.out} (${buf.length} bytes, ${entries.length} 条辞条)`);
});
