# AI 協作工作流程紀錄

本文件記錄每個 stage 中 AI（Claude Code）與開發者（minzhankuo）的協作過程，作為 take-home task 的 AI workflow 佐證。

---

## Stage 0 — Repo 初始化

**日期**：2026-05-07

### 協作過程

1. **需求確認**：minzhankuo 提供 CLAUDE.md，明確列出專案目標、技術決策、目錄結構與 stage 計畫。Claude Code 在開始動手前先讀取 CLAUDE.md 確認方向。

2. **目錄結構建立**：Claude Code 依照 CLAUDE.md § 六的規格，以單一 `mkdir -p` 指令建立完整目錄樹，並用 `touch` 建立 placeholder 檔案（git 不追蹤空目錄，故 leaf 目錄放 `.gitkeep`）。

3. **pyproject.toml**：Claude Code 依照已鎖定決策（§ 三）填入套件版本下限：
   - `pymupdf>=1.24.0`、`python-pptx>=0.6.23`（文件解析）
   - `mcp[cli]>=1.0.0`（FastMCP，官方 Python SDK）
   - `rank-bm25>=0.2.2`、`voyageai>=0.2.0`（混合檢索）
   - `httpx`、`python-dotenv`（HTTP client、環境變數）
   - dev extras：`pytest`、`pytest-asyncio`、`ruff`

4. **README.md**：寫入執行指令、主要假設、目錄說明的 skeleton；公開 URL 欄位留白，待 Stage 5 部署後補充。

5. **\.gitignore**：涵蓋 Python bytecode、uv venv、`.env`、IDE 設定、`data/processed/`（可由 script 重建，不 commit）、Claude Code local settings。

6. **Git 初始化與 push**：`git init` → 加入所有檔案 → 第一次 commit → 在 GitHub 建立 `docpilot` public repo → push。

### 關鍵決策

| 決策 | 理由 |
|---|---|
| `data/processed/` 加入 `.gitignore` | 索引由 script 重建，不應 commit 大型 binary |
| `uv.lock` 加入 `.gitignore` | lock file 由 `uv sync` 自動產生，CI 環境重建即可 |
| `.claude/settings.local.json` 加入 `.gitignore` | 本機個人設定，不應進 repo |

### 驗證

- `gh repo view minzhankuo-0719/docpilot` 回傳 repo 資訊 ✓
- 目錄結構符合 CLAUDE.md § 六規格 ✓

---

## Stage 1 — doc_preprocessor library

*待補充*

---

## Stage 2 — 索引建構

*待補充*

---

## Stage 3 — MCP Server

*待補充*

---

## Stage 4 — Claude Skills

*待補充*

---

## Stage 5 — Zeabur 部署

*待補充*

---

## Stage 6 — Demo + 文件收尾

*待補充*
