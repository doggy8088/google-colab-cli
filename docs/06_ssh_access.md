---
log:
2026-11-23：更新 `integration/repro_windows_ssh/test.py`，改為透過 OS `keyring`（`KEYRING_SERVICE_NAME` / `KEYRING_USERNAME`）檢查快取的 OAuth2 憑證，而不是已移除的 `TOKEN_CONFIG_PATH`，並在 `tests/test_windows_ssh.py` 新增可攜式匯入與前置條件略過的迴歸測試。
2026-11-09：`--identity/-i` 現在可接受 `.pub` 公開金鑰或私密金鑰路徑：`_resolve_pubkey` 會先直接讀取存在的 `.pub` 檔，再退回 `_pubkey_from_identity`（`ssh-keygen -y -f`），且 `_ssh_base_args` 在同名私密金鑰存在於磁碟時，會為 `ssh -i` 去掉 `.pub`。
2026-10-29：移除了 `colab console` 子指令，因此 `colab ssh` 是執行期上的互動式 shell。從 Windows 驗證注意事項中刪除了 console 行為。
2026-10-29：新增 `colab ssh [-s NAME] -- CMD`，在既有工作階段上執行一個指令並以其狀態結束（只有 stdin 與 stdout 都是終端機時才使用 PTY；它與其 ProxyCommand 子程序都不會建立執行期）。其握手帶有 `ssh-mode-cmd`，且 stdout 不是終端機時 `ssh` 會略過更新橫幅。新增 `tests/test_ssh_cmd.py`。
2026-10-29：HTTP 429 現在會在主體帶有上限時顯示伺服器的 SSH 工作階段上限（「N of N SSH sessions in use」）。
2026-10-29：`colab ssh` 啟動的 ProxyCommand 現在會保留非預設的全域 `--auth` 與 `--config`（以絕對路徑表示），因此 `colab --config ALT ssh -s S` 會從 ALT 橋接 S，而不是預設的工作階段檔案。
2026-10-29：每個 `/colab/ssh` 握手現在都會送出 `X-Colab-Client-Agent: colab-cli` 與兩個 `colab-client-agent` 查詢值 `colab-cli` 和 `ssh-mode-<mode>`。mode 在一般 `colab ssh` 時為 `interactive`，在 `colab ssh -- CMD` 時為 `cmd`（兩者都透過隱藏的 `--colab-internal-mode` 選項傳給其 ProxyCommand 再次呼叫），其餘情況為 `proxy`。
2026-10-20：修復 Windows SSH ProxyCommand 引號、本地空裝置選擇與清理訊號註冊。新增 Windows 原生迴歸與真實整合測試；在 Windows、Linux 與 macOS 上驗證 SSH 套件，外加 Windows 真實遠端執行與執行期清理。
2026-09-25：清理工作階段建立與拆除文件中的 keep-alive 守護行程參考。
2026-08-09：當 `colab ssh` 自動建立執行期時，新增 `--high-mem` 透傳（轉發給 `colab new --high-mem`）。
2026-07-17：`colab ssh` 的初始設計與實作 — SSH-over-WebSocket 執行期存取的用戶端。新增三種模式（互動式 shell、`-s SESSION`，以及 `--proxy-mode` OpenSSH ProxyCommand 橋接）、`--identity/-i` 金鑰選擇，以及依 HTTP 狀態區分的握手錯誤訊息。伺服器端不在本 repo 範圍內；對未暴露 `/colab/ssh` 端點的執行期，此子指令不會有作用（會呈現可操作的 HTTP 404 訊息）。
2026-07-22：裸 `colab ssh` 現在會在您沒有作用中工作階段時自動建立執行期（透過 `colab new`），並透傳 `--gpu/--tpu`，且可用 `--rm` 在結束時停止自動建立的執行期。修復兩個用戶端錯誤：已死的 403 分支（功能關閉時回傳 404，不是 403），以及 RSA 指引（所有 `ssh-rsa` 金鑰都會被伺服器拒絕，因此不再自動掃描 `id_rsa`，400 訊息也不再宣傳 `rsa-sha2`）。新增 `tests/test_ssh_wire_contract.py`（真實 loopback 伺服器連線斷言）與 `tests/test_ssh_autocreate.py`。
2026-07-22：互動式 `colab ssh` 現在會透過強制 PTY（`-t`）加上遠端 `cd /content 2>/dev/null; exec $SHELL -l`，從 `/content`（Colab 的工作目錄）開始，而不是 `/root`。缺少 `/content` 時退回登入主目錄。新增 `tests/test_ssh_workdir.py`。
2026-07-22：`--proxy-mode` 現在會遵守每個 `colab ssh` 旗標：帶 `-s NAME` 時會在缺少時建立工作階段（建立輸出導向 stderr，使 stdout 保持乾淨的 ssh 位元組串流），`--gpu/--tpu` 設定加速器，`--rm` 在中斷連線時停止橋接的工作階段 — 因此 `~/.ssh/config` 主機第一次連線就能運作，也可做成臨時性的。完全移除 `--drive` 子功能（程式碼與測試）。
2026-07-22：修復 `--proxy-mode --rm` 在中斷連線時未拆除的問題。OpenSSH 在工作階段結束時會對 ProxyCommand 送出 SIGHUP（已實證），不只是 stdin EOF，而 Python 預設的 SIGHUP 動作會在拆除的 `finally` 執行前就終止程序，洩漏執行期與 keep-alive 守護行程。現在 `--rm` 會安裝 SIGHUP/SIGTERM/SIGINT 處理常式來執行停止（與 `finally` 冪等）。
2026-07-23：對 ssh 程式碼套用 go/pystyle 可讀性（80 欄重排、Args/Returns/Raises docstring），並將整合測試從 `--help` 冒煙升級為真實端到端：它以 `colab ssh --proxy-mode` 作為 OpenSSH ProxyCommand 驅動真實遠端指令（握手 + 公鑰標頭驗證 + 橋接 + 遠端執行），斷言 RSA 金鑰被拒絕，並驗證沒有孤兒虛擬機器 — 外加永遠開啟的離線檢查（說明旗標 + 未知工作階段以 2 結束）。真實部分現在會在驗證存在時自動執行，而不是以 `RUN_LIVE` 閘控。
2026-07-24：將 `ssh()` 重構為以意圖命名的輔助函式（`_select_proxy_session`、`_select_interactive_session`、`_run_proxy_bridge`、`_run_interactive_shell`、`_install_rm_signal_handlers`、`_warn_accelerator_ignored`）— 行為不變 — 並將兩則 `--gpu/--tpu ignored` 訊息統一為一則。新增 `tests/test_ssh_lifecycle.py` 鎖定生命週期保證：`--rm` 拆除能挺過例外（try/finally）、ssh/橋接結束代碼傳播、`--proxy-mode` stdout 乾淨（建立/`--rm` 輸出留在 stderr）、自動建立失敗會在連線前中止、`--gpu`+`--tpu` 都轉發給 `colab new`、`--rm` 在訊號與 finally 路徑間冪等，以及重用工作階段的 `--rm` 拆除。精簡了本文件與整合 README 的文字。
---

