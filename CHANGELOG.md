# 變更記錄

本專案所有值得注意的變更都會記錄在此檔案中。

格式依循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，且本專案遵循[語意化版本](https://semver.org/spec/v2.0.0.html)。

套件版本由 git 標籤透過 `hatch-vcs` 產生；以下每個版本都對應一個同名標籤。

## [未發佈]

### 變更

- **ssh：** 每個 `colab ssh` WebSocket 現在都會送出 `X-Colab-Client-Agent: colab-cli`，以及查詢值 `colab-client-agent=colab-cli` 與 `colab-client-agent=ssh-mode-<mode>`，其中 mode 在一般 `colab ssh` 時為 `interactive`，在 `colab ssh -- CMD` 時為 `cmd`，其餘情況為 `proxy`。
- **ssh：** 當伺服器以 HTTP 429 拒絕連線並回報其 SSH 工作階段上限時，`colab ssh` 現在會說明已達上限（該執行期正在使用 N 個工作階段，共 N 個），且該上限取決於 Colab 方案。沒有可用上限資訊的 429 則保留先前的訊息。

### 新增

- **ssh：** `colab ssh [-s NAME] -- CMD` 在既有的執行期上執行一個指令，並以其狀態結束。管線傳輸時輸出會逐位元組精確（只有在 stdin 與 stdout 都是終端機時才使用 PTY），且永遠不會建立執行期。其握手會標記為 `ssh-mode-cmd`。

### 移除

- **console：** **重大變更：** 移除 `colab console` 子指令。互動式 shell 請改用 `colab ssh -s NAME`，單次指令請用 `colab ssh -s NAME -- CMD`；在 ssh 無法使用時，請將加上 `!` 前綴的 shell 指令管線傳給 `colab exec -s NAME`。每一行 `!` 都是獨立的 shell，且 IPython 會展開其中的 `{expr}` 與 `$name`，所以多行腳本請以 `%%bash` 開頭，並讓不可信文字不要出現在 `!` 行中。此為重大變更，因此會隨新的主版本號發佈。

### 修復

- **ssh：** `colab --config FILE ssh` 與 `colab --auth adc ssh` 現在會在 `colab ssh` 啟動的 ProxyCommand 中保留那些選項，使其使用相同的工作階段檔案與驗證提供者，而不是預設值。
- **安全性：** 建立偵錯日誌（`~/.config/colab-cli/colab.log`）、`sessions.json`、`settings.json` 與工作階段歷史檔案時，只允許其擁有者讀取，並在 CLI 下次使用舊版留下的、他人可讀的副本時將其收緊。
- **安全性：** 不再將存取權杖、執行期代理權杖、OAuth 代碼、用戶端密鑰、驗證標頭與 cookies 寫入偵錯日誌。舊版寫出的日誌可能含有憑證，可以刪除；若其他使用者可能讀過舊日誌，請在您的 Google 帳戶中撤銷 CLI 的存取權並重新登入。

## [0.7.1] - 2026-09-14

### 修復

- **建置：** 將 wheel 與 sdist 的核心中繼資料都固定為 2.4 版。hatchling 1.32.0 將其預設值提高到 2.5，而我們的發佈管線會拒絕它，因此 0.7.0 雖然建置完成，卻從未抵達 PyPI。`colab ssh`（於 0.7.0 新增）因此對任何從 PyPI 安裝的人都無法使用。

## [0.7.0] - 2026-09-03

### 變更

- **依賴：** 將 cryptography 從 49.0.0 升級到 50.0.0（#98），pyasn1 從 0.6.3 升級到 0.6.4（#87）。
- **鎖定檔：** 透過 `uv lock --upgrade` 升級鎖定檔依賴。（#67）
- **技能：** 將 CLI 說明技能的細節移到專用的 `SKILL.md`。（#55）
- **文件：** 在 `AGENTS.md` 中更新發佈標籤工作流程的說明。（#66）

### 新增

- **ssh：** 新增 `colab ssh` 指令，透過 SSH-over-WebSocket 直接存取 Colab 執行期虛擬機器。（#88）
- **執行：** 在 `colab run` 與 `colab exec` 指令新增 `--env KEY=VALUE` 旗標，允許將自訂環境變數注入執行中的核心。（#65）
- **工作階段：** 在建立新工作階段、選擇機器規格時新增 `--high-mem` 旗標，以支援高 RAM 資源。（#105）

### 修復

- **工作階段：** 在 412 GPU/TPU 配置失敗時呈現友善的錯誤訊息，而不是印出原始追蹤。（#112）
- **執行期：** 在執行期層同時支援 `ColabKernelClient` 與標準 `KernelClient`，以改善跨環境相容性。（#95）

## [0.6.0] - 2026-06-16

### 變更

- **驗證：** OAuth2 登入現在使用遠端複製貼上流程，而不是 localhost 回呼伺服器。CLI 會印出一個授權網址，其 `redirect_uri=https://sdk.cloud.google.com/applicationdefaultauthcode.html` 且 `token_usage=remote`，然後從 stdin 讀取貼上的代碼。這在無頭／遠端環境中也能運作，因為在那些環境中瀏覽器無法抵達本地回呼連接埠。（#54）

### 新增

- **顯示輸出：** 透過共用的 `render_display_data()` 輔助函式，為 `display_data` 輸出提供 Rich 呈現。HTML 會以 `html2text` 轉換並呈現為 Markdown，依循 `text/markdown > text/html > text/plain` 的優先順序；`text/plain` 會以 `Text.from_ansi` 包裝，以保留內嵌的 ANSI 逸出序列。在 `exec`、`console`/`repl` 與自動化呼叫點一致套用。（#58）

### 修復

- **keep-alive：** 將 `colab.pa.googleapis.com` 上的 `RuntimeService/KeepAliveAssignment` RPC 換成 Tunnel Frontend (TFE) HTTP ping（在 `colab.research.google.com` 上以使用者的 bearer 權杖驗證的 `GET /tun/m/<endpoint>/keep-alive/`，帶 `X-Colab-Tunnel: Google`）。舊 RPC 需要對 Colab 內部專案的 `serviceusage` 消費者存取權，對每個外部使用者都回傳 HTTP 403 `USER_PROJECT_DENIED`，導致他們的工作階段在幾分鐘內就被閒置修剪。TFE ping 不需要任何專案資格；因為虛擬機器在此路徑上通常不會回應，`ReadTimeout` 會被視為成功，真正的 HTTP 錯誤則會往外傳播。（#14, #61）

### 移除

- 已死的 grpc-web 用戶端登錄／API 金鑰程式碼路徑，以及現在已無關的 `colaboratory` 範圍／`pa.googleapis.com` 預檢修復訊息，已被 TFE keep-alive ping 取代。（#61）

[0.7.0]: https://github.com/googlecolab/google-colab-cli/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/googlecolab/google-colab-cli/compare/v0.5.11...v0.6.0
