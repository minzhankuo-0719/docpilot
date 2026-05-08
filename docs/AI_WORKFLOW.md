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

**日期**：2026-05-07

### 協作過程

1. **需求確認**：minzhankuo 要求建構可檢索的索引。Claude Code 確認檢索策略（§ 三）為 hybrid（BM25 + Voyage AI embedding），fallback 到純 BM25。

2. **索引設計**：Claude Code 規劃 `scripts/build_index.py`，流程為：
   - 載入兩份源檔（PDF + PPTX）
   - parse → clean → chunk_blocks
   - 將每個 chunk 與 metadata（chunk_id、doc_id、page_or_slide、block_type）輸出至 JSONL
   - 同時建構 BM25 索引（逐 chunk 的 text 作為 corpus）並序列化為 pickle
   - 若設定 `VOYAGE_API_KEY`，逐 chunk embedding 後儲存向量

3. **Hybrid retrieval**：`retrieval.py` 實作 `KnowledgeBase` class，負責：
   - `load()`：讀 JSONL + BM25 pickle，optional 載入 Voyage embedding
   - `search(query, top_k)`：優先執行 hybrid search（BM25 score + Voyage similarity），分值加權後排序；若無 embedding，fallback 到純 BM25
   - `get_chunk(chunk_id)` / `list_documents()`：查詢介面

4. **輸出驗證**：
   - `data/processed/chunks.jsonl`：118 chunks（50 from PDF + 68 from PPTX）
   - `data/processed/bm25_index.pkl` + `bm25_corpus.pkl`：BM25 模型
   - `uv run python scripts/build_index.py` 可重建，支援冪等性

### 關鍵決策

| 決策 | 理由 |
|---|---|
| JSONL 格式存 chunks | 輕量、行式流讀、易於 streaming / debugging |
| pickle 序列化 BM25 | BM25 初始化時間 O(n)，序列化避免每次重建 |
| Voyage embedding 選用 | 強大語義理解，補足 BM25 詞頻盲點；但加 fallback，確保無 API key 也能用 |

### 驗證

- `uv run python scripts/build_index.py` 完成 ✓
- `data/processed/` 產生 chunks.jsonl 及兩個 pickle 檔 ✓
- Demo query：`"attention mechanism"` 返回高分 chunks（PDF p7、PPTX p6）✓

---

## Stage 3 — MCP Server

**日期**：2026-05-07

### 協作過程

1. **需求確認**：minzhankuo 要求建構 MCP server，需暴露搜尋、取文、列文件三項工具，並用 Streamable HTTP transport 供遠端連線。

2. **FastMCP 搭建**：Claude Code 用官方 FastMCP SDK 建構 `apps/mcp_server/server.py`：
   - `@asynccontextmanager lifespan`：startup 時 `kb.load()` 一次索引（單例，避免重複載入）
   - `@mcp.tool` 裝飾器定義三個工具：
     - `search(query, top_k=5)`：hybrid 檢索，返回 top-k 結果
     - `get_chunk(chunk_id)`：單一 chunk 查詢
     - `list_documents()`：列出已索引的文檔
   - Streamable HTTP transport：`mcp.run(transport="streamable-http")`

3. **本機測試**：`tests/mcp_client.py` 驗證 5 個測試用例：
   - list_tools：確認三個工具存在 ✓
   - list_documents：回傳 2 份文檔、118 chunks ✓
   - search 查詢：`"attention mechanism"` 返回相關 chunks ✓
   - get_chunk：單一 chunk 查詢 ✓
   - get_chunk（unknown id）：null handling ✓

4. **Docker 打包**：`Dockerfile` 配置：
   - Python 3.11 slim base
   - `uv pip install` 快速安裝依賴
   - 複製 chunks + pickle 至容器
   - `CMD python apps/mcp_server/server.py` 啟動

### 關鍵決策

| 決策 | 理由 |
|---|---|
| Streamable HTTP（vs stdio） | production-grade transport，支持並發、健康檢查、可遠端連線 |
| 單例索引（lifespan）| 避免每個請求重新載入索引（IO overhead）；FastMCP 原生支持 |
| 環境變數讀 HOST/PORT | Render 自動注入 PORT，伺服器部署無需改代碼 |

### 驗證

- `cd apps/mcp_server && uv run python server.py`：本機啟動 ✓
- `uv run python tests/mcp_client.py`：5/5 測試通過 ✓

---

## Stage 4 — Claude Skills

**日期**：2026-05-07

### 協作過程

1. **需求確認**：minzhankuo 要求把 `doc_preprocessor` 功能（parse、clean、chunk）封裝為 Claude Skills，供 Claude Code 安裝並複用。

2. **Skill 結構設計**：Claude Code 為四個 Skill 建立統一目錄結構：
   ```
   skills/{skill-name}/
   ├── SKILL.md           # Skill 定義、輸入/輸出規格
   ├── scripts/run.py     # 可執行腳本
   └── packages/          # 依賴的 Python 模組（symlink 到 ../../packages/）
   ```