# 設計文件：`colab ssh` — 透過 WebSocket 的 SSH 執行期存取

## 動機
使用者想要在他們的 Colab 執行期上有真正的 shell，更重要的是 IDE 遠端開發（VS Code Remote-SSH、JetBrains Gateway、一般 `ssh`）。`colab ssh` 是允許 ssh 進入 Colab 的用戶端，它重用 CLI 既有的工作階段解析與執行期代理權杖，因此不需要另外處理憑證。

## 使用者介面

```
colab ssh [OPTIONS] [-- CMD [ARGS]...]
```

| 旗標 | 類型 | 預設值 | 用途 |
|---|---|---|---|
| `-s`, `--session` | 字串 | 自動 | 要連線的工作階段。若省略，會使用您唯一的作用中工作階段；在您沒有工作階段時自動建立一個（搭配 `-- CMD` 時不會），或在您有多個時出錯。 |
| `--proxy-mode` | 布林值 | False | 作為與 OpenSSH `ProxyCommand` 相容的 WebSocket↔stdio 橋接（讀取 stdin、寫入 stdout），供 `~/.ssh/config` 使用。其他每個旗標仍然適用。 |
| `-i`, `--identity` | 字串 | 自動 | SSH 金鑰（`.pub` 公開金鑰或私密金鑰路徑），用於送給 Colab 的公開金鑰。預設：`~/.ssh/id_ed25519.pub`、`id_ecdsa.pub` 中的第一個。 |
| `--gpu` | 字串 | None | 本指令所建立執行期的 GPU 加速器（T4, L4, G4, H100, A100）。 |
| `--tpu` | 字串 | None | 本指令所建立執行期的 TPU 加速器（v5e1, v6e1）。 |
| `--high-mem` | 布林值 | False | 當本指令自動建立執行期時要求高 RAM（連線到既有工作階段時忽略）。 |
| `--rm` | 布林值 | False | 工作階段結束時停止執行期。互動式：只限 `colab ssh` 自動建立的執行期（重用的工作階段永遠不會被移除）。`--proxy-mode`：橋接的工作階段，於中斷連線時停止。搭配 `-- CMD` 時忽略。 |

