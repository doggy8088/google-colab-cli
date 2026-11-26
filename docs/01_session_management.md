---
log:
2026-11-23：`colab stop -s <name>` 現在會在指定的工作階段不存在（或已從後端消失）時以 1 結束，將缺失工作階段的處理交給 `State.get_session`（#251）。
2026-11-13：在全域旗標下記錄了 `--auth {oauth2,adc}`（預設 `oauth2`）與 ADC 所需的 `gcloud` 範圍。
2026-11-04：`--gpu` 與 `--tpu` 現在會拒絕未知值，而不是默默選擇 `A100`（GPU）或 `v6e1`（TPU）。`resolve_runtime_options()` 使用新的 `GPU_ACCELERATORS` / `TPU_ACCELERATORS` 對映，並拋出指出旗標與支援清單的 `typer.BadParameter`；`--help` 由相同的對映產生，因此不會漂移。驗證在任何配置請求之前執行，在 `colab new` 與 `colab run` 中皆然。
2026-11-02：在 `auth.py` 新增 `_check_linux_keyring_locked`，在讀取或寫入 OAuth 權杖之前，透過 `secretstorage` 檢查作用中的 Linux `SecretService` 金鑰圈集合是否已鎖定，記錄並立即印出帶有集合標籤、逾時與 `--auth=adc` 提示的警告，同時仍嘗試金鑰圈操作。
2026-10-29：移除了 `colab console` 子指令；現在會略過工作階段中途權杖刷新的長壽命連線是 `repl` 與 `ssh`。
2026-10-29：偵錯日誌（`colab.log` 與 `--logtostderr`）會遮罩存取權杖、執行期代理權杖、OAuth 代碼、用戶端密鑰、驗證標頭與 cookies，包括在百分比編碼的 URL 中；`jupyter_kernel_client` 以 INFO 記錄，因此核心 stdin 回覆不會被記錄。
2026-10-29：`sessions.json`、`settings.json`、`colab.log` 與工作階段歷史檔案以 0600 模式建立，既有副本會在 CLI 下次使用它們時收緊為 0600（歷史檔案則在歷史記錄器每次啟動時）。
2026-10-22：新增全域 `--public-api/--no-public-api` 切換（`COLAB_CLI_PUBLIC_API`、`Settings.use_public_api`，預設 `False`）、雙路徑 `Client.list_assignments()` 分派（`/v1beta/runtimes` 與 `/tun/m/assignments`）、`Operation`/`Status` 模型，以及在 HTTP 401/403 時快取的驗證能力提示。
2026-10-21：透過 `keyring` 函式庫將 OAuth2 憑證儲存在 OS 原生金鑰圈中，而不是 `~/.config/colab-cli/token.json`，在金鑰圈無法存取時退回 `_run_remote_flow`。金鑰圈失敗會回報在 stderr 上，既有的 `token.json` 會遷移進入金鑰圈然後刪除（或在金鑰圈已有權杖時直接刪除）。
2026-10-14：新增可設定的 HTTP 請求逾時與有界的配置重試。不確定的配置 POST 會在重新提交之前，以相同的筆記本雜湊透過 GET 對帳。
2026-09-25：執行期代理權杖現在會在過期前刷新。`SessionState` 持久化 `token_expires_at`，`State.get_session` 會在權杖距離過期 5 分鐘以內時，透過 `GET /tun/m/assignments` 重新取得權杖。
2026-09-25：移除了 keep-alive 背景守護行程與相關的用戶端/CLI ping 函式。虛擬機器存活由 Colab 後端依核心活動自動維持。
2026-08-10：透過工作階段後端上的 `GET /tun/m/ccu-info`（與 `colab new` 相同的 bearer 權杖），新增用於帳戶層級運算單位速率／餘額的 `colab usage`。
2026-08-09：在 `colab new`、`colab run` 與 `colab ssh`（自動建立）新增 `--high-mem`。要求高 RAM 時，配置請求現在會送出 `shape=hm`；`colab sessions` 與 `colab status` 會顯示機器規格。
2026-06-15：將 keep-alive 守護行程從 `colab.pa.googleapis.com` 的 `RuntimeService/KeepAliveAssignment` RPC 切換為 `colab.research.google.com` 上的 Tunnel Frontend HTTP ping（帶 `X-Colab-Tunnel: Google` 的 `GET /tun/m/<endpoint>/keep-alive/`）。該 RPC 需要對 Colab 內部專案 `1014160490159` 的 `serviceusage` 消費者存取權，一般使用者帳戶沒有，因此每個外部使用者都遇到 HTTP 403 `USER_PROJECT_DENIED`，其 CLI 工作階段在幾分鐘內就被閒置修剪（issue #14）。已用第三方帳戶真實重現；驗證通道 ping 被與 `assign` 已能運作的相同 bearer 權杖憑證接受。ping 的 `ReadTimeout` 視為成功（TFE 在轉發給通常不回應的虛擬機器之前就記錄活動）。將預檢修復訊息從現在已無關的 `colaboratory`/`pa.googleapis.com` 框架一般化，並移除已死的 grpc-web 用戶端登錄/API 金鑰程式碼。
2026-06-10：將 `_LockedFileStore` 中僅限 POSIX 的 `fcntl.flock` 檔案鎖定換成跨平台的 `filelock` 函式庫（在 Windows 上回報損壞）。讀取使用 `ReadWriteLock.read_lock()`（共享），寫入使用 `write_lock()`（獨占），保留原本的 `LOCK_SH`/`LOCK_EX` 語意。此鎖以 `is_singleton=False` 建構，因此同一程序中同一路徑的兩個 `StateStore` 實例不會塌陷成單一可重入鎖（在多執行緒寫入爭用時會拋出 `RuntimeError`）。新增共享讀取、跨程序獨占與多執行緒/多程序迴歸測試。
---

