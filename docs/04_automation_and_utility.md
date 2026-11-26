---
log:
2026-11-19：新增 `colab logout`，可清除儲存於所有串連的作業系統金鑰圈後端中的 OAuth2 憑證（區分遺失的項目與真實的 keychain/KWallet 失敗，並在 `NoKeyringError` 時發出警告），以及舊版 `~/.config/colab-cli/token.json`，且不會撤銷 Google Cloud SDK 共用的 OAuth 用戶端授權。在 `--auth=adc` 下，會印出 `gcloud auth application-default revoke`。同時會使 `sessions.json` 中快取的執行期代理權杖失效（若仍有本地工作階段會發出警告）、重設 `settings.json` 中快取的 API 能力旗標，並抑制每日自動更新橫幅。
2026-11-13：`auth.py` 中的 `_get_adc_credentials` 現在會捕捉 `google.auth.default()` 的 `DefaultCredentialsError`，因此缺少本地 ADC 時會印出帶 4 個範圍的 `gcloud auth application-default login` 指令並以 1 結束，而不是呈現 `google-auth` 預設的無範圍設定訊息。更新了範圍文件，澄清 `colaboratory` 與 `userinfo.email` 都是 `colab.research.google.com` 所必需的。
2026-11-07：優化 `auth.py` 中的 `_get_adc_credentials`，在 `google.auth.default()` 周圍 stub `google.auth._cloud_sdk.get_project_id`。當 ADC 使用者憑證缺少 `quota_project_id` 時，`google-auth` 否則會在每次 CLI 呼叫時生成 `gcloud config get-value project`，以解析一個 `_get_adc_credentials` 隨即丟棄的 `project_id`（`_`）。
2026-11-04：`colab drivemount` 現在會在系統瀏覽器中開啟 Drive 同意網址（`utils.open_url_in_browser`，也供 `colab pay`/`colab url --open` 使用），而不是只印出它。網址仍會先印出，缺少瀏覽器開啟程式（SSH、容器、CI）視為正常：流程會像以前一樣繼續等待使用者。提示已移入 `commands/automation.py::show_drive_auth_url`，使其可做單元測試。
2026-11-04：`colab drivemount` 現在會處理憑證傳播失敗，而不是傾印 HTTP 主體。回應會被防禦性解析（HTML/空主體不再從 websocket hook 拋出），只有在伺服器確實回傳 `unauthorized_redirect_uri` 時才顯示驗證提示，失敗時會印出狀態加上多帳戶指引（從 `colab whoami` 選擇帳戶），同時將原始主體記錄到歷史。被攔截的核心請求在失敗時也會被回覆，因此指令會迅速結束，而不是掛到其 600 秒逾時。
2026-11-02：新增 `auth.py` 中的 `_check_linux_keyring_locked`，在 `get_password`/`set_password` 之前透過 `secretstorage` 檢查作用中的 Linux `SecretService` 集合，在金鑰圈鎖定時立即警告，讓使用者知道 CLI 為何在等待解鎖提示（並建議 `--auth=adc`）。
2026-10-29：工作階段歷史檔案以只有擁有者可讀的方式建立（0600），既有檔案會在歷史記錄器每次啟動時收緊為 0600。
2026-10-22：新增隱藏的 `colab test-public-api` 子指令與 `Client.check_api_access()`，探測 `colaboratory.googleapis.com/v1beta/runtimes` 與 `colab.research.google.com/tun/m/assignments`，並在 `Settings` 中快取 `public_api_supported` 與 `tunnel_api_supported`，以提供針對性的 HTTP 401/403 錯誤提示。
2026-10-21：將 `auth.py` 中的 OAuth2 權杖持久化從 `~/.config/colab-cli/token.json` 遷移到透過 `keyring` 函式庫的 OS 原生密碼儲存（`KEYRING_SERVICE_NAME = "google-colab-cli"`、`KEYRING_USERNAME = "oauth_token"`）。當金鑰圈為空、已鎖定或無法存取時，會呼叫 `_run_remote_flow`；金鑰圈讀寫失敗會在 stderr 印出警告，但不會讓指令失敗。既有的 `~/.config/colab-cli/token.json`（`LEGACY_TOKEN_PATH`）會在金鑰圈沒有權杖時使用、複製進入金鑰圈，且只在金鑰圈寫入成功後刪除；當金鑰圈已有權杖時也會刪除它。
2026-09-25：清理了 keep-alive 背景守護行程與預檢 ping 的參考。虛擬機器存活由 Colab 後端依作用中的核心活動自動維持。
2026-08-10：透過工作階段後端上的 `GET /tun/m/ccu-info`（與 `colab new` 相同的 bearer 權杖），新增用於帳戶層級運算單位速率／餘額的 `colab usage`。
2026-06-11：將 `oauth2` 提供者的 `run_local_server()`（localhost 重新導向）換成遠端複製貼上流程（`auth.py` 中的 `_run_remote_flow`）。CLI 現在會印出以 `redirect_uri=https://sdk.cloud.google.com/applicationdefaultauthcode.html` 與 `token_usage=remote` 建構的授權網址，然後透過 `input()` 讀取貼上的授權碼，並以 `flow.fetch_token(code=...)` 交換它。這與 `gcloud auth application-default login` 使用的流程相同，在本地與遠端／無頭／容器環境中運作方式一致，移除了是否自動開啟瀏覽器的啟發式判斷。已透過對搭售的 cloud-SDK 用戶端（`764086051850-...`）的真實 GET-only 檢查確認伺服器端接受；OOB 重新導向與非搭售用戶端 id 都已驗證會被拒絕（`OOB flow has been blocked` / `redirect_uri_mismatch`）。`tests/test_auth.py` 中的單元測試斷言不會啟動 localhost 伺服器、重新導向 URI + `token_usage=remote` 有被設定，且貼上的代碼有被交換。
2026-06-01：除了 Linux 之外，在 macOS 上也啟用了 `colab update --install` 自主更新。重構了平台檢查邏輯以維持實作的 DRY 原則，並更新了測試與相關文件。此外，在這些支援的平台上，會在標準的 `pip`/`uv` 安裝指令上方，額外顯示一條建議使用 `colab update --install` 進行就地升級的提示訊息。
2026-05-29：將預設的 OAuth2 用戶端設定（`oauth_config.json`）作為搭售的套件資源加入，並在 `get_credentials()` 中恢復了遞補載入邏輯。現在，當找不到明確的本地設定時，CLI 會遞補使用這些預設憑證。加入了 `integration/repro_bundled_oauth` 整合測試。
2026-05-27：重構了 `colab README` 與 `colab AGENT`，透過 Hatchling 的 `force-include` 設定搭售 `README.md` 與 `AGENTS.md`，並使用 `importlib.resources` 代替 `importlib.metadata` 進行讀取。現在 `colab AGENT` 已能正確印出 `AGENTS.md`。
2026-05-27：擴充了 `colab update --install`，以偵測 CLI 是否透過 `uv tool install` 安裝（藉由檢查 `sys.executable` 是否包含 `/uv/`），若是，則使用 `uv tool install -U google-colab-cli` 進行升級。
2026-05-27：更新了自動更新升級提示，改為建議執行 `pip install --upgrade google-colab-cli` 而非 `colab`，以與 PyPI 套件名稱保持一致。
2026-05-27：`colab url` 現在會**同時**發射 `?dbu=<urlencoded path>` 查詢參數（既有）與全新的 `#datalabBackendUrl=<full URL>` 雜湊片段（新增）。格式為：`https://<host>/notebooks/empty.ipynb?dbu=%2Ftun%2Fm%2F<endpoint>#datalabBackendUrl=<host>/tun/m/<endpoint>`。為什麼同時需要兩者：部分 Colab 前端程式碼路徑會優先查閱雜湊片段並完全忽略 `dbu`，因此先前僅發射查詢參數的形式對這些使用者而言會無聲失敗（前端會退而配置全新的 VM，即 `/tun/m/assign`）。雜湊片段的值是包含配置與主機的**完整網址**（而不僅僅是路徑），並且是以**原始格式**（未經 URL 編碼）發射，因為瀏覽器在將 `location.hash` 傳遞給頁面 JS 之前不會解碼雜湊片段——Colab 的解析器會直接呼叫 `new URL(rawString)`。雜湊片段的主機一律與 `--host` 匹配，因此 Colab 對嵌入式後端網址的同源政策強制執行不會阻擋該連線，且沙箱/開發使用者（`--host https://colab.sandbox.google.com`）會自動獲得沙箱雜湊片段。在 `tests/test_url.py` 中新增了三個測試案例，涵蓋了原始編碼需求（雜湊片段中不得出現 `%3A`/`%2F`）、雙重訊號同時存在的不變性，以及 `--open` 將雜湊片段傳播至 `webbrowser.open()` 的行為。已針對三種主機形態（預設、沙箱、帶尾隨斜線）與合成的工作階段狀態進行即時整合驗證；全部皆產生了格式正確的網址，且沒有產生任何 `//` 雜訊。
2026-05-07：新增了開發者專用的 `colab whoami` 子指令（在 `colab --help` 中隱藏）。透過與 CLI 其他部分相同的 `auth.get_credentials(...)` 路徑（遵循全域 `--auth=...` 旗標）鑄造存取權杖、重新整理憑證，隨後查詢 `https://oauth2.googleapis.com/tokeninfo`，以印出 CLI 即將發送之任何權杖的電子郵件、權限範圍、受眾與過期時間。此指令專為縮短「為什麼我對 colab.pa.googleapis.com 的呼叫一直回傳 403」的偵錯循環而建——答案幾乎總是「遺漏權限範圍」或「身分錯誤」，這兩者在 `whoami` 下皆能立竿見影。透過 `app.command(hidden=True)` 隱藏；可透過 `colab whoami` 或 `colab whoami --help` 存取。本指令已從每日更新橫幅檢查中排除（加入至 `cli.py` 的 `_AUTO_UPDATE_SUPPRESSED` 中），以防橫幅遮蔽了驗證輸出。
2026-05-11：移除了本地檔案更新來源（`update_file_path` 設定與 `_fetch_local` 輔助常式）；`colab update` 現在僅查詢 PyPI。將預設的 `update_url` 切換至規範的 PyPI JSON API（`https://pypi.org/pypi/google-colab-cli/json`），該 API 已暴露了自動更新子系統所預期的 `info.version` Schema。重新加入 `colab update --install` 作為公開的自我安裝路徑，其針對目前的 `sys.executable` 執行 `pip install -U google-colab-cli`；此功能僅限 Linux 與 macOS，其他平台將以非零狀態碼退出並顯示解釋訊息。當快取的 `latest_version` 已經等於或低於目前安裝版本時，此旗標為無聲的無操作，因此可以安全地寫入自動化流程中。若升級指令以非零狀態碼結束，`colab update --install` 會傳播相同的結束代碼。
2026-05-12：在 `ColabRuntime.execute_code` 中加入了選用的 `timeout=` 參數，該參數會流向 `execute()` 與 `execute_interactive()` 兩個分支。`colab auth` 與 `colab drivemount` 現在會透過 `commands/automation.py` 中共享的 `INTERACTIVE_AUTOMATION_TIMEOUT_SEC` 常數傳遞 `timeout=600`（10 分鐘）。背景脈絡：`jupyter_kernel_client` 預設有 10 秒的實際時間（Wall-clock）逾時，即使核心處於閒置並等待 `input_request` 時也會消耗該時間。在 drivefs 掛鉤攔截該請求並提示使用者在瀏覽器中進行 OAuth 驗證時，任何花費超過 10 秒進行點擊授權的使用者（基本上是所有人）都會遭遇 `TimeoutError` 並看到「drivemount 失敗」，即便後端掛載實際上已經成功。此修復僅限縮於這兩個需要人工介入的子指令；非互動式路徑（`colab exec`、`colab run`、`colab install`、`colab repl --pipe`、`colab console --pipe`）仍維持上游預設值，因為它們會接收到能重設實際無活動上限的持續 iopub 流量。
---

