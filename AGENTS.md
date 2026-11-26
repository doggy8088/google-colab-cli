# Colab CLI：AI 代理開發指引

## 架構概述
- **CLI**：基於 `Typer` 的模組化進入點，位於 `cli.py`，其子指令定義於 `commands/` 目錄中。
- **Common**：`common.py` 集中管理共享的 `State`（採用延遲載入 lazy-loading 機制）與工作階段解析（Session Resolution）。
- **Client**：`ColabClient` 負責處理 API 互動（包含資源的分配與取消分配）。
- **Auth**：`auth.py` 暴露單一的 `get_credentials(config_path, provider)` 外觀模式（Facade）介面，依據 `AuthProvider` 列舉進行分派。支援兩種提供者，透過全域的 `--auth=oauth2|adc` 旗標選取（預設為 `oauth2`）：
  - `oauth2`：公開的 `google-auth-oauthlib` `InstalledAppFlow`，權杖透過 Python `keyring` 函式庫（`service_name="google-colab-cli"`、`username="oauth_token"`）快取在 OS 金鑰圈中，在金鑰圈無法存取或已鎖定時退回 `_run_remote_flow`（金鑰圈失敗會回顯到 stderr；只有日誌會進檔案；在 Linux 上，`_check_linux_keyring_locked` 會事先透過 `secretstorage` 檢查，並在 `SecretService` 集合鎖定時立即警告）。金鑰圈出現之前的 `~/.config/colab-cli/token.json`（`LEGACY_TOKEN_PATH`）會遷移進入金鑰圈，且只在金鑰圈寫入成功後刪除，或在金鑰圈已有權杖時立即刪除。整合腳本假設不存在舊檔案，並透過只看金鑰圈的 `has_oauth2_token` 輔助函式偵測 OAuth2 可用性；遷移路徑由 `integration/repro_legacy_token_migration/test.sh` 涵蓋（隔離的 HOME + 檔案型測試金鑰圈）。必須忽略主機金鑰圈的測試會設定 `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`。它從 `-c/--client-oauth-config`（預設 `~/.colab-cli-oauth-config.json`）讀取用戶端 OAuth 設定，並退回使用**搭售的** `src/colab_cli/oauth_config.json` 資源（在 PR #41 / `9f44fe2`，2026-05-29 重新加入 — 先前「在 `20eb88e` 移除」的註記已過時／不正確；該檔案存在，且 `auth.py:_get_google_auth_credentials` 透過 `importlib.resources` 載入它）。自 2026-06-11 起，此流程是**遠端複製貼上流程**，不是 localhost 伺服器：`_run_remote_flow` 設定 `redirect_uri=https://sdk.cloud.google.com/applicationdefaultauthcode.html` + `token_usage=remote`，印出網址，並透過 `input()` 讀取貼上的代碼。永遠不要退回 OOB（`urn:ietf:wg:oauth:2.0:oob`）— Google 已於 2022 年封鎖它（「OOB flow has been blocked」）；`sdk.cloud.google.com` 重新導向只註冊給搭售的 cloud-SDK 用戶端（`764086051850-...`），因此任何其他用戶端 id 都會得到 `redirect_uri_mismatch`。這些變體在伺服器端的接受／拒絕可透過只用 GET 建構授權網址，並檢查 Google 是抵達登入還是 OAuth 錯誤頁面來驗證（不配置任何資源）。
  - `adc`：透過 `google.auth.default()` 取得 Google 應用程式預設憑證。CLI 會傳入 `scopes=PUBLIC_SCOPES`（包含 `colaboratory`），並對支援的憑證類型透過 `creds.with_scopes()` 重新套用。**透過 `gcloud auth application-default login` 鑄造的使用者憑證會忽略 `scopes=` 參數，且在 `with_scopes` 上拋出 `NotImplementedError`**：ADC 使用者必須明確地以 `gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory` 重新驗證。`colaboratory` 與 `userinfo.email` 都是位於 `colab.research.google.com` 的工作階段後端所必需的（缺少時 assign/unassign/sessions 回傳 401）；`openid` 與 `cloud-platform` 是 `gcloud` 本身強制要求的，它會拒絕遺漏 `cloud-platform` 的範圍清單，並顯示 `Invalid value for [--scopes]`。服務帳戶 / GCE / GKE / 冒充憑證透過 `with_scopes` 透明地取得正確範圍。
