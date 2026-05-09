# docpilot

Raydium AI 應用工程師 take-home task — Task 1 (MCP Server) + Task 2 (Claude Skills)。

## 專案簡介

以「Attention Is All You Need」論文 PDF 與簡報 PPTX 為原始資料，建構：

1. **文件預處理 pipeline**：解析 → 清洗 → 切塊 → 索引（BM25 + Voyage AI embedding）
2. **遠端 MCP Server**：透過 FastMCP 暴露 `search`、`get_chunk`、`list_documents` 工具，供 LLM agent 查詢
3. **Claude Skills**：將預處理能力封裝為可安裝的 Skills（`parse-pdf`、`parse-pptx`、`clean-text`、`chunk-content`）

## 快速開始

```bash
# 安裝依賴（需要 uv）
uv sync
```

## 視覺化 Pipeline 輸出（推薦先從這裡開始）

執行以下指令，會依序跑完 parse → clean → chunk，並將每個階段的結果寫成 Markdown 檔案到 `data/processed/demo/`：

```bash
uv run python scripts/demo_pipeline.py
```

產生的檔案：

| 檔案 | 內容 |
|---|---|
| `data/processed/demo/parse_pdf.md` | PDF 每頁的 **Block 列表**，每個 block 標註 `paragraph` / `caption` / `heading` |
| `data/processed/demo/parse_pptx.md` | PPTX 每張投影片的 Block 列表（含 title heading 識別）|
| `data/processed/demo/clean_pdf.md` | 段落感知清洗結果（每個 block 獨立清洗，段落界線保留）|
| `data/processed/demo/clean_pptx.md` | PPTX 清洗結果 |
| `data/processed/demo/chunks_pdf.md` | PDF 切塊結果（max 220 words，overlap 1 sentence；caption 獨立成 chunk）|
| `data/processed/demo/chunks_pptx.md` | PPTX 切塊結果 |

### 預處理 pipeline 設計重點

- **Block-level parsing**：PDF 用 PyMuPDF `get_text("blocks")` 抓 paragraph block；PPTX 用每個 `text_frame.paragraphs` 當 block。每個 block 帶 `block_type`，並用 regex `^(Figure|Fig\.?|Table|圖|表)\s*\d+[:.]` 識別 caption。
- **段落感知清洗**：`clean_text` 以 `\n\n` 切段落、各自清洗、再組回去。Block 內的行內換行 → 空白；段落界線保留。
- **語意切塊**：caption / heading **獨立成 chunk**（不會被混入內文）；paragraph 依字數打包；超大段落以 sentence boundary `[.!?。！？]` 拆分；body chunk 之間以 sentence-level overlap 銜接。

## Claude Skills（Task 2）

四個 skill 封裝了文件預處理各階段的能力，可在 Claude Code 中直接呼叫。

| Skill | 功能 | 預設輸出路徑 |
|---|---|---|
| `parse-pdf` | 解析 PDF → 結構化 blocks JSON | `data/processed/<stem>_parsed.json` |
| `parse-pptx` | 解析 PPTX → 結構化 blocks JSON | `data/processed/<stem>_parsed.json` |
| `clean-text` | 清洗原始文字（修復 soft-hyphen、換行等） | `data/processed/<stem>_cleaned.txt` |
| `chunk-content` | 切塊供 RAG 使用（含 sentence-level overlap） | `data/processed/<doc-id>_chunks.json` |

### 安裝 Skills

```bash
# 從專案根目錄執行，複製四個 skill 到 Claude Code 的 skills 目錄
cp -r skills/parse-pdf   ~/.claude/skills/
cp -r skills/parse-pptx  ~/.claude/skills/
cp -r skills/clean-text  ~/.claude/skills/
cp -r skills/chunk-content ~/.claude/skills/
```

安裝後在 Claude Code 對話中即可直接呼叫，例如：

> 「幫我解析 data/raw/transformer.pdf」

結果會自動寫入 `data/processed/transformer_parsed.json`，並顯示：

```
Output saved to: /your/project/data/processed/transformer_parsed.json
```

如需自訂輸出路徑，加上 `--output` 參數：

```bash
uv run python skills/parse-pdf/scripts/run.py data/raw/transformer.pdf --output my_output.json
```

## 執行單元測試

```bash
uv run pytest
```

35 個測試涵蓋 cleaner / chunker / chunk_blocks / parse_pdf / parse_pptx，包含 caption isolation、paragraph preservation、sentence overlap 等行為驗證。

## 建構索引與啟動 MCP Server

```bash
# 建構索引
uv run python scripts/build_index.py

# 啟動 MCP Server
uv run python apps/mcp_server/server.py
```

## 驗證 MCP Server

```bash
# 本機測試
uv run python tests/mcp_client.py

# 遠端測試（Render）
uv run python tests/mcp_client.py --url "https://docpilot-5hht.onrender.com/mcp"
```

## 主要假設

- 使用 `pymupdf` 解析 PDF（速度快、對學術論文表格支援佳）
- 使用 `python-pptx` 解析 PPTX（逐 slide 提取文字與備註）
- 混合檢索（BM25 + Voyage AI）；若未設定 `VOYAGE_API_KEY` 則 fallback 到純 BM25
- MCP transport 使用 Streamable HTTP，部署於 Render（免費 tier）
- **Render 部署採純 BM25**：embeddings 檔案（`embeddings.npy` / `embedding_ids.json`）為本機重建後產生且未 commit（被 `.gitignore` 排除）；遠端容器啟動時 `VOYAGE_API_KEY` 也未注入，因此 `KnowledgeBase` 會自動 fallback 到純 BM25。本機如需驗證 hybrid，請設定 `VOYAGE_API_KEY` 後重跑 `build_index.py`。

## 已知限制

- **B-01**：PDF 第 14–15 頁的視覺化範例圖內嵌大量重複文字（如 `The Law will never be perfect ...`），BM25 純詞頻計分會把這些噪音 chunk 排到高位。緩解方案是 hybrid search（embedding 對語意敏感），但目前遠端僅有 BM25，因此這個 retrieval bias 仍存在。本機啟用 Voyage embedding 後可顯著降低其影響。

## AI 協作工作流程

詳見 [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md)。

## 部署

**Public MCP Server**（Render）：https://docpilot-5hht.onrender.com

- 部署平台：Render（免費 tier，auto-scale down 後有 ~30s 冷啟動）
- 連線測試：見上方「驗證 MCP Server」章節
- Claude Desktop：透過 `mcp-remote` 橋接連線此遠端 server，設定方式見 [DEMO.md](DEMO.md) Step 3

## 目錄結構

```
raydium-takehome/
├── data/raw/               原始文件（PDF、PPTX）
├── data/processed/         切塊後的 JSONL 與索引
├── packages/doc_preprocessor/  核心解析 library
├── apps/mcp_server/        FastMCP 伺服器
├── skills/                 Claude Code Skills
├── scripts/                索引建構腳本
├── tests/                  單元測試 + MCP client 測試
└── docs/                   工作流程文件
```
