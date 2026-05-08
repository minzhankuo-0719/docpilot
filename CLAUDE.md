# docpilot — 瑞鼎科技 take-home task

## 一、專案脈絡

- **應徵職務**：瑞鼎科技（Raydium）AI 應用程式開發工程師
- **應徵者**：minzhankuo（GitHub: `minzhankuo-0719`）
- **Repo**：`github.com/minzhankuo-0719/docpilot`
- **溝通語言**：繁體中文

## 二、原作業要求（信件原文）

> For this interview, please complete the take-home task(s) below by the day before your interview and share your deliverables.
> Please complete at least one task. Completing more than one is a plus.

### Task 1 — Unstructured Data Pipeline & Remote MCP Server

Build a data processing pipeline that ingests simulated, messy enterprise documents (e.g., a multi-page PDF containing tables/headers, and a PPTX slide deck). The script must extract, clean, and appropriately chunk the content. Next, package this searchable knowledge base into a remote Model Context Protocol (MCP) server. Expose specific tools or resources via the MCP server so that a standard LLM agent (e.g., Claude Desktop or a custom agent script) can connect and query the extracted information. Provide verifiable outputs (e.g., an MCP client test script, example queries, or server logs proving successful data retrieval).

### Task 2 — Data Preprocessing as Claude Skills

Package the unstructured data preprocessing capabilities (like parsing PDFs or PPTX files, cleaning text, and structured formatting) into reusable Skills. Ensure that these Skills have clear inputs/outputs, a safe execution boundary, and can be easily installed and invoked by Claude Code. Provide verifiable outputs (e.g., run logs, terminal screenshots, or a recorded demo showing Claude Code successfully executing the Skill). Skills reference (optional): https://kaochenlong.com/claude-code-skills

### Task 3 — Browser automation agent task （**本專案不做**）

### Requirements（硬性指標）

- **AI-only workflow**：Complete the work using AI coding tools or an agent workflow (Claude Code preferred). Using Skills is a plus.
- **Git evidence**：Provide a repo with meaningful commit history that reflects your process.
- **Deploy online**：Deploy to a public URL (e.g., Zeabur or equivalent).
- **Documentation**：Include a short README with how to run/verify, key assumptions, and how you used the AI/agent workflow.
- **No confidential material**：Use only public or self-created code/data.

## 三、已鎖定的決策

| 項目 | 決定 |
|---|---|
| 範圍 | 合併實作 **Task 1 + Task 2**，不做 Task 3 |
| 共用核心 | `packages/doc_preprocessor`（PDF/PPTX 解析、清洗、切塊） |
| 程式語言 | Python 3.11+ |
| 套件管理 | `uv` |
| PDF 解析 | `pymupdf` |
| PPTX 解析 | `python-pptx` |
| MCP framework | FastMCP（官方 Python SDK） |
| MCP transport | Streamable HTTP |
| 檢索策略 | Hybrid（BM25 + Voyage AI embedding），fallback 到純 BM25 |
| 部署平台 | **Render**（免費 tier，Docker 部署）|
| MCP 驗證 | Claude Desktop 連線 + 自製 test client 腳本 |

## 四、來源資料

- **PDF**：`/Users/kevin/Downloads/Papers/Attention Is All You Need.pdf` → commit 為 `data/raw/attention.pdf`
- **PPTX**：`/Users/kevin/Downloads/Attention_Is_All_You_Need_Presentation.pptx` → commit 為 `data/raw/attention_presentation.pptx`
  
## 五、階段計畫

| # | 階段 | 主要產出 | 驗證方式 |
|---|---|---|---|
| 0 | Repo 初始化 | 目錄結構、`pyproject.toml`、CLAUDE.md、README skeleton、`.gitignore`、GitHub remote | repo 公開可見 |
| 1 | `doc_preprocessor` library | PDF/PPTX parser、cleaner、chunker + 單元測試 | `pytest` 通過 |
| 2 | 索引建構 | chunks JSONL + BM25 索引 | `python scripts/build_index.py` |
| 3 | MCP Server | FastMCP tools：`search`、`get_chunk`、`list_documents` + test client | `python tests/mcp_client.py` 看到回傳 |
| 4 | Claude Skills | `parse-pdf`、`parse-pptx`、`clean-text`、`chunk-content` 共 4 個 skill | Claude Code 載入後可呼叫 |
| 5 | Zeabur 部署 | Dockerfile + 公開 URL | 主管打開 URL 能連到 MCP server |
| 6 | Demo + 文件收尾 | README 完整化、`docs/AI_WORKFLOW.md` 完整化 | 整體可重現 |

## 六、目錄結構