- **後端主機**：
  - `colab.research.google.com`（工作階段後端 / `tun/m/...`）：需要 `colaboratory` 與 `userinfo.email` 範圍。處理 assign、unassign、CCU 資訊與 contents API。
- **Runtime**：`ColabRuntime` 包裝 `jupyter-kernel-client` 以執行程式碼。
- **State**：
  - `StateStore` 將工作階段中繼資料持久化儲存於 `~/.config/colab-cli/sessions.json`。
  - 持久化設定則儲存於 `~/.config/colab-cli/settings.json`。
- **History**：`HistoryLogger` 將結構化事件記錄於 `~/.config/colab-cli/history/*.jsonl`。

## 核心準則
- **極簡主義**：在可行的情況下優先使用標準函式庫（例如 `urllib`），同時利用 `Typer` 提供優雅的 CLI 使用體驗。
- **管線傳輸**：一律考慮管線輸入（`stdin`）與互動式 TTY 的處理差異。
- **軌跡對齊**：在實作新的端點時，請對照擷取自瀏覽器的網路軌跡（HAR 檔案）進行驗證。
- **測試驅動開發 (TDD)**：務必堅持「先寫測試，後寫程式」。在實作解決方案使其通過之前，請先確認測試是否確實失敗。每項設計都必須包含測試策略與具體的測試案例。

- **Jupyter 協定偏離**：Google Colab 對 Jupyter 協定進行了自訂擴充。例如在 `iopub` 通道上傳送 `colab_request` 訊息，以及在 `stdin` 通道上將 `colab_reply` 負載包裝於 `input_reply` 中。這些都需要在 `jupyter-kernel-client` 中進行猴子補丁（Monkey-patching）或使用特定的處理常式（例如 `wsclient.kernel_socket.on_message` 攔截器）。

- **整合測試**：僅靠單元測試與模擬（Mock）是不夠的。在宣告任何功能開發完成之前，您**必須**使用 CLI 對真實的 Colab 環境進行實際且端對端的整合測試。切勿僅依賴模擬的單元測試來驗證功能的正確性。
    - 整合測試位於 `integration/`（例如 `integration/repro_plot_redirection/test.sh`）。
    - 要執行整合測試，請使用：`uv run bash integration/repro_<name>/test.sh`。
    - `uv run` 可確保 `colab` 指令（進入點）在 shell 環境中可用。
- **持續改進**：每當使用者提供回饋、工作流程建議或修正時，請立即將該建議編碼記錄至本 `AGENTS.md` 檔案中。其目標是從檢討中學習，絕不重複相同的錯誤。

## 工具與工作流程
- **工作流程**：
    1. **草案**：規劃並開始任務。在著手開發新功能或變更之前，請先建立一個新的 git 分支。
    2. **精煉**：實作變更並透過測試和 Lint 進行驗證。使用 `uv run pytest tests/` 執行測試，並使用 `uv run ruff check . --fix` 修正所有程式碼排版與靜態分析錯誤。
    3. **完成**：確保一切完整且正確。**每當新增功能或變更行為時，您必須重新審閱 `docs/` 中對應的設計文件，並將其更新以反映最新狀態。您也應該在更新後的設計文件 frontmatter 中，新增簡短的日誌記錄，並附上當前日期以摘要該變更。** 最後，將完成的變更提交至 git 分支以供審查。

## 子指令工作流程
- **工作階段管理**：`new`、`sessions`、`status`、`stop`。
- **執行**：`repl`、`exec`、`ssh`。
- **檔案管理**：`ls`、`rm`、`upload`、`download`、`edit`。
- **自動化與工具**：`auth`、`drivemount`、`install`、`log`、`pay`、`version`、`update`。

## 發佈標籤工作流程
套件版本透過 `hatch-vcs` 從 git 標籤產生（見 `pyproject.toml`），因此一次發佈就是 (1) 一筆 `CHANGELOG.md` 條目，以及 (2) 在已合併提交上的一個 `vX.Y.Z` 標籤。只有當使用者明確要求發佈時（例如「cut a release」、「tag v0.7.0」）才遵循此工作流程。永遠不要主動提議或執行發佈。