# 設計文件：自動化與工具 (`auth`, `install`, `log`, `pay`, `usage`, `version`, `update`, `whoami`)

## 概述

這些子指令是透過在 Colab 虛擬機器上執行 Python 程式碼、管理本地狀態，或檢查環境來實作的。

## 身分驗證策略（CLI 後端）

CLI 支援兩種與 Colab 後端通訊的身分驗證策略，可透過全域的 `--auth=<provider>` 旗標進行選擇：

1.  **`oauth2`**（預設）：透過 `google-auth-oauthlib` 進行公開的 `InstalledAppFlow`，但以**遠端複製貼上流程**執行，而不是 localhost 伺服器。CLI 會印出授權網址（帶 `token_usage=remote`），使用已註冊的 HTTPS 落地頁 `https://sdk.cloud.google.com/applicationdefaultauthcode.html`；使用者登入、複製 Google 顯示的代碼，並在提示處貼回。重新整理權杖透過 `keyring` 函式庫（`service_name="google-colab-cli"`、`username="oauth_token"`）快取在 OS 原生金鑰圈中，在金鑰圈無法存取或已鎖定時退回執行 `_run_remote_flow`。在 Linux 上，`_check_linux_keyring_locked` 會在讀取或寫入之前透過 `secretstorage` 檢查作用中的 `SecretService` 集合，若集合在等待解鎖提示時已鎖定，會立即印出警告。金鑰圈讀寫失敗會印出到 stderr，因為寫入失敗意味著使用者會在每個指令都被再次提示。留在金鑰圈出現之前路徑 `~/.config/colab-cli/token.json` 的權杖會在第一次使用時遷移進入金鑰圈，且檔案會在金鑰圈寫入成功後刪除（寫入失敗時保留）。若金鑰圈已有權杖，舊檔案會被刪除。這與 `gcloud auth application-default login` 使用的機制相同，在本地、遠端、無頭與容器主機上行為一致（不自動開啟瀏覽器、不綁定連接埠）。我們刻意**不**使用 `run_local_server()`（依環境而定）或帶外（OOB）重新導向 `urn:ietf:wg:oauth:2.0:oob`（Google 已於 2022 年封鎖 — 見 `auth.py` 中的 `_run_remote_flow` / `REMOTE_REDIRECT_URI`）。`sdk.cloud.google.com` 重新導向註冊給 cloud-SDK OAuth 用戶端（`764086051850-...`），它也是搭售 `oauth_config.json` 中附帶的用戶端；以任何其他用戶端 id 重用它會產生 `redirect_uri_mismatch`。若未透過 `-c/--client-oauth-config` 提供本地設定，也未在 `~/.colab-cli-oauth-config.json` 找到，系統會退回使用該搭售的 `oauth_config.json`。
2.  **`adc`**：透過 `google.auth.default()` 取得應用程式預設憑證（Application Default Credentials）。遵循標準的 ADC 探索鏈（`GOOGLE_APPLICATION_CREDENTIALS`、`gcloud auth application-default login`、GCE/GKE 中繼資料伺服器）。當從已經具備 Google 憑證環境的環境中執行 CLI 時非常實用。