```
raydium-takehome/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── data/
│   ├── raw/
│   └── processed/
├── packages/
│   └── doc_preprocessor/
│       ├── __init__.py
│       ├── pdf.py
│       ├── pptx.py
│       ├── cleaner.py
│       └── chunker.py
├── apps/
│   └── mcp_server/
│       ├── server.py
│       ├── retrieval.py
│       └── Dockerfile
├── skills/
│   ├── parse-pdf/
│   ├── parse-pptx/
│   ├── clean-text/
│   └── chunk-content/
├── scripts/
│   └── build_index.py
├── tests/
│   ├── test_preprocessor.py
│   └── mcp_client.py
└── docs/
    └── AI_WORKFLOW.md
```

## 七、目前進度

| Stage | 狀態 | 產出與備注 |
|---|---|---|
| 0 — Repo 初始化 | ✅ 完成 | 目錄結構、`pyproject.toml`、`.gitignore`、GitHub remote |
| 1 — `doc_preprocessor` library | ✅ 完成 | v2：block-level parse + 段落感知 clean + sentence-aware chunk；`pytest` 通過 |
| 1.5 — `scripts/demo_pipeline.py` 視覺化驗證 | ✅ 完成 | `data/processed/query_results.md` 有輸出結果 |
| 2 — 索引建構 | ✅ 完成 | `data/processed/chunks.jsonl`、`bm25_index.pkl`、`bm25_corpus.pkl` 已產出；`scripts/build_index.py` 可重跑 |
| 3 — MCP Server | ✅ 完成 | `server.py` + `retrieval.py` 已驗證；`mcp_client.py` 5/5 通過；`Dockerfile` 已補齊 |
| 4 — Claude Skills | ✅ 完成 | `parse-pdf`、`parse-pptx`、`clean-text`、`chunk-content` 各含 `SKILL.md` + `scripts/run.py`；全部驗證通過；已安裝至 `~/.claude/skills/` |
| 5 — Render 部署 | 🔲 未開始 | `Dockerfile` 已備；`render.yaml` 已備；待連 GitHub 取得公開 URL |
| 6 — Demo + 文件收尾 | 🔲 未開始 | README 未完整；`docs/AI_WORKFLOW.md` 未補充 |

**doc_preprocessor v2 重點**：
- `Block` dataclass + `block_type ∈ {paragraph, caption, heading}`
- PDF 用 PyMuPDF `get_text("blocks")` 抓段落，regex 識別 figure/table caption
- PPTX 把 title placeholder 標為 `heading`
- `clean_text` 以 `\n\n` 為段落分隔保留語意；`clean_block_text` 處理單一 block
- `chunk_blocks` 讓 caption/heading 獨立成 chunk，paragraph 以 sentence boundary 切並做 sentence-level overlap
- 預處理結果：PDF 15 頁 → 484 blocks (9 captions) → 50 chunks；PPTX → 421 blocks (33 headings) → 68 chunks

**下一步**：Stage 5 — Zeabur 部署（Dockerfile 已備，需加 `zeabur.yaml` 並推上去）。

## 七之一、待修復 Bug

| # | 問題 | 現象 | 根本原因 | 預計解法 |
|---|---|---|---|---|
| B-01 | PDF 視覺化範例圖被解析為高分 chunk | Query 2/4/5 的 Rank 1-2 都是 `The Law will never be perfect...` 這串字元間有大量空白的噪音內容，佔據高位 | PDF 第 14-15 頁的翻譯視覺化圖內嵌大量重複文字，BM25 只看詞頻不懂語意，長 chunk 得分虛高 | 加入 Voyage AI embedding 做 hybrid search；或在 chunker 加噪音偵測過濾掉字元密度異常的 block |
| B-02 | Figure 內嵌 token 文字被當作正文解析 | PDF 圖片（如 Transformer 輸入示意圖）中每個 token 獨佔一行，被 PyMuPDF 抽取為大量單詞斷行的文字，混入正文 chunk，造成誤導性搜尋結果 | PyMuPDF `get_text("blocks")` 無法區分 figure 內文字與正文；圖片內的 token 以極小字型排列，每字自成一行 | 在 `pdf.py` 的 block 過濾階段，偵測「平均每行字數 < 3 且行數 > 10」的 block 標記為 `figure_text` 並於 chunking 前丟棄；或改用 `get_text("dict")` 以 font size 門檻過濾小字 |

## 八、協作慣例

- 每完成一個 stage 才 commit + push，commit message 要有意義
- 每次跑 Bash 指令前先用 1-2 句話說明在做什麼、為什麼現在跑
- 任何架構級決定先跟 minzhankuo 確認，不要自己改方向
- `docs/AI_WORKFLOW.md` 是作業靈魂，每個 stage 都要補充 AI 協作紀錄
