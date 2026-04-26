# KAGAMI_REVIEW_TOOL

> 一个可开源、可扩展、可审计的学术文献综述 Agent  
> 输入：研究主题 + 关键词  
> 输出：严格基于摘要、带 `#id` 证据引用的结构化综述报告

---

# 1. 项目介绍

KAGAMI_REVIEW_TOOL 是一个自动化学术综述系统，面向科研人员与开发者，支持从多源数据库检索文献，并基于 LLM 生成**可追溯、结构化、可审计**的综述报告。

与传统“生成式综述”不同，本项目强调：

- **只基于摘要内容**
- **所有结论必须带 `#id` 引用**
- **全流程可复现 + 可审计**

---

## ✨ 核心特性

- ✅ 多源文献检索（OpenAlex / Semantic Scholar / PubMed / arXiv 等）
- ✅ 自动关键词扩展 + 布尔检索式生成
- ✅ 文献去重 + 标准化编号（#1, #2, #3...）
- ✅ LLM 分块分析（支持 100+ 文献）
- ✅ 强制证据引用（防幻觉）
- ✅ 结果结构化输出（Markdown / JSON）
- ✅ 全流程日志记录（可审计）

---

# 2. 系统架构

## 2.1 工作流

```text
用户输入 topic / keywords
        ↓
关键词扩展（LLM）
        ↓
布尔检索式生成
        ↓
多源文献检索（API）
        ↓
数据清洗 + 去重
        ↓
文献编号（#id）
        ↓
文本分块（chunking）
        ↓
LLM 分块分析（严格基于摘要）
        ↓
全局汇总 + 证据对齐
        ↓
生成综述报告
```

---

## 2.2 架构分层

```text
User Input
    ↓
Agent Orchestrator（agents/）
    ↓
Query Layer（query/）
    ↓
Retriever Layer（retriever/）
    ↓
Processing Layer（parser/ + utils/）
    ↓
Analysis Layer（analyzer/）
    ↓
Output Layer（output/）
```

---

# 3. 模块设计

## 3.1 Retriever Layer（检索层）

支持数据源：

- OpenAlex ✅（推荐）
- Semantic Scholar ✅
- Crossref ✅
- PubMed ✅
- arXiv ✅
- Google Scholar ✅（需 SerpAPI）
- Web of Science ⚠️（仅支持检索式，不支持自动抓取）

---

## 3.2 Processing Layer（处理层）

- 文献解析（RIS / BibTeX / CSV）
- 去重（基于标题 + DOI）
- 标准化结构
- 自动编号（#id）

输出：

```text
papers.jsonl
papers.ris
```

---

## 3.3 Analysis Layer（分析层）

- chunk 切分（token 控制）
- 分块 LLM 分析
- 证据引用强约束（#id）
- 覆盖率检查
- 全局综述生成

---

## 3.4 Output Layer（输出层）

生成：

- `review.md`（最终报告）
- `review.json`
- `papers.ris`
- `queries.txt`
- `logs/`

---

# 4. 技术选型

```text
Python >= 3.10
```

原因：

- 学术 API 生态成熟
- 文献处理工具丰富
- LLM 集成简单
- 易部署、易开源

---

# 5. 使用方法

## 5.1 环境准备

```bash
git clone https://github.com/zhangmai19/KAGAMI_REVIEW_TOOL.git
cd KAGAMI_REVIEW_TOOL

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

## 5.2 配置环境变量

复制示例文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
OPENAI_API_KEY=your_openai_key
SEMANTIC_SCHOLAR_API_KEY=your_key
SERPAPI_KEY=your_key
```

> ⚠️ 至少需要配置 `OPENAI_API_KEY`

---

## 5.3 运行（核心命令）

```bash
python main.py review-from-search \
  -t "topic of your research" \
  -k "keyword1" \
  -k "keyword2" \
  -d openalex \
  -d semantic_scholar \
  --max-papers 100 \
  --from-year 1980
```

---

### 参数说明

- `-t`：研究主题
- `-k`：关键词（支持多个）
- `-d`：数据源（支持多个）
- `--max-papers`：最大文献数
- `--from-year`：年份过滤

---

### 示例

```bash
python main.py review-from-search \
  -t "Large Language Models in Education" \
  -k "LLM" \
  -k "AI education" \
  -d openalex \
  -d semantic_scholar \
  --max-papers 80 \
  --from-year 2015
```

---

## 5.4 输出结果

```text
output/
├── review.md
├── review.json
├── papers.jsonl
├── papers.ris
├── queries.txt
└── logs/
```

---

## 5.5 其他入口

### Web UI

```bash
streamlit run ui/streamlit_app.py
```

### API 服务

```bash
uvicorn ui.api_server:app --reload
```

---

## 5.6 使用建议

- ✅ 推荐数据源：`openalex + semantic_scholar`
- ✅ 文献数量：50–100 篇最佳
- ✅ 多关键词提高召回率
- ✅ 查看 logs 进行审计

> ⚠️ 当前不支持 Web of Science 自动检索（仅支持 Query 生成）

---

# 6. License

MIT License

---

# 7. 贡献
IDEA: CYC
MODIFY&CODING: MAI

欢迎提交 Issue / PR 🚀
```

---