這些選項在 `auth.py` 中被編碼為 `AuthProvider` 字串列舉（String-enum）。`get_credentials(config_path, provider)` 進入點會依據此列舉進行分派，使核心 `Client` 得以保持驗證無涉（Authentication-agnostic）——它僅需要看見一個 `requests.AuthorizedSession`。

### 必需的權限範圍（Scopes）

CLI 與位於 `colab.research.google.com` 的 Colab 工作階段後端通訊，進行配置、取消配置、CCU 資訊與 Contents API。此主機同時需要 `colaboratory` 與 `userinfo.email` 兩個範圍。

各提供者如何提供這些範圍：

-   **`oauth2`**：`PUBLIC_SCOPES` 同時包含 `colaboratory` 與 `userinfo.email`，因此 InstalledAppFlow 同意畫面會列出它們。在範圍變更之前鑄造、快取於金鑰圈中的既有權杖必須被清除，以觸發全新的同意流程。
-   **`adc`**：呼叫 `google.auth.default(scopes=PUBLIC_SCOPES)`，對於支援 `with_scopes` 的憑證子類別（服務帳戶、GCE/GKE 中繼資料、冒充憑證），我們透過 `creds.with_scopes(...)` 重新套用。自 `gcloud auth application-default login` 取得的使用者憑證會忽略 `scopes=` 參數，且在 `with_scopes` 上會拋出 `NotImplementedError`；這些使用者必須明確地重新驗證：

    ```bash
    gcloud auth application-default login \
        --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory
    ```

    位於 `colab.research.google.com` 的工作階段後端需要 `colaboratory` 與 `userinfo.email`（否則配置/取消配置/查詢工作階段將回傳 HTTP 401）；`openid` 與 `cloud-platform` 則是 `gcloud` 本身強制要求（`gcloud auth application-default login` 會拒絕遺漏 `cloud-platform` 的範圍清單，並顯示 `Invalid value for [--scopes]`）。