# 設計文件：工作階段管理 (`new`, `status`, `stop`, `sessions`)

## 概述
工作階段管理涉及與 Colab 後端互動，以配置、監控和終止執行期（Runtimes）。

## 執行期參數

`colab new` 指令支援選擇特定的硬體與執行期環境。根據 `tpu-v5e1.har` 追蹤軌跡與 `colab-agent` 原始碼，識別出以下參數與其數值：

### 1. 變體 (`variant`)
定義所請求硬體的一般類別。
- `DEFAULT`：標準的 CPU 執行期。
- `GPU`：請求 GPU 加速的執行期。
- `TPU`：請求 TPU 加速的執行期。

### 2. 加速器 (`accelerator`)
定義具體的硬體型號。
- **None**：適用於 `DEFAULT` 變體。
- **GPU 加速器**：
    - `T4`：NVIDIA T4（標準免費層 GPU）。
    - `L4`：NVIDIA L4（具高性價比的現代 GPU）。
    - `G4`：NVIDIA G4（入門級資料中心 GPU）。
    - `A100`：NVIDIA A100（高效能 GPU）。
    - `H100`：NVIDIA H100（最新一代高效能 GPU）。
- **TPU 加速器**：
    - `V2-8`：TPU v2（8 核心）。
    - `V5E1`：TPU v5e（1 核心，專為推論與高效訓練優化）。
    - `V6E1`：TPU v6e（1 核心，極致效能）。

### 3. 機器規格 (`shape`)
定義支援選擇的執行期（CPU、T4、A100 等）的 RAM 配置。
- `STANDARD`（預設）：在 assign 時省略 `shape` 查詢參數。
- `HIGH_RAM`：在 assign 時送出 `shape=hm`（需要 Colab Pro/Pro+ 資格）。

只有一種規格的加速器（L4、v5e1、v6e1）會忽略 `--high-mem`。

