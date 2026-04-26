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
- ✅ **支持 TS 级布尔检索（本地实现）**

---

## ✨ 核心特性（重点升级）

- ✅ 多源文献检索（OpenAlex / Semantic Scholar / PubMed / arXiv 等）
- ✅ **OpenAlex 宽召回 + Python 布尔精筛（核心创新）**
- ✅ ✅ 支持 **TS 级布尔逻辑（AND / OR / 短语）**
- ✅ 自动关键词扩展（LLM）
- ✅ 文献去重 + 标准化编号（#1, #2, #3...）
- ✅ LLM 分块分析（支持 100+ 文献）
- ✅ 强制证据引用（防幻觉）
- ✅ 结果结构化输出（Markdown / JSON）
- ✅ 全流程日志记录（可审计）

---

# 🔥 2. 核心检索机制（重要）

本项目实现了一个关键升级：

## ✅ OpenAlex ≠ 布尔引擎 → 我们自己实现

### ✅ 实际策略：

```text
Step 1: OpenAlex 宽召回（关键词搜索）
Step 2: Python 本地布尔过滤（TS 逻辑）
```

---

## ✅ 布尔逻辑表示方式

```python
keyword_groups = [
    ["A1", "A2"],   # OR
    ["B1", "B2"],   # OR
    ["C1", "C2"],   # OR
]
```

语义：

```text
(A1 OR A2) AND (B1 OR B2) AND (C1 OR C2)
```

👉 ✅ 完全等价：

```
TS=((A) AND (B) AND (C))
```

---

## ✅ 为什么这样设计？

| 问题 | 解决 |
|------|------|
| OpenAlex 不支持 AND/OR | ✅ 本地实现 |
| API 检索能力有限 | ✅ 宽召回弥补 |
| 精度不足 | ✅ Python 精筛 |
| 不可控 | ✅ 完全可审计 |

---

## ✅ 一句话总结

```
OpenAlex 负责“多捞”
Python 负责“精筛”
```

---

# 3. 系统架构

## 3.1 工作流（升级版）

```text
用户输入 topic / keywords / keyword_groups
        ↓
关键词扩展（LLM，可选）
        ↓
构建 keyword_groups（布尔结构）
        ↓
生成宽召回 query
        ↓
多源检索（OpenAlex 等）
        ↓
布尔过滤（Python TS 逻辑 ✅）
        ↓
去重 + 标准化
        ↓
文献编号（#id）
        ↓
LLM 分析（严格基于摘要）
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
Query Layer（query/） ✅（新增 Boolean Builder）
    ↓
Retriever Layer（retriever/） ✅（支持 keyword_groups）
    ↓
Processing Layer（utils/ + parser/）
    ↓
Analysis Layer（analyzer/）
    ↓
Output Layer（output/）
```

---

# 4. 模块设计（关键更新）

## 4.1 Retriever Layer（检索层）

✅ 所有检索器统一支持：

```python
search(..., keyword_groups=None)
```

并实现：

```text
宽召回 → 本地布尔过滤
```

支持数据源：

- OpenAlex ✅（推荐）
- Semantic Scholar ✅
- Crossref ✅
- PubMed ✅
- arXiv ✅
- Google Scholar ✅（需 SerpAPI）

---

## 4.2 Query Layer（新增重点）

### ✅ BooleanQueryBuilder

支持：

- 构建 keyword_groups
- 构建宽召回 query
- LLM 自动扩展关键词

输出：

```python
{
    "keyword_groups": [...],
    "broad_query": "xxx xxx xxx"
}
```

---

## 4.3 Processing Layer（处理层）

- 文献解析（RIS / BibTeX / CSV）
- 去重（标题 + DOI）
- 标准化结构
- 自动编号（#id）

---

## 4.4 Analysis Layer（分析层）

- chunk 切分
- 分块分析
- 强制引用（#id）
- 覆盖率检查
- 全局综述生成

---

## 4.5 Output Layer（输出层）

生成：

```text
review.md
review.json
papers.jsonl
papers.ris
queries.txt
logs/
```

---

# 5. 使用方法（升级）

---

## ✅ 5.1 标准模式（自动扩展）

```bash
python main.py review-from-search \
  -t "AI in healthcare" \
  -k "machine learning" \
  -k "diagnosis" \
  -d openalex
```

👉 LLM 自动生成：

- keyword_groups ✅
- 宽召回 query ✅

---

## ✅ 5.2 高级模式（手动布尔控制 ⭐推荐）

```bash
python main.py review-from-search \
  -t "Insurance risk" \
  -g "reinsurance,risk transfer,cat bond" \
  -g "mutual insurance,insurtech,blockchain insurance" \
  -g "risk sharing,risk pooling" \
  -d openalex -d semantic_scholar
```

---

### ✅ 等价 WoS：

```text
TS=((reinsurance OR "risk transfer" OR "cat bond")
 AND ("mutual insurance" OR insurtech OR "blockchain insurance")
 AND ("risk sharing" OR "risk pooling"))
```

---

## ✅ 参数说明（更新）

- `-t`：研究主题
- `-k`：关键词（用于 LLM 扩展）
- `-g`：关键词组（逗号分隔 OR，多组 AND ✅）
- `-d`：数据源
- `--max-papers`
- `--from-year`

---

# 6. 使用建议（重要）

- ✅ 推荐：`openalex + semantic_scholar`
- ✅ 使用 `-g` 控制精度（代替传统布尔检索）
- ✅ 文献量建议：50–150
- ✅ 优先使用短语（如 "risk sharing"）

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