## 實作方法

### 1. 身分驗證 (`colab auth`)

-   **動作**：在虛擬機器上執行程式碼，以使用傳統的 Gcloud 退回路徑觸發使用者互動式驗證。
-   **程式碼**：
    ```python
    import os
    os.environ['USE_AUTH_EPHEM'] = '0'
    from google.colab import auth
    auth.authenticate_user()
    ```
-   **處理方式**：將 `USE_AUTH_EPHEM` 設定為 `'0'` 會強制核心印出標準的 `gcloud` 驗證網址，並在 `iopub` 通道上觸發 `input_request` 訊息。CLI 透過 `stdin_hook` 攔截此訊息並在本地提示使用者，回傳驗證碼以解鎖核心執行緒。

### 2. 套件安裝 (`colab install`)

-   **動作**：在虛擬機器上執行 `pip`。
-   **程式碼**：
    ```python
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "..."])
    ```
-   **Requirements 檔案**：若透過 `-r` 提供了 `requirements.txt`，則先上傳該檔案，接著執行 `pip install -r`。

### 3. 雲端硬碟掛載 (`colab drivemount`)

-   **動作**：執行 `drive.mount()` 並透明地代理 Colab 專屬的憑證傳播流程。
-   **程式碼**：
    ```python
    from google.colab import drive
    drive.mount('/content/drive')
    ```