### `~/.ssh/config` 使用方式
`--proxy-mode` 讓 `colab ssh` 變成任何以 SSH 為基礎的工具都能驅動的傳輸：

```
Host <alias>
  ProxyCommand <abs-path-to>/colab ssh --proxy-mode -s <name> [--gpu T4] [--rm]
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
```

因為每個旗標在 `--proxy-mode` 下都適用，`-s <name>` 會在第一次連線時建立工作階段，`--gpu/--tpu` 決定其大小，`--rm` 讓該主機成為臨時性的。請使用 `colab` 的**絕對**路徑：`ssh` 在非登入 shell 中執行 `ProxyCommand`，裸 `colab` 可能不在 `PATH` 上。外部 SSH 工具會執行它們自己的遠端指令，因此若也要落在 `/content`，請加上 `RequestTTY yes` 與 `RemoteCommand cd /content 2>/dev/null; exec bash -l`。

### 遠端指令
`colab ssh [-s NAME] -- CMD [ARGS]...` 在既有工作階段的 `/content` 中執行 CMD（永遠不會建立工作階段）；從 CMD 開始的每個字都會傳給 CMD，旗標也是。

- 一個參數是一行 shell 指令（`-- 'ls / | wc -l'`）；多個參數則是精確的 argv，因此分開參數中的 `*`、`~` 與 `$VAR` 不會被展開。腳本也可以管線輸入：`echo cmd | colab ssh -s NAME -- bash`。
- 只有 stdin 與 stdout 都是終端機時才用 `-t`；否則不使用 PTY，因此管線輸出會逐位元組精確。結束狀態就是 CMD 的；255 表示 ssh 錯誤，或遠端指令被訊號殺死（例如來自 `| head` 的 SIGPIPE）。
- 一個執行期接受有限數量的並行 SSH 連線；超過時伺服器回覆 429，`colab ssh` 會印出其訊息。
- 兩端都是終端機時，Ctrl-C 會抵達遠端指令，且 ssh 以 255 結束。管線傳輸時，Ctrl-C 只會停止 `colab ssh`（以 130 結束），遠端指令可能繼續執行：請用不會比對到它自己 shell 的模式停止它，例如 `colab ssh -s NAME -- pkill -f '[s]leep 300'`，或用 `colab stop`。
- SSH 工作階段使用精簡環境：Python、pip 與 `nvidia-smi` 可以運作；`gcloud` 或 `node` 等工具可能需要把其目錄加入 `PATH`。

## 行為

