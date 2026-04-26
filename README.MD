# KAGAMI_REVIEW_TOOL

> 一个可开源、可扩展、可审计的学术文献综述 Agent  
> 输入：研究主题 + 关键词 / 布尔关键词组  
> 输出：严格基于摘要、带 `#id` 证据引用的结构化综述报告

---

# 1. 项目介绍

KAGAMI_REVIEW_TOOL 是一个自动化学术综述系统，面向科研人员与开发者，支持从多源数据库检索文献，并基于 LLM 生成**可追溯、结构化、可审计**的综述报告。

与传统“生成式综述”不同，本项目强调：

- ✅ **只基于摘要内容**
- ✅ **所有结论必须带 `#id` 引用**
- ✅ **全流程可复现 + 可审计**
- ✅ **支持布尔关键词组（AND / OR）本地过滤**

---

## ✨ 核心特性

- ✅ 多源文献检索（OpenAlex / Semantic Scholar / PubMed / arXiv 等）
- ✅ OpenAlex 宽召回 + Python 本地布尔过滤
- ✅ 支持关键词组布尔逻辑（AND / OR）
- ✅ 自动关键词扩展（LLM）
- ✅ 文献去重 + 标准化编号（#1, #2, #3...）
- ✅ LLM 分块分析（支持 100+ 文献）
- ✅ 强制证据引用（防幻觉）
- ✅ 结果结构化输出（Markdown / JSON）
- ✅ 全流程日志记录（可审计）

---

# 2. 核心检索机制

## ✅ 检索策略

```text
Step 1: 多源 API 宽召回（关键词搜索）
Step 2: Python 本地布尔过滤（keyword_groups）
```

---

## ✅ 布尔逻辑表示

```python
keyword_groups = [
    ["A1", "A2"],
    ["B1", "B2"],
]
```

语义：

```text
(A1 OR A2) AND (B1 OR B2)
```

---

## ✅ 设计原因

- API（如 OpenAlex）不支持复杂布尔逻辑  
- 宽召回提高 recall  
- 本地过滤保证 precision  
- 全流程可审计  

---

# 3. 系统架构

## 3.1 工作流

```text
用户输入 topic / keywords / keyword_groups
        ↓
关键词扩展（LLM，可选）
        ↓
构建 keyword_groups
        ↓
多源检索（OpenAlex 等）
        ↓
本地布尔过滤 ✅
        ↓
去重 + 标准化
        ↓
文献编号（#id）
        ↓
LLM 分块分析
        ↓
综述生成 + 引用对齐
```

---

## 3.2 架构分层

```text
User Input
    ↓
Agent Orchestrator（agents/）
    ↓
Query Layer（query/）
    ↓
Retriever Layer（retriever/）
    ↓
Processing Layer（utils/ + parser/）
    ↓
Analysis Layer（analyzer/）
    ↓
Output Layer（output/）
```

---

# 4. 模块设计

## 4.1 Retriever Layer

统一接口：

```python
search(..., keyword_groups=None)
```

支持：

- OpenAlex ✅
- Semantic Scholar ✅
- Crossref ✅
- PubMed ✅
- arXiv ✅
- Google Scholar ✅（需 SerpAPI）

---

## 4.2 Processing Layer

- RIS / BibTeX / CSV 解析  
- 去重（标题 + DOI）  
- 标准化  
- 自动编号（#id）

---

## 4.3 Analysis Layer

- chunk 切分  
- 分块分析  
- 强制引用（#id）  
- 覆盖率计算  
- 全局综述生成  

---

## 4.4 Output Layer

```text
review.md
review.json
papers.jsonl
papers.ris
queries.txt
logs/
```

---

# 5. 使用方法

---

## ✅ 5.1 搜索模式（推荐）

```bash
python main.py review-from-search \
  -t "p2p insurance in heterogeneous types" \
  -g "p2p insurance" \
  -g "risk sharing" \
  -d openalex \
  -m gpt-5.1-instant \
  --report-model Claude-Opus-4.7
```

---

## ✅ 参数说明（与 main.py 对齐）

- `-t, --topic`：研究主题  
- `-k, --keyword`：关键词（可多个，用于扩展）  
- `-g, --keyword-group`：关键词组（逗号分隔 OR，多组 AND ✅）  
- `-d, --database`：数据源（可多个）  
- `--max-papers`：最大检索文献数  
- `--from-year` / `--to-year`：年份过滤  

### ✅ 模型参数

- `-m, --model`：  
  👉 用于：
  - 关键词扩展  
  - 分块分析  

- `-r, --report-model`：  
  👉 用于：
  - 最终综述生成（建议更强模型）

---

## ✅ 5.2 文件输入模式

支持：

```bash
review-from-ris
review-from-bib
review-from-csv
```

---

# 6. 使用建议

- ✅ 推荐数据源：`openalex + semantic_scholar`  
- ✅ 使用 `-g` 控制精度（比 keyword 更稳定）  
- ✅ 文献数量：50–150  
- ✅ 使用短语关键词（如 `"risk sharing"`）  

---

# 7. 技术选型

```text
Python >= 3.10
```

---

# 8. 输出示例

```text
# Finding 1: Risk Sharing Mechanisms

Reinsurance improves capital efficiency (#3, #12)
Mutual insurance enhances pooling (#7, #15)
```

---

# 9. License

MIT License

---

# 10. 贡献

IDEA: CYC  
MODIFY & CODING: MAI  

欢迎提交 Issue / PR 🚀
```