### 4. CLI 旗標對應
CLI 將使用者旗標對應至這些後端參數：
- `colab new my-session` -> `variant=DEFAULT`, `accelerator=NONE`
- `colab new my-session --gpu=L4` -> `variant=GPU`, `accelerator=L4`
- `colab new my-session --tpu=v5e1` -> `variant=TPU`, `accelerator=V5E1`
- `colab new my-session --high-mem` -> 加入 `shape=hm`（受支援時）
- `colab new my-session --gpu A100 --high-mem` -> `variant=GPU`, `accelerator=A100`, `shape=hm`

`--gpu` 接受 `T4`、`L4`、`G4`、`H100` 與 `A100`；`--tpu` 接受 `v5e1` 與 `v6e1`（不分大小寫）。其他任何值都會在要求虛擬機器之前，連同支援清單一起被拒絕。未知值過去會默默退回 `A100`/`v6e1`，使自動化腳本中的拼寫錯誤變成真實且會計費的配置。

## 實作方法

### HTTP 逾時與配置恢復

`COLAB_CLI_REQUEST_TIMEOUT` 設定 HTTP 請求逾時（秒）。若未設定，則套用工作階段既有的預設值（AuthorizedSession 預設 120 秒）。呼叫端明確傳入的 `timeout=` 優先。此設定不會改變核心執行逾時、Colab 執行期壽命或基準測試任務逾時。

配置 POST 對 `ReadTimeout` 與 HTTP 502/503/504 最多重試 `COLAB_CLI_ASSIGN_RETRIES` 次（預設 3；0 表示停用重試）。每次嘗試之間，用戶端等待 `COLAB_CLI_RETRY_BACKOFF * 2**attempt` 秒（預設 10、20、40）。然後它查詢相同的筆記本雜湊：既有配置直接回傳；否則以下一個 POST 使用刷新後的 XSRF 權杖。HTTP 412 仍拋出 `TooManyAssignmentsError`；其他錯誤不重試。失敗的初始／恢復 GET 與用盡的 POST 重試會傳播給呼叫端。沒有無限等待。

```bash
COLAB_CLI_REQUEST_TIMEOUT=300 COLAB_CLI_ASSIGN_RETRIES=3 COLAB_CLI_RETRY_BACKOFF=10 \
  colab new --session kernel-benchmark-v6e --tpu v6e1
```

迴歸測試涵蓋逾時優先順序、相同請求恢復、刷新後的權杖、重試上限、指數退避與永久錯誤處理。在宣稱此行為已端到端驗證之前，還需要一次真實的配置／恢復測試；光靠模擬逾時無法確立後端相容性。

### 1. 新增工作階段 (`colab new`)
- **API**：`GET https://colab.sandbox.google.com/tun/m/assign`（基於 HAR 軌跡）。
- **參數**：
    - `nbh`：Notebook 哈希值。基於每個 CLI 工作階段/用戶端執行個體的唯一 UUID 生成，轉換為帶有特定填充（共 44 個字元）的 Web 安全 Base64。
    - `nsa`：1（瀏覽器軌跡中觀察到的標準旗標，通常用於「下一代工作階段架構」）。
    - `variant`：選自上述列表。
    - `accelerator`：選自上述列表。
- **狀態持久化**：回應中包含一個 `token`，可能還包含一個後端網址或識別碼。我們將其儲存在本地的 JSON 檔案中（預設為 `~/.config/colab-cli/sessions.json`），只允許其擁有者讀取（模式 0600）。
    - 格式：`{ "session_name": { "token": "...", "backend_url": "...", "hardware": "..." } }`

### 2. 工作階段狀態 (`colab status`)
- **工作階段行**：每個追蹤工作階段的本地中繼資料 — 硬體、規格、variant、IDLE/BUSY（來自 CLI 記帳），以及選用的最後執行細節。與 `GET /tun/m/assignments` 同步以修剪過期項目。
- **未來**：透過核心診斷片段取得即時虛擬機器資源使用率（CPU/RAM/GPU）仍是待辦事項。帳戶層級的運算單位餘額與使用率請用 `colab usage`。