1. **工作階段解析／自動建立**：帶 `-s NAME` 時，解析該工作階段（透過 `state.resolve_session`，與其他指令相同的輔助函式）。裸 `colab ssh` 使用您唯一的作用中工作階段；在**沒有**工作階段時自動建立一個（鏡像 `colab new`：assign → 持久化 `SessionState`；搭配 `-- CMD` 時永遠不會）；在有**多個**時出錯，並請您用 `-s` 選一個。
2. **連線**：開啟到 `wss://<netloc>/colab/ssh?colab-runtime-proxy-token=<token>` 的 WebSocket，並將解析出的公開金鑰逐字送在 `X-Colab-Ssh-Pubkey` 標頭中（不做任何轉換 — 使用者控制的位元組正是伺服器收到的內容）。只接受 `ssh-ed25519` / `ecdsa-sha2-nistp{256,384,521}` 金鑰。它也會送出 `X-Colab-Client-Agent: colab-cli`，並附加 `&colab-client-agent=colab-cli&colab-client-agent=ssh-mode-<mode>`：一般 `colab ssh` 為 `interactive`，`colab ssh -- CMD` 為 `cmd`，使用者自寫的 `ProxyCommand` 或 IDE 為 `proxy`。
3. **互動式 shell**：以 CLI 被再次呼叫作為其自己的 `ProxyCommand`（`python -m colab_cli.cli ssh --proxy-mode --colab-internal-mode interactive`）來生成系統 `ssh` 二進位檔，因此 WebSocket 橋接與互動式 shell 共用同一條程式碼路徑。它強制使用 PTY（`-t`）並執行 `cd /content 2>/dev/null; exec $SHELL -l`，讓您落在 `/content`（Colab 的工作目錄）而不是 root 的主目錄；缺少 `/content` 時退回登入主目錄。在 Windows 原生環境，ProxyCommand 使用 `subprocess.list2cmdline` 處理 CreateProcessW 參數解析；POSIX 系統繼續使用 `shlex.join`。本地 `UserKnownHostsFile` 使用 `os.devnull`（Windows 上為 `nul`）。
4. **`--proxy-mode` 橋接**：橋接 WebSocket ↔ stdin/stdout，作為 OpenSSH `ProxyCommand` 使用。遵守每個旗標：`-s NAME` 會在缺少時建立工作階段（建立輸出導向 stderr，使 stdout 保持乾淨的 ssh 位元組串流）；沒有 `-s` 的裸 `--proxy-mode` 只會解析既有工作階段。
5. **`--rm` 拆除**：工作階段結束時停止執行期。在 `--proxy-mode` 下，這必須挺過 OpenSSH 結束 `ProxyCommand` 的方式：中斷連線時它會送出 **SIGHUP**（已驗證），不只是 stdin EOF，而 Python 預設的 SIGHUP 動作會在拆除的 `finally` 執行前終止程序 — 洩漏執行期。`--rm` 因此會為可用的 SIGHUP/SIGTERM/SIGINT 訊號安裝處理常式來執行停止，與 `finally` 冪等。`SIGKILL` 無法攔截，因此 `kill -9`／硬當機仍可能洩漏；正常中斷連線是 SIGHUP，會被處理。Windows 沒有 SIGHUP，因此註冊時略過它，保留 SIGTERM/SIGINT。Windows 上的強制程序終止也可能繞過清理；此變更不保證被殺死的程序之後仍能拆除。
6. **錯誤處理**：WebSocket 升級會將每個常見 HTTP 狀態對映為可操作的訊息：

   | 狀態 | 向使用者呈現的意義 |
   | --- | --- |
   | 400 | 公鑰不正確／不受支援／缺失，並附修復方式（`ssh-keygen -t ed25519`） |
   | 401 | 權杖無效／已過期 — 請試 `colab new` |
   | 403 | 禁止 — 權杖缺少此動作的權限（功能關閉時回傳 404，不是 403） |
   | 404 | 此執行期未暴露 SSH — SSH 是在建立時內建的，因此請執行 `colab new` |
   | 429 | 已達工作階段上限：「N of N SSH sessions in use」，且上限取決於 Colab 方案；若主體沒有可用上限，則表示另一個 `colab ssh` 已連線：請先中斷它 |
   | 502 | 執行期 `sshd` 無法抵達 — 執行期可能不健康 |
   | 其他／無 | 原始狀態，或網路檢查提示 |

7. **遠端指令**：`-- CMD` 解析既有工作階段，並依「遠端指令」一節所述執行 CMD。其 ProxyCommand 子程序（mode `cmd`）也只解析工作階段，因此兩個程序都不會建立執行期。

## 測試策略 (TDD)

### 單元測試 (`tests/test_ssh.py`)
1. WebSocket URL 建構（https 用 `wss`，http 用 `ws`；權杖查詢參數）。
2. 公鑰解析 — `--identity`（先讀取對應的 `.pub` 檔，無論傳入時有沒有 `.pub`，再退回 `ssh-keygen -y -f`）與 `~/.ssh` 預設掃描；缺少金鑰與缺少 identity 的結束路徑。
3. 完整的狀態→訊息對映（400/401/403/404/429/502/其他/無）。
4. `ProxyCommand` 字串的 shell 引號。
5. 工作階段解析（既有與缺失）。
6. 端到端分派：互動式與 `--proxy-mode`，包括逐字公鑰透傳斷言與可操作的 400 訊息。

