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

# 建構索引
uv run python scripts/build_index.py

# 啟動 MCP Server
uv run python apps/mcp_server/server.py

# 執行測試
uv run pytest
```

## 驗證 MCP Server

```bash
uv run python tests/mcp_client.py
```

## 主要假設

- 使用 `pymupdf` 解析 PDF（速度快、對學術論文表格支援佳）
- 使用 `python-pptx` 解析 PPTX（逐 slide 提取文字與備註）
- 混合檢索（BM25 + Voyage AI）；若未設定 `VOYAGE_API_KEY` 則 fallback 到純 BM25
- MCP transport 使用 Streamable HTTP，部署於 Zeabur

## AI 協作工作流程

詳見 [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md)。

## 部署

Public URL（Zeabur）：*待補充*

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