1. **驗證乾淨、最新的 `main`**：`git fetch origin && git checkout main && git pull --ff-only origin main`。確認 `git status` 乾淨。若 `main` 已分歧，或有使用者期望納入發佈的未合併功能分支，停下來詢問。
2. **識別未發佈的提交**：以 `git describe --tags --abbrev=0` 找出最後一個發佈標籤，然後以 `git log <last-tag>..HEAD --oneline` 列出自那之後的提交。這些就是新變更記錄章節必須涵蓋的內容。交叉比對每個提交的 PR 編號（合併提交主旨中的 `(#NN)` 後綴）— 變更記錄中的每個條目都應引用至少一個 PR。
3. **推斷下一個版本（semver）**：使用 `CHANGELOG.md` 中已有的 Keep-a-Changelog 分類（`Added`、`Changed`、`Fixed`、`Removed`、`Deprecated`、`Security`）為每個提交分類。選擇升級幅度：主版本（`X.0.0`）為 CLI 介面、旗標語意、磁碟狀態 schema（`sessions.json` / `settings.json`）或持久化權杖格式的任何重大變更；次版本（`0.X.0`）為至少一個 `Added` 條目（新子指令、新旗標、新能力）且沒有重大變更；修訂版（`0.0.X`）為只有 `Fixed`、`Changed`、`Removed`（非重大清理）、`Deprecated` 或 `Security` 條目。在繼續之前先與使用者確認推斷出的版本 — 永遠不要在未經確認的情況下打標籤，即使升級幅度看似明顯。
4. **在分支上草擬並提交 CHANGELOG 條目**：建立發佈分支（例如 `release-v0.7.0`），然後在前一個版本上方前置一個新的 `## [X.Y.Z] - YYYY-MM-DD` 章節。依 `CHANGELOG.md` 中已建立的順序（`Changed`、`Added`、`Fixed`、`Removed`）將條目分組。每個項目應是一小段，說明使用者可見的行為變更（不是實作細節），並以 PR 參考 `(#NN)` 結尾。在底部附加新的連結參考：`[X.Y.Z]: https://github.com/googlecolab/google-colab-cli/compare/v<PREV>...vX.Y.Z`。以訊息 `docs: add CHANGELOG.md for vX.Y.Z release` 提交，推送分支，並以 `gh pr create` 開 PR。
5. **等待變更記錄 PR 合併**：不要在您分支上的合併前提交打標籤。標籤必須落在出現在 `main` 上的 squash-merge 提交上（這是 `hatch-vcs` 會看到的，也是使用者會 `git checkout` 的）。在使用者回報 PR 已合併（或您透過 `gh pr view <num> --json state,mergeCommit` 觀察到）之後，執行 `git fetch origin && git checkout main && git pull --ff-only origin main`。
6. **為已合併的變更記錄提交打標籤並推送標籤**：驗證 `git log -1 --oneline` 是已合併的變更記錄提交（主旨符合 `docs: add CHANGELOG.md for vX.Y.Z release (#NN)`）。建立一個註解標籤，其訊息是變更記錄章節主體：`git tag -a vX.Y.Z -m "vX.Y.Z" -m "<changelog section body>"`。以 `git push origin vX.Y.Z` 推送。不要透過 `gh release create` 建立 GitHub Release 條目 — 光是標籤就足夠了，因為 `hatch-vcs` 直接讀取它，且正式的發佈說明已存在於 `CHANGELOG.md` 中。
7. **驗證**：執行 `git describe --tags --exact-match HEAD`（應印出 `vX.Y.Z`）與 `uv run colab version`（版本字串應相符）。以 `gh api repos/googlecolab/google-colab-cli/tags --jq '.[0].name'` 確認該標籤在遠端可見。