### 連線契約測試 (`tests/test_ssh_wire_contract.py`)
架設 loopback WebSocket 伺服器並驅動真實連線路徑（不使用 mock），斷言請求路徑、`colab-runtime-proxy-token` 查詢參數、`X-Colab-Ssh-Pubkey` 標頭、`X-Colab-Client-Agent` 標頭與兩個 `colab-client-agent` 查詢值都逐字抵達連線。包括變異測試：若 `_SSH_PATH`/`_PUBKEY_HEADER`、用戶端代理標頭或 mode 值漂移就會失敗；透過真正的 `WebSocketBadStatusException` 測試真實 HTTP 400/429 對映（包括帶上限的 429 主體），以及一般 `colab ssh`（`interactive`）與使用者 `ProxyCommand`（`proxy`）的真實 CLI 子程序。

### 自動建立與 proxy-mode 測試 (`tests/test_ssh_autocreate.py`)
裸 `colab ssh` 的建立、重用與不明確情況；`--gpu/--tpu` 透傳；`--rm` 結束時停止；以及 `--proxy-mode` 矩陣 — 帶 `-s NAME` 時缺少即建立、重用既有工作階段、`--gpu` 透傳、`--rm` 拆除，以及 SIGHUP 清理處理常式只在 `--rm` 下安裝。

### 工作目錄測試 (`tests/test_ssh_workdir.py`)
互動式 `ssh` 強制使用 PTY（`-t`）並執行 `cd /content` 遠端指令（主機在指令之前，以 `2>/dev/null` 容忍目錄缺失）。

### 遠端指令測試 (`tests/test_ssh_cmd.py`)
`-- CMD` 轉發與引號、`-t`/`-T` 規則、結束狀態、父程序與其 ProxyCommand 子程序都不自動建立、`websocket.WebSocket.connect` 處的 `ssh-mode-cmd`、已關閉的 stdio，以及更新橫幅閘控。

### 整合測試 (`integration/repro_ssh/`)
兩部分。永遠執行的離線冒煙（不需虛擬機器）：`--help` 有宣傳文件記載的旗標，未知工作階段以 2 結束並附可操作訊息。在驗證存在時執行的真實端到端（配置一台 CPU 虛擬機器）：它以 `colab ssh --proxy-mode` 作為 OpenSSH ProxyCommand，透過 WebSocket 橋接執行真實遠端指令 — 走與互動式 shell 相同的連線 → 公鑰標頭驗證 → 握手 → 橋接 → 遠端執行路徑，只差沒有 TTY — 斷言 RSA 金鑰被拒絕，並驗證 `colab stop` 不會留下孤兒虛擬機器。

### Windows 迴歸測試 (`tests/test_windows_ssh.py`)
真實 Windows 子程序使用安裝在帶空格路徑下的 Python 直譯器，執行產生的 ProxyCommand。斷言檢查空格、引號、shell 標點、反斜線、Unicode 與 identity 路徑的精確 argv 保留。另一項測試以本地 stub ProxyCommand 啟動真正的 Windows OpenSSH 用戶端並驗證其 argv，不聯絡 Colab。可攜式測試也檢查沒有 SIGHUP 時的註冊、本地空裝置，以及 `integration/repro_windows_ssh/test.py` 在各平台的匯入與前置條件略過路徑。既有的 POSIX shell 引號與拆除測試仍保留在套件中。

這些與既有的 SSH 測試已在 Windows、Linux 與 macOS 上以 Python 3.12 通過。這只涵蓋 SSH 相容性；本地檔案編輯與自我更新需要另外的平台驗證。

`uv run python integration/repro_windows_ssh/test.py` 提供 Windows 原生真實測試，使用 OS 金鑰圈中快取的 OAuth2 憑證。它建立 CPU 執行期、透過產生的 ProxyCommand 以帶空格的金鑰路徑執行遠端指令、 測試 `--rm`，並在失敗時清理所記錄的端點。以 77 結束是前置條件略過，不是成功的真實驗證。

Windows 原生真實測試已於 2026-10-20 以 Python 3.12.14 與 Windows OpenSSH 用戶端通過。這驗證了此 SSH 路徑的遠端指令執行與清理，而不是整體 Windows 原生功能對等性。