-   **處理方式**：由於 `drivefs` 強制執行基於 WebSocket 的臨時旁路憑證傳播（`colab_request` 訊息），CLI 透過 `ColabRuntime.colab_request_hook` 攔截這些訊息。一旦攔截，CLI 會自動與 Colab 後端（`/tun/m/credentials-propagation/`）進行互動，在需要時提示使用者 Google OAuth 同意網址，並向 `stdin` 通道派送所需的 `colab_reply` 訊息，以解鎖核心執行緒。同意網址也會傳給 `webbrowser.open`（見 `utils.open_url_in_browser`）；當沒有瀏覽器開啟程式可用時（SSH、容器、CI），網址會留在畫面上，流程會像以前一樣繼續等待使用者。
-   **逾時**：在使用者於瀏覽器中進行 OAuth 驗證的整個過程中，核心是靜默的（沒有 iopub 流量）。為了避免上游 `jupyter_kernel_client` 預設的 10 秒限制在中途引發 `TimeoutError`，此子指令會將 `timeout=INTERACTIVE_AUTOMATION_TIMEOUT_SEC`（600 秒）傳遞至 `ColabRuntime.execute_code`。同樣的設定亦適用於 `colab auth`。
-   **多帳戶瀏覽器**：Drive 傳播歸屬於核准同意頁面的 Google 帳戶，它可能不是 CLI 驗證身分所用的帳戶。若瀏覽器顯示帳戶選擇器，請選擇 `colab whoami` 回報的帳戶；以另一個帳戶核准會以 HTTP 400 失敗，即使同意本身成功。無痕視窗只有在它已登入該帳戶時才有幫助。
-   **失敗回報**：來自傳播端點的錯誤永遠不會回顯原始回應主體（通常是 HTML）。CLI 會印出狀態、指向 `colab whoami`、將主體記錄到歷史檔案，並回覆等待中的核心請求，使 `drivemount` 結束，而不是掛到其逾時為止。

### 4. 日誌與筆記本擷取 (`colab log`)

-   **動作**：擷取工作階段的指令歷史紀錄與輸出。
-   **儲存**：在 `~/.config/colab-cli/history/<session_name>.jsonl` 中維護一個包含所有主要操作、執行與 stdin 互動的本地 JSON-L 檔案，只允許擁有者讀取（模式 0600）。
-   **檢視**：使用 `colab log list` 與 `colab log show <session>`。
-   **轉換（規劃中）**：未來將擴充支援把歷史紀錄日誌轉換為 `.ipynb` 或 `.html`。

### 5. 運算單位使用量 (`colab usage`)