## 實作原則
1. **直接執行**：用於 `auth`、`drivemount` 等的程式碼，應注入並直接在虛擬機器核心（VM Kernel）上執行。
2. **內容 API**：如瀏覽器軌跡所示，使用 Jupyter Contents API 進行檔案管理。
3. **透明儲存**：本地狀態必須可透過旗標進行覆寫。
4. **不使用 netrc**：在此專案中，避免使用 `netrc` 來儲存持久化的權杖（Token）。
5. **模擬互動性**：在測試會根據 `stdin.isatty()` 進行分支的指令時，請使用 `execution.py` 中的 `is_stdin_tty` 輔助函式，並透過 `mocker.patch("colab_cli.commands.execution.is_stdin_tty", return_value=...)` 進行模擬。這可確保測試不會在 CI/代理環境中掛起。
6. **狀態隔離**：在測試中務必對 `colab_cli.common.state` 單例（Singleton）進行補丁，以控制工作階段的持久化與用戶端行為。請參考 `tests/conftest.py` 了解標準全域 fixture 的設定。
7. **即發即忘架構**：Colab CLI 是一款「即發即忘」（Fire-and-forget）的工具。在指令流程中，請避免使用背景執行緒或持久守護行程。指令會進行驗證、執行其任務，然後乾淨地結束。
8. **驗證本地安裝**：全域安裝的 `colab` 可能存在於 `PATH` 中（例如在 `~/.local/bin/colab`），當從儲存庫外部調用 `uv run` 時，它可能會遮蔽專案的「可編輯安裝」（Editable install）。**務必**將儲存庫作為工作目錄來執行 shell 指令（例如透過 `workdir` 參數，絕不要使用 `cd && cmd`），使 `uv run colab ...` 能正確解析為 `.venv/bin/colab`。如果 CLI 測試產生非預期的結果（例如對於您剛新增的旗標出現「無法識別旗標」的錯誤），請透過 `which colab` 與 `uv run which colab` 進行確認。**Shebang 的調用一律透過 `$PATH` 解析**，因此即使可編輯安裝是最新的，像 `#!/usr/bin/env -S colab run ...` 這樣的腳本仍會讀取到舊的全域工具。在修改程式碼後測試基於 Shebang 的行為時，請務必先執行 `uv tool install --reinstall --force --from . colab`，然後使用 `colab version` 進行驗證（版本字串包含 git 的簡短 SHA）。*此條款記錄於 2026-05-12，起因於 `examples/hello_colab.py` 中 SystemExit 抑制修正似乎未生效，經查發現 shebang 解析至釘死在前一提交的 uv-tool 安裝版本。*
9. **先隔離迴歸**：當使用者回報您剛修改的程式碼出現錯誤時，**請勿**直接假設是您的變更造成的。首先，請在 `main` 分支（或分支點）上重現該錯誤，以判斷此 Bug 是否為既有問題。只有在確認該迴歸確實由您造成之後，才開始偵錯新程式碼。*此條款記錄於：花費了一輪對話偵錯「ADC 導致 `colab new` 壞掉」後，才發現 `colab new --gpu A100` 在 `main` 分支上本來就因為 A100 配額與預設問題而失敗，與 ADC 完全無關。*
10. **真實探測會分配實際資源**：探測 Colab API 以進行偵錯會建立真實且會計費的分配（Assignment）——每次成功的 POST `/tun/m/assign` 都會保留一台虛擬機器。在可行時，應優先使用唯讀（GET）的探測。對於任何會變更狀態的呼叫：(a) 隨時記錄您所建立的每個端點，並 (b) 在宣告調查結束前，透過 `client.unassign(endpoint)`（或 `colab stop`）進行清理。接著使用 `colab sessions` 驗證沒有任何遺留的孤兒工作階段。
11. **推送新鮮度**：遠端儲存庫可能會在您開發期間被推入新變更（其他貢獻者在您工作時合併了提交）。在推送或合併之前，**務必**立即執行 `git fetch <remote>`。如果 `git log main..<remote>/main` 不為空，請將本地 `main` 重設為遠端狀態，並將特徵分支 Rebase 到其上，重新測試後再推送。**切勿**強制推送（Force-push）`main` 分支以解決分歧。
12. **修改（Amend）安全性**：在執行 `git commit --amend` 之前，請明確驗證以下三個前提條件：(a) 使用者要求 Amend，或 pre-commit hook 自動修改了本應成功提交的檔案，(b) HEAD 是由您在此對話中建立的（`git log -1 --format='%an %ae'`），(c) 該提交尚未被推送到遠端。若任一前提不成立，請建立新提交。**切勿**修改失敗或被拒絕的提交——請修正問題並建立新提交。
13. **親自執行整合測試**：在宣稱無法自主執行測試之前，請重新閱讀 AGENTS.md 的「代理執行限制」。不允許執行的指令清單僅限於互動式指令（`colab auth`、`colab drivemount`、未管線的 `colab repl`、互動式 `colab ssh`）。基於 `colab new` / `colab stop` / `colab log` 構建的測試皆為非互動式，您**必須**在宣告修復完成前親自執行它們。*此條款記錄於：在完成一輪實作與文件更新後，才發現若花 30 秒執行整合測試就能當場推翻該修復——正確的解藥是 `uv run bash integration/repro_run_command/test.sh`。*
14. **重視調研警告**：當研究子代理提出警告時（例如「協定允許，但策略可能會拒減」），請將其視為一項待辦事項（TODO）進行驗證，而非僅作為腳註。驗證模式為：使用擬議的輸入實際對真實服務執行 shell 指令，並在編寫依賴該行為的程式碼**之前**，確認其回應是否符合預期。對於策略受限的路徑，在著手設計前請先執行單次探測。
15. **兩種截然不同的驗證機制——絕不可混淆**：本儲存庫有兩個互不相關的驗證關注點：(a) **CLI 到 Colab 控制平面**：`Client` 如何對 `colab.research.google.com` 與 `colab.pa.googleapis.com` 的 HTTP 請求進行身分驗證。這由全域的 `--auth={oauth2,adc}` 旗標與 `auth.py:get_credentials` 所驅動。當金鑰圈中沒有儲存權杖（或 `keyring` 無法存取）時，OAuth2 路徑會在首次呼叫時由 `google_auth_oauthlib` 的 `InstalledAppFlow` 自動引導；**不需要單獨執行任何指令**——任何 `--auth=oauth2` 的呼叫（例如 `colab --auth=oauth2 sessions`）皆會觸發瀏覽器授權同意流程。(b) **VM 端憑證**：`colab auth` 子指令如何將使用者的 GCP 憑證注入執行中的 Colab 核心，以便筆記本程式碼（例如 `gcloud`、BigQuery 用戶端）可以在 VM 內部進行身分驗證。這會透過 `ColabRuntime` 在核心上執行 `USE_AUTH_EPHEM='0'` 預設退回路徑。**絕不可告訴使用者「請執行 `colab auth`」來作為解決 CLI 端驗證問題的前置步驟**——它們是完全不同層級的機制，此建議會誤導使用者。
16. **Pydantic 驗證需要 Schema**：`_issue_request` 接受選用的 `schema=`，且歷來無條件地呼叫 `TypeAdapter(schema).validate_python(...)`。當 `schema=None` 時（亦即呼叫者不在意回應主體——例如 unassign 或回傳 `[]` 的即發即忘端點），這會引發 `pydantic.ValidationError: Input should be None`。請務必在空主體捷徑之後，加上 `if schema is None: return` 的防護。
17. **提交後建議使用分支差異審查指令**：使用者會透過 `git diff main..<branch-name>` 審查變更（相對於 `main` 的完整累積差異，而非僅是最新提交）。在特徵分支上提交一次或多次變更後，**務必**建議精確的指令——例如「使用 `git diff main..sort-help-commands` 進行審查」——而非 `git show <sha>`（這僅能顯示單個提交，並在分支有多個提交時遺漏脈絡）。*此條款記錄於 2026-05-05，起因於為一個使用者希望整體審閱的分支建議了 `git show 9d9c7da`。*
18. **對研調工具的說法進行首要來源驗證**：研調工具與 AI 助理有時會給出極度自信卻錯誤的答案，特別是針對其訓練語料庫之外的邊緣案例或功能。當此類工具指出「X 未被使用/未被解析/不存在」時，請將其視為一項待驗證的假設，而非事實。請務必對照首要來源（實際程式碼或設定檔）進行交叉比對——且當工具提及檔案名稱時，請檢查它所描述的間接調用鏈是否確實存在。相信工具錯誤說法的代價是交付不合用的功能，而重複確認的成本極低。*此條款記錄於 2026-05-05，起因於第一版 `colab url` 因為未經驗證的輸出而交付了錯誤的 URL 格式。*
19. **在結束即時測試前清理孤兒分配**：在執行即時整合測試後，`colab sessions` 可能會顯示伺服器端的分配，而本地的 `colab stop` 無法偵測到它們（例如從對話早期洩漏的分配，或來自先前崩潰的執行）。務必將執行 `colab sessions` 作為最終的清理步驟，且對於任何標示有 `[?]` 的孤兒，請執行 `python -c "from colab_cli.common import state; state.client.unassign('<endpoint>')"`（CLI 並未直接提供依端點取消分配的指令）。重新驗證並確認 `colab sessions` 回傳「無作用中工作階段」。*此條款記錄於 2026-05-05，起因於第一版 `colab url` 即時測試遺留了先前對話輪次的孤兒，這會導致該資源閒置並計費。*
20. **透過 `context_settings` 在 Typer 中轉發未知參數**：除非另行設定，否則 Typer/Click 會將任何以 `-`/`--` 開頭的語彙基元（Token）視為父指令的旗標。對於像 `colab run script.py --some-script-flag` 這樣的子指令（其中 `--some-script-flag` 屬於使用者的腳本，而非 `colab`），請使用 `app.command(name="run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})` 進行宣告，並使用 `Annotated[Optional[List[str]], typer.Argument(...)] = None` 接收該位置參數。此外，在將這些轉發的字串嵌入到核心端的 Python 原始碼時，請使用 `repr()`（而非 f-字串插值）——不論使用者在 shell 中傳遞了何種引號、反斜線或非 ASCII 位元組，`repr()` 皆能產生安全且可還原的字面量（Literal）。*此條款記錄於 2026-05-12，於實作 `colab run` 時記錄。*
21. **將工作拆成小型 PR/提交**：將多步驟變更分解成小型、自包含的 PR 或提交，使每個步驟都容易獨立審查與驗證。
22. **簡潔程式碼且不寫單行註解**：撰寫簡潔、自解釋的程式碼，且不要撰寫單行註解。只在真正需要解釋非顯而易見的不變條件時，才使用 docstring 或多行說明。

