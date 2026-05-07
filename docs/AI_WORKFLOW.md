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

## Stage 1.5 — doc_preprocessor v2（語意感知重構）

**日期**：2026-05-07

### 問題回報

minzhankuo 跑完 `scripts/demo_pipeline.py` 後檢查輸出，提出 4 個品質問題：

1. **Cleaner 把段落結構壓平**：`re.sub(r"\n+", " ", text)` 會把所有換行（包含段落間的空行）通通變成空白，丟失段落語意。
2. **Chunker 純字數切**：完全不看段落、句子邊界，硬性 400 words/chunk。
3. **每頁只切 1~3 個 chunk，每個 chunk 過大**：Attention 論文每頁約 600~1000 words，配 400 words/chunk 結果單頁只有 1~3 個 chunk，對 retrieval 不利。
4. **Figure / Table caption 被混入內文**：PDF parser 用 `get_text("text")` 拿一坨 reading-order 文字，caption 跟前後段直接連在一起。

### 設計決策

Claude Code 先把問題對到具體檔案、行號，提出修法表後與 minzhankuo 確認方向 OK 再動手：

| 階段 | 改法 |
|---|---|
| **parse** | PDF 改用 `get_text("blocks")` 抓 paragraph block；新增 `Block` dataclass（`text` / `block_type` / `bbox`）；用 regex `^(Figure\|Fig\.?\|Table\|圖\|表)\s*\d+[:.：。]` 偵測 caption。`ParsedPage` / `ParsedSlide` 新增 `blocks: list[Block]`。 |
| **clean** | `clean_text` 改成段落感知：先以 `\n\n+` 切段落、各自清洗、再用 `\n\n` 接回。新增 `clean_block_text` 處理單一 block。 |
| **chunk** | 新增 `chunk_blocks(blocks, ...)`：caption / heading 獨立成 chunk（帶 `block_type` metadata）；paragraph 以 220 words 為上限打包；超大段落以 sentence boundary `[.!?。！？]` 拆；body chunk 之間以 sentence-level overlap 銜接；累積純 overlap 不會被當成 chunk flush 出去（用 `has_fresh` 旗標守住）。 |
| **demo_pipeline** | 把 parse / clean 兩階段都改成顯示 block 列表 + `block_type` badge，視覺上看得到 caption 被獨立辨識的差異。 |

### 介面相容性

- `parse_pdf` / `parse_pptx` / `clean_text` / `chunk_text` 名字保留，外部呼叫無需改。
- `chunk_text(chunk_size=, overlap=)` 語意微調：`overlap` 從 word-count 改為 sentence-count（預設 1）。

### 驗證

- `uv run pytest -v` → **35 passed** ✓（13 個新測試覆蓋 caption isolation、heading isolation、paragraph packing、oversize sentence split、cross-paragraph overlap）
- `uv run python scripts/demo_pipeline.py`：
  - PDF：15 頁 → **484 blocks（9 captions）→ 50 chunks**（41 paragraph + 9 caption）。和舊版每頁 1~3 chunk 對比，retrieval 粒度大幅提升。
  - PPTX：→ **421 blocks（33 headings）→ 68 chunks**（35 paragraph + 33 heading）。
  - 人工抽看第 3 頁 chunk #1：原本被混入的 "Figure 1: The Transformer ..." caption 已乾淨抽離；段落分隔（`3.1 Encoder...` / `Encoder: ...`）以 `\n\n` 保留；chunk #2 開頭的句子正是 chunk #1 的最後一句，sentence-level overlap 正確銜接。

### 關鍵決策

| 決策 | 理由 |
|---|---|
| caption 不和 body 同 chunk | retrieval 時可單獨命中圖表，且不會把無關描述塞進語意上不對的內文 chunk |
| sentence-level overlap（取代 word-level）| 保留語意完整句，避免 chunk 邊界切在半句 |
| `max_words=220`（從 400 降）| Attention 論文每頁 600~1000 words，220 words/chunk 換得每頁 3~5 chunks，對 BM25 + embedding retrieval 顆粒度合適 |
| `block_type` 寫入 `Chunk.metadata` | 後續 retrieval 可依 `block_type` 加權或過濾（例如「只查圖表」） |
| `Block` 帶 `bbox` | 之後若要做 layout-aware filtering（如過濾頁首頁尾）可直接用座標 |

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