-   **動作**：印出帳戶層級的運算單位（CU）使用率與餘額。
-   **資料來源**：`GET https://colab.research.google.com/tun/m/ccu-info`（餘額、每小時速率、配置數量）。與 `colab new` 相同的 bearer 權杖與工作階段後端。
-   **輸出**：`Current balance: … compute units`、`Usage rate: {rate}/hr`（所有已配置虛擬機器的合計 CU/小時）、`Active assignments: N`。

### 6. 訂閱管理 (`colab pay`)

-   **動作**：在使用者瀏覽器中開啟 Colab 訂閱頁面。
-   **實作**：使用 `webbrowser.open("https://colab.research.google.com/signup")`。

### 7. 版本資訊 (`colab version`)

-   **動作**：顯示 Colab CLI 的目前版本。
-   **實作**：
    -   嘗試使用 `importlib.metadata.version("colab")` 獲取版本。
    -   若未安裝（例如從原始碼執行），則退而使用 `git rev-parse --short HEAD` 取得簡短的 Git 提交雜湊值。
    -   在建置系統中，透過 `hatch-vcs` 支援動態版本控制。

### 8. 自動更新 (`colab update`)

-   **動作**：檢查是否有新版本的 Colab CLI 可用。
-   **自動檢查**：CLI 會在執行任何指令時，每 24 小時自動檢查一次更新。獨立地，在**每次**調用時皆會查閱快取的 `latest_version`（詳見下方說明），以便在不耗費網路來回時間的情況下，使升級橫幅在各次獲取之間保持可見。
-   **隱藏的子指令**：為了保持機器可解析輸出的乾淨，每日獲取與快取的橫幅將對以下指令進行抑制：`update`（執行其自身的檢查）、`version`、`log`、`pay`、`url`、`help` 與 `whoami`。此清單在 `cli.py` 中作為 `_AUTO_UPDATE_SUPPRESSED` 存在於全域 Typer 回呼中。
-   **手動檢查**：`colab update` 強制進行檢查並印出狀態。
-   **實作**：
    -   從可設定的 `update_url`（預設為 `https://pypi.org/pypi/google-colab-cli/json`）獲取 PyPI 風格的 JSON 文件，並讀取 `info.version`。
    -   使用 PEP 440 / 語意化版本（Semantic versioning）比較獲取的版本與目前的 CLI 版本，在版本無法解析時則退而使用字串等價比較。
    -   將以下欄位持久化儲存於 `~/.config/colab-cli/settings.json`：
        -   `update_url`：來源設定。
        -   `last_check`：上次獲取的時間戳記（用以驅動每日頻率限制）。
        -   `enable_update_check`：每日獲取與快取橫幅的主開關。
        -   `latest_version`：在最近一次成功檢查中觀察到的最高版本。每當觀察到嚴格更新的版本時便會更新（絕不降級），並在檢查失敗時原封不動地保留，以防暫時性網路問題抹除快取。
-   **通知**：若發現新版本，會在主控台印出一條不具侵入性的訊息，並附帶 `請執行 'pip install --upgrade google-colab-cli' 進行更新。` 的提示。在支援 `--install` 自我更新的 Linux 與 macOS 平台上，會在 pip/uv 安裝指令上方額外顯示 `您可以執行 'colab update --install' 進行就地升級。` 的提示。在多次獲取之間顯示的快取橫幅則使用通用的 `請執行 'colab update' 進行更新。` 提示。
-   **自我安裝 (`--install`)**：選用的 `--install` 旗標（預設為 `False`）可使 `colab update` 進行就地升級（僅限 **Linux 與 macOS**）。它會自動偵測 CLI 的安裝方式：
    - 若 `sys.executable` 包含 `/uv/tools`（代表它是透過 `uv tool install` 安裝），它會執行 `uv tool install -U google-colab-cli`。
    - 否則，使用 `sys.executable` 執行 `pip install -U google-colab-cli`，確保升級至相同的直譯器中。
    在其他平台上，該指令會以非零狀態碼結束並顯示解釋訊息。當快取的 `latest_version` 已經等於或低於目前安裝版本時，該旗標是無聲的無操作，因此可以安全地寫入自動化流程中。若升級指令以非零狀態碼結束，`colab update --install` 會傳播相同的結束代碼。