### 3. 停止工作階段 (`colab stop`)
- **API**：`POST https://colab.sandbox.google.com/tun/m/unassign/<endpoint>`（基於 `tpu-v5e1-unassign.har`）。
- **流程**：
    1. 對取消分配（Unassign）網址執行 `GET` 請求以取得全新的 XSRF 權杖。
    2. 對同一個網址執行 `POST` 請求，並帶上 `X-Goog-Colab-Token` 標頭。
- **參數**：
    - `authuser`：0。
    - `<endpoint>`：配置期間回傳的唯一工作階段識別碼（例如 `tpu-v5e1-s-kkb-...`）。
- **清理**：成功收到 204 回應後，從本地狀態檔案中移除該工作階段。
- **缺失的工作階段**：停止特定工作階段（`colab stop` 或 `colab stop -s <name>`）時，若不存在相符的作用中工作階段，會以代碼 1 結束。當沒有工作階段作用中時，`colab stop --all` 以 0 結束。

### 4. 列出工作階段 (`colab sessions`)
- **API**：`GET https://colab.research.google.com/tun/m/assignments`（基於 `colab-agent` 實作）。
- **功能**：列出該使用者所有作用中的虛擬機器分配。這對於將本地狀態與實際後端工作階段進行同步非常實用。

### 5. 工作階段存活
虛擬機器的存活由 Colab 後端依作用中的核心執行與互動自動維持。CLI 不執行任何 keep-alive 守護行程。工作階段會持續存在，直到透過 `colab stop` 明確終止，或直到後端因閒置而回收它為止。

### 6. 執行期代理權杖刷新
執行期代理權杖（`runtimeProxyInfo.token`）驗證對虛擬機器的每個請求，並在 `tokenExpiresInSeconds`（1 小時）後過期。`SessionState.token_expires_at` 儲存收到權杖時計算出的絕對過期時間。與虛擬機器溝通的指令會透過 `State.get_session(name)` 載入其工作階段；當權杖缺少過期時間或距離過期 5 分鐘以內時，它會呼叫 `GET /tun/m/assignments`，取得相符端點的新權杖／網址，並將其持久化。若該端點已不再被配置，該工作階段會被修剪。`sync_sessions` 也會回寫它已取得的新權杖。長壽命連線（`repl`、`ssh`）只在初始連線時呈現權杖，不會在工作階段中途刷新。

## 待辦事項 / 未來規劃
- **後端同步**：實作一種能將本地 `sessions.json` 與 `colab sessions` 輸出進行核對與同步的方法。
- **虛擬機器資源使用率**：透過在虛擬機器上執行診斷程式碼片段，在 `status` 輸出中加入即時資源使用率（CPU/RAM/GPU）（與可透過 `colab usage` 取得的帳戶層級 CU 資訊不同）。

## 實作細節
- **身分驗證**：使用 `google-auth-oauthlib`（`InstalledAppFlow` 遠端複製貼上流程，預設 `--auth oauth2`）或應用程式預設憑證（`--auth adc`）。
- **全域旗標**：
    - `--auth`：身分驗證策略（`oauth2` 或 `adc`，預設：`oauth2`）。使用者 ADC 憑證需要 `gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory`。
    - `-c`、`--client-oauth-config`：用戶端金鑰 JSON 檔案路徑（預設為 `~/.colab-cli-oauth-config.json`）。
    - `--config`：工作階段狀態 JSON 檔案路徑（預設為 `~/.config/colab-cli/sessions.json`）。
