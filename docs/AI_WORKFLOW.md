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

**日期**：2026-05-07

### 協作過程

1. **需求確認**：minzhankuo 要求繼續 Stage 1，並希望將來源資料（PDF/PPTX）直接 commit 進 repo 作為測試用檔案。Claude Code 從 CLAUDE.md § 四確認來源路徑後執行複製。

2. **模組設計**：Claude Code 提出四個模組的職責切分：
   - `pdf.py`：用 PyMuPDF (`fitz`) 逐頁提取文字，回傳 `ParsedPage` dataclass 列表。
   - `pptx.py`：用 python-pptx 遍歷 `shapes`，彙整每張投影片的文字段落，回傳 `ParsedSlide` 列表。
   - `cleaner.py`：純函數 `clean_text()`，處理 PDF soft-hyphen 斷行、多餘換行、控制字元、unicode 正規化。
   - `chunker.py`：依照字數（預設 400 words、50 words overlap）切塊，回傳帶 `chunk_id`（sha256 truncated）的 `Chunk` dataclass。
   - `__init__.py`：re-export 公開 API。

3. **測試撰寫**：共 22 個測試，分為 unit（cleaner、chunker 純邏輯）與 integration（pdf/pptx，條件式 skip）兩層，確保 CI 環境即使沒有資料檔也能跑 unit tests。

4. **Import 問題排除**：初始測試用 `from packages.doc_preprocessor import ...` 導致 `ModuleNotFoundError`，因為 hatchling 把 `packages/doc_preprocessor` 打包成 `doc_preprocessor`（不帶前綴）。Claude Code 修正 import 後測試全過。

5. **pytest 結果**：`22 passed` ✓

### 關鍵決策

| 決策 | 理由 |
|---|---|
| word-count chunking（非 token-count） | 無需額外 tokenizer 依賴，對 BM25 友好 |
| `chunk_id` 用 `sha256(doc_id:page:idx)[:16]` | 確定性 ID，相同輸入永遠得到相同 ID，方便去重 |
| PDF/PPTX 原始檔直接 commit 進 `data/raw/` | 讓測試可重現，檔案為論文公開資料（Attention Is All You Need） |

### 驗證

- `uv run pytest tests/test_preprocessor.py -v` → 22 passed ✓
- PDF 解析：`attention.pdf` 有 15 頁，每頁均有文字 ✓
- PPTX 解析：`attention_presentation.pptx` 多張投影片均抽出文字 ✓

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