### 9. 身分檢查 (`colab whoami`) [僅限開發者]

-   **動作**：解析目前作用中的憑證、鑄造存取權杖，並印出該權杖的電子郵件、受眾、權限範圍與過期時間。
-   **能見度**：以 `hidden=True` 註冊，因此不會出現在 `colab --help` 中。可透過檢視原始碼、`colab whoami --help` 或口耳相傳來發現。其目的是保持公共介面專注於終端使用者指令，同時仍為開發者提供一個一鍵偵錯的利器。
-   **實作**：
    -   呼叫 `auth.get_credentials(state.client_oauth_config, provider=state.auth_provider)`——此為與 `Client` 所使用的完全相同之程式碼路徑——確保權杖反映了 CLI 實際傳送的內容。
    -   在讀取 `creds.token` 之前，務必先呼叫 `creds.refresh(Request())`。服務帳戶、GCE/GKE 中繼資料與某些冒充憑證採用延遲鑄造（Lazy-mint）權杖；若無明確的 refresh 呼叫，即使憑證有效，`creds.token` 仍會是 `None`。
    -   透過標準庫的 `urllib.request` 存取 `https://oauth2.googleapis.com/tokeninfo?access_token=<token>`，而非使用已授權的 `requests.AuthorizedSession`。因為 tokeninfo 端點接受將權杖作為查詢參數，且不需要附帶 `Bearer` 標頭。
    -   將 `expires_in`（秒）轉換為分鐘以提高可讀性。
    -   當 tokeninfo 回傳 HTTP 4xx（常見於遭撤銷或過期的權杖）時，JSON 格式的錯誤主體會原封不動地呈現，而非被靜默吞掉；開發者需要看見權杖被拒絕的*原因*。
-   **輸出格式**：
    ```
    Auth provider: adc
    Email:         user@example.com
    Audience:      764086051850-...apps.googleusercontent.com
    Expires in:    47m
    Scopes:
      - email
      - https://www.googleapis.com/auth/cloud-platform
      - https://www.googleapis.com/auth/colaboratory
      - https://www.googleapis.com/auth/userinfo.email
      - openid
    ```

### 10. README 與 AGENT 指令 (`colab README`, `colab AGENT`)

-   **動作**：印出搭售的 `README.md` 或 `AGENTS.md` 檔案。
-   **實作**：
    -   使用 `importlib.resources.files("colab_cli").joinpath(...)` 從套件資源中讀取搭售的 `README.md`（用於 `colab README`）或 `AGENTS.md`（用於 `colab AGENT`）。
    -   這些檔案是透過 `pyproject.toml` 中 Hatchling 的 `force-include` 設定搭售至套件中。
    -   若從資源讀取失敗（例如在未安裝的開發階段），則會退而從專案根目錄讀取檔案。
    -   將內容印出至 stdout。

### 11. Public 與通道 API 探測 (`colab test-public-api`)

-   **動作**：隱藏的診斷指令（`hidden=True`，從自動更新橫幅抑制），執行 `state.client.check_api_access()`。
-   **實作**：
    -   對 `https://colaboratory.googleapis.com/v1beta/runtimes` 與 `https://colab.research.google.com/tun/m/assignments` 發出唯讀 GET 探測。
    -   將 `public_api_supported` 與 `tunnel_api_supported` 布林值持久化於 `~/.config/colab-cli/settings.json`，並為每個後端印出 `OK` 或 `FAILED`。
    -   當 `Client._issue_request` 收到 HTTP 401/403 時，它會更新失敗後端的快取旗標，並在另一後端被快取為受支援時，附加針對性的修復提示（`--no-public-api` 或 `--public-api`）。

### 12. 登出 (`colab logout`)