## AI 代理執行限制 (我可以與我不能執行的操作)
作為透過非互動式 shell 工具（`run_shell_command`）運作的 AI 代理，在無需人工介入的情況下，我的自主測試能力存在嚴格限制：
- **我可以執行：**
  - 自動化測試（`pytest`）、靜態分析（`ruff`）以及無介面執行腳本。
  - 不需暫停等待使用者輸入的子指令（例如 `colab new`、`colab status`、`colab stop`、`colab ls`、`colab install`、`colab exec <file.py>`）。
  - **管線傳輸的 `colab repl`**：自 2026-05-07 起，它支援管線輸入 `stdin` 並在 EOF 時乾淨地退出（`echo 'print(1)' | colab repl -s s`）。未經管線傳輸的互動式版本仍無法自主執行。
  - **單次 shell 指令**：`colab ssh -s s -- cmd` 以非互動方式執行 `cmd` 並以其狀態結束（若您的 shell 工具在終端機中執行指令，請加上 `</dev/null`）；在 ssh 無法運作時，使用 `echo '!cmd' | colab exec -s s`（每一行 `!` 都是自己的 shell，且 IPython 會展開其中的 `{expr}` 與 `$name`）。
  - 特別建構、用於模擬逾時或 API 呼叫的 Mock 腳本。
- **我不能執行（需要使用者協助）：**
  - **`colab auth`**：此指令依賴傳統的 Gcloud 退回路徑 `input_request`（透過 `USE_AUTH_EPHEM='0'`），它會透過 Python 的 `input()` 提示使用者，要求點擊網址、登入並貼回授權碼。我的 shell 工具會在此 `input()` 處無限掛起。
  - **`colab drivemount`**：此指令會透過 `sys.stdin.readline()`（特別是查詢 `/dev/tty` 以確保擷取到輸入）提示使用者，要求在瀏覽器中同意 OAuth 授權後按下 `Enter` 鍵。我的 shell 工具會逾時/掛起以等待鍵入。
  - **互動式（TTY）`colab repl` / `colab ssh`**：當 stdin 是真實終端機時，這些指令會開啟需要即時按鍵串流的互動式工作階段。我的 shell 工具無法支援此模式。（管線傳輸至 `colab repl` 或 `colab exec` 運作正常 — 請參閱上方說明。）

每當處理互動式指令時，我必須建構核心邏輯、撰寫模擬測試，並明確要求使用者在他們的終端機中執行即時測試以驗證成功。