- **權杖儲存**：在初始流程完成後，憑證會透過 `keyring` 函式庫（`service_name="google-colab-cli"`、`username="oauth_token"`）持久化到 OS 原生金鑰圈。若金鑰圈無法存取或已鎖定，會為本次執行呼叫 `_run_remote_flow`，並在 stderr 印出警告。舊版 `~/.config/colab-cli/token.json` 會在第一次使用時遷移進入金鑰圈，並在金鑰圈寫入成功後刪除，或在金鑰圈已有權杖時立即刪除。
- 使用 `requests` 處理健全的 HTTP 互動，並使用 `pydantic` 進行 Schema 驗證。
- 處理身分驗證標頭（如 `Authorization: Bearer <token>` 或 Cookie）。

### 狀態持久化與檔案鎖定
- **儲存庫**：`StateStore`（`sessions.json`）與 `SettingsStore`（`settings.json`）都衍生自 `_LockedFileStore`，它保護跨獨立 `colab` 呼叫的並行存取。
- **跨平台鎖定**：鎖定使用 [`filelock`](https://pypi.org/project/filelock/) 函式庫，而不是 `fcntl.flock`。`fcntl` 僅限 POSIX 且在 Windows 上不可用，因此原始實作在該平台匯入時會當掉。`filelock` 在 Linux、macOS 與 Windows 上提供相同的建議性跨程序鎖定。
- **共享與獨占**：每個儲存庫擁有一個綁定到附屬檔案（`<path>.lock`）的 `filelock.ReadWriteLock`。讀取取得 `read_lock()`（共享 — 允許多個並行讀取者），寫入取得 `write_lock()`（獨占）。這保留了先前 `fcntl` 實作的 `LOCK_SH`/`LOCK_EX` 區別。
- **`is_singleton=False`**：`ReadWriteLock` 以 `is_singleton=False` 建立。使用 `filelock` 的預設值（`True`）時，同一程序內同一路徑的兩個 `ReadWriteLock` 物件會被去重成單一可重入鎖；其可重入保護會在兩個執行緒各自建構自己的 `StateStore` 並爭用寫入鎖時拋出 `RuntimeError`。停用單例登錄使每個儲存庫的鎖彼此獨立，讓它們改透過底層檔案鎖序列化。

## 測試策略
所有工作階段管理功能皆必須遵循測試驅動開發（TDD）。

### 1. 模擬配置 API
- **測試案例**：驗證 `colab new` 是否能正確解析 `PostAssignmentResponse` 並將其儲存於本地的 `StateStore` 中。
- **測試案例**：驗證 `colab stop` 是否對取消配置端點傳送帶有正確 XSRF 權杖的 `POST` 請求。
- **測試案例**：驗證 `colab stop -s <missing>` 會印出找不到的錯誤，並以狀態 1 結束，且不呼叫 unassign。
- **測試案例**：驗證透過 `-c` 指定的路徑是否被正確傳遞至身分驗證流程中。
- **模擬方法**：使用 `unittest.mock` 攔截 `requests.Session.request`，並回傳與 HAR 軌跡相符、帶有模擬 XSSI 前綴的 JSON 負載（Payload）。

### 2. 狀態儲存庫驗證
- **測試案例**：驗證 `StateStore` 是否能正確處理檔案鎖定以及多個同時進行的讀取/寫入。
- **測試案例**：驗證 `--config` 覆寫是否能正確地將所有作業導向至指定的檔案路徑。
- **測試案例（跨平台鎖定）**：驗證儲存庫透過 `<path>.lock` 附屬檔案上的 `filelock.ReadWriteLock` 鎖定，且不匯入僅限 POSIX 的 `fcntl`。
- **測試案例（共享／獨占語意）**：驗證讀取走 `read_lock()`，寫入走 `write_lock()`。
- **測試案例（跨程序獨占）**：從另一個程序持有寫入鎖，並確認儲存庫的程序內寫入會阻塞直到釋放。
- **測試案例（並行讀取者）**：從另一個程序持有讀取鎖，並確認儲存庫仍能並行完成讀取。
- **測試案例（多執行緒迴歸）**：兩個從不同執行緒寫入的 `StateStore` 實例必須序列化，且不拋出 `RuntimeError`（保護 `is_singleton=False` 的選擇）。