-   **動作**：清除本地快取的 OAuth2 憑證與快取的執行期代理權杖，讓使用者能在下一個指令登出或切換帳戶。
-   **實作**：
    -   在 `--auth=oauth2`（預設）下，刪除所有串連金鑰圈後端中的 `(google-colab-cli, oauth_token)`（區分遺失的項目與真實的 keychain/KWallet 錯誤，並在 `NoKeyringError` 時於 stderr 發出警告），並移除任何殘留的 `~/.config/colab-cli/token.json`，即使其中一個儲存區出錯，也會嘗試兩個儲存區。不會呼叫 Google 的 `/revoke` 端點，因為內建的 OAuth 用戶端與 Google Cloud SDK 共用。
    -   在 `--auth=adc` 下，不動本地 ADC，並指引使用者執行 `gcloud auth application-default revoke`。
    -   清空本地 `sessions.json` 項目中快取的 `token` 與 `token_expires_at`（使 `-s 名稱` 無法以過期的代理權杖繞過重新驗證）、重設 `settings.json` 中快取的 `public_api_supported`／`tunnel_api_supported` 旗標，若存在本地工作階段會在 stderr 發出警告。
    -   從每日自動更新橫幅中排除（`_AUTO_UPDATE_SUPPRESSED`）。

## 實作細節

-   **程式碼注入**：透過 `ColabRuntime` 使用標準的 `run_code(session, code)` 輔助常式。
-   **歷史紀錄管理**：使用 `HistoryLogger` 類別將結構化事件附加至工作階段專屬的 `.jsonl` 檔案中。
-   **互動式提示**：配置了 `stdin_hook` 與 `colab_request_hook`，以記錄互動式使用者輸入與專有的後端請求。

## 測試策略

所有自動化相關功能皆必須遵循測試驅動開發（TDD）。

### 1. 模擬核心注入

-   **測試案例**：驗證 `colab auth` 是否正確注入 `from google.colab import auth; auth.authenticate_user()`。
-   **測試案例**：驗證 `colab install` 是否正確向遠端 VM 核心注入 `pip install` 或 `uv install` 指令。
-   **測試案例**：驗證 `colab drivemount` 是否正確注入 `drive.mount()` 指令，並註冊 `colab_request_hook` 以攔截憑證傳播事件。

### 2. 歷史紀錄擷取

-   **測試案例**：驗證所有透過 `exec` 傳送的程式碼是否皆被正確附加至該工作階段的 JSON-L 歷史紀錄檔案中。
-   **測試案例**：驗證 `colab log` 是否能正確從已填入資料的歷史紀錄檔案中產生 `.ipynb`。

### 3. `whoami` 身分解析

-   **測試案例**：模擬憑證與 `urllib.request.urlopen` 以回傳虛擬的 tokeninfo 承載資料；驗證印出的輸出是否包含電子郵件、作用中的驗證提供者名稱、權限範圍（每行一個），以及人類可讀的過期時間（分鐘，而非原始秒數）。
-   **測試案例**：當 `urlopen` 引發 `HTTPError(400)`（權杖遭撤銷/過期）時，`whoami` 會以非零狀態碼退出並顯示指明失敗的訊息，而非拋出未處理的 Traceback。
-   **測試案例**：驗證 `colab --help` 不會提及 `whoami`（防止意外解除隱藏的迴歸測試），但 `colab whoami --help` 仍能顯示該指令自身的說明文字。
-   **測試案例**：在讀取 `creds.token` 之前已呼叫了 `creds.refresh()`（防止針對服務帳戶/GCE 中繼資料憑證產生無聲的 `None` 權杖）。

### 4. `README` 與 `AGENT` 指令

-   **測試案例**：驗證當套件中繼資料可用時，`colab README` 是否印出預期內容。
-   **測試案例**：驗證 `colab AGENT` 是否印出相同內容。
-   **測試案例**：驗證當中繼資料不可用時，是否能退而讀取本地的 `README.md` 檔案。
-   **測試案例**：驗證當中繼資料與本地檔案皆不可用時，是否能以錯誤狀態碼退出。

### 5. `logout` 帳戶登出

-   **測試案例**：驗證 `clear_oauth_token()` 會移除兩個金鑰圈項目（包括跨 `ChainerBackend` 後端者）與 `LEGACY_TOKEN_PATH`，能乾淨地處理並行的 `FileNotFoundError` 與 macOS 的 `NotFound`，並在不跳過其餘儲存區的情況下，重新引發被鎖定／拒絕／取消的 `PasswordDeleteError` 與 `OSError`。
-   **測試案例**：驗證 `colab logout` 會使 `sessions.json` 中快取的執行期權杖失效、重設 `settings.json` 中快取的能力旗標、抑制自動更新檢查、將警告／錯誤發送至 stderr，並在 `--auth=adc` 下印出 `gcloud` 提示。