3. **各 Skill 實作**：
   - `parse-pdf`：讀 PDF，輸出 Block JSON（text / block_type）
   - `parse-pptx`：讀 PPTX，輸出 Block JSON
   - `clean-text`：輸入文字，輸出段落感知清洗後的文字
   - `chunk-content`：輸入 Block JSON 或文字，輸出切塊後的 Chunk JSON

4. **安裝與驗證**：Claude Code 執行 `~/.claude/skills/install.sh`（或手動 symlink）將四個 Skills 連結到 `~/.claude/skills/`，確認 Claude Code CLI 可呼叫。

### 關鍵決策

| 決策 | 理由 |
|---|---|
| JSON 輸入/輸出 | 結構化、易於下游處理 |
| Block 結構一致 | parse 與 chunk 都以 Block dataclass 為中樞，銜接無縫 |
| 相對 symlink 依賴 | 避免複製代碼，保持單一真理來源 |

### 驗證

- `uv run python skills/parse-pdf/scripts/run.py --input data/raw/attention.pdf` ✓
- `uv run python skills/clean-text/scripts/run.py --input <text>` ✓
- 四個 Skills 均已安裝至 `~/.claude/skills/` ✓

---

## Stage 5 — Render 部署

**日期**：2026-05-08

### 協作過程

1. **平台選擇**：minzhankuo 原計畫用 Zeabur，但發現 Zeabur 需要購買伺服器。Claude Code 建議改用 **Render**（免費 tier）替代方案，優勢：
   - 完全免費（hobby plan）
   - 支持 Docker 直接部署
   - GitHub 連動部署（push 即 build）
   - 公開 URL（`https://docpilot-5hht.onrender.com`）

2. **設定修改**：
   - 移除 `zeabur.yaml`，新增 `render.yaml`（Render Blueprint）
   - 更新 CLAUDE.md，記錄部署平台變更

3. **部署流程**：minzhankuo 登入 Render → 以 GitHub 連動 → Render 自動偵測 `render.yaml` → free tier Docker build 並啟動
   - Build 輸出：Uvicorn 在 `0.0.0.0:10000` 啟動（PORT 由 Render 自動注入）
   - 公開 URL：https://docpilot-5hht.onrender.com

4. **遠端測試**：
   ```bash
   uv run python tests/mcp_client.py --url "https://docpilot-5hht.onrender.com/mcp"
   ```
   結果：5/5 測試通過 ✓

### 關鍵決策

| 決策 | 理由 |
|---|---|
| Render（非 Zeabur） | 免費 tier 夠用，無需付費；GitHub 原生支持 |
| free tier 可接受的冷啟動 | 面試場景內，~30s 冷啟動可接納；對標 fallback-only 的安全邊界 |

### 驗證

- Render build log：`Application startup complete` ✓
- 遠端 MCP client 測試：5/5 通過 ✓
- 公開 URL 可訪問 ✓

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

**日期**：2026-05-08

### 協作過程

1. **文件補完**：Claude Code 補充 README.md 與 docs/AI_WORKFLOW.md：
   - README：加入公開 URL、遠端測試指令、部署平台註記
   - AI_WORKFLOW：補充 Stage 2–5 完整協作紀錄，每個 stage 涵蓋問題、決策、驗證

2. **最終提交**：所有修改 commit + push，repo 完整可重現。

### 關鍵成果

| 項 | 產出 |
|---|---|
| 公開 repo | github.com/minzhankuo-0719/docpilot（main 分支） |
| MCP Server 公開 URL | https://docpilot-5hht.onrender.com（可直接連線） |
| 完整文檔 | README + docs/AI_WORKFLOW.md（每 stage 都有 AI 協作紀錄） |
| 可重現性 | `uv sync` + `uv run pytest` + `uv run python scripts/build_index.py` + `uv run python apps/mcp_server/server.py` 完整可執行 |
| AI workflow 佐證 | 本文件詳細記錄每個 stage 中 AI 與人類的協作過程、決策理由、驗證方式 |

### AI 協作總結

**工作流模式**：
1. **需求讀取** → 確認目標、檢查依賴、詢問決策（如有歧義）
2. **分解任務** → 拆成可驗證的子步驟，先淺談再深入
3. **漸進實作** → 每步都驗證，問題立即浮現、即時修正
4. **文件追蹤** → 本文件是「ai workflow 證據」，協作意圖清晰可查

**Claude Code 角色**：
- 需求確認：讀 CLAUDE.md、跟 minzhankuo 確認方向
- 代碼撰寫：編寫核心邏輯（parser / chunker / MCP server）
- 問題診斷：遇到 soft-hyphen、caption isolation 等問題時，精準指出根因
- 架構決策：提出 block-level parsing、sentence-aware chunking、hybrid retrieval 等設計
- 部署優化：建議免費方案（Render）替代付費方案（Zeabur）

**minzhankuo 角色**：
- 方向把關：批准架構決策、提出修復需求
- 品質檢驗：跑 demo、看輸出，發現語意問題並反饋
- 執行决策：登入 Render、部署、驗證 URL

**協作成效**：
- 4 個工作日內完成 6 個 stage，產出可公開演示的 take-home task
- 每個 stage 都有明確的驗證（pytest / 視覺檢查 / 遠端測試）
- 最終交付物包含源碼 + 公開 URL + 完整文檔
