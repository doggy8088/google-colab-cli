---
name: colab-operator
description: 透過 `colab` CLI 操作 Google Colab 環境。在被要求建立或管理 GPU/TPU 工作階段、在遠端 Colab 虛擬機器上執行 Python/shell、同步檔案、自動化環境設定（套件、驗證、Drive），或匯出工作階段歷史時使用。
---

# 技能：Colab 工作階段操作員

透過 `colab` CLI 操作 Google Colab 環境：配置 GPU/TPU 工作階段、在虛擬機器（VM）上執行 Python/Shell、同步檔案，並將成果擷取為 Jupyter 筆記本（Notebooks）。

## 安裝

若使用者尚未安裝 `colab` 工具，可執行 `uv tool install google-colab-cli` 或 `pip install google-colab-cli` 取得。

## 何時啟用
- 建立或管理 TPU/GPU 工作階段時。
- 在遠端 Colab 虛擬機器上執行 Python 或 Shell 指令時。
- 在本地與遠端之間同步檔案時。
- 自動化環境設定時（包含安裝套件、身分驗證與掛載雲端硬碟 Drive）。
- 將工作階段歷史紀錄匯出為 Jupyter 筆記本時。

## 心智模型（請先閱讀此處）
- **工作階段 == 在租用的虛擬機器上運作的作用中 Jupyter 核心。** `colab new` 會配置需要計費的虛擬機器；`colab stop` 則會釋放該資源。只要核心仍在活動，工作階段就會保持存活，Colab 後端會自動維持其存活狀態。
- **核心狀態在同一個工作階段中呼叫 `colab exec` / `colab repl` 時將會「持續存在」（PERSISTS）。** 每次調用都會重新附加至「同一個」核心（核心 ID 會快取在本地狀態中），並且只在退出時關閉 WebSocket 連線——它**不會**關閉核心本身。因此，在不同的 `colab exec` 指令之間，匯入的模組、變數和定義的函式皆能留存。您可以漸進式地建構狀態，無需每次調用都重新匯入所有內容（實際重設狀態請使用 `colab stop` 與 `colab restart-kernel`）。
- **預設工作目錄為 `/content`。** 每次執行 `exec`/`repl`/`run` 都會先 `cd` 至此目錄；進行檔案操作時請優先使用絕對路徑（`/content/...`）。對於 `colab ls/rm/upload/download` 指令，絕對路徑 `/content/...` 皆可正常運作，且預設的 `ls` 路徑為 `content`（即 VM 根目錄）。
- **`colab` 採用即發即忘（Fire-and-forget）機制。** 每個指令會進行身分驗證、執行單一任務，然後退出。

## 身分驗證（AI 代理最常遇到的阻礙）
- 全域旗標為 `--auth={oauth2,adc}`，且**預設值為 `oauth2`**。若要使用應用程式預設憑證，請將 `--auth=adc` 置於子指令*之前*：`colab --auth=adc new -s x`。
- **ADC 設定**（`--auth=adc`，適用於無介面/代理運作，最穩定可靠）：Colab 後端需要特定的權限範圍（Scope），因此請使用以下全部四種權限範圍重新鑄造 ADC：
  ```bash
  gcloud auth application-default login \
      --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory
  ```
  為什麼需要這四種：`colaboratory` 與 `userinfo.email`（工作階段後端 `colab.research.google.com` 必需，否則回傳 401 錯誤）、`openid` + `cloud-platform`（`gcloud` 本身強制要求；它會拒絕遺漏 `cloud-platform` 的權限範圍清單）。
- **OAuth2 設定**（預設）：首次呼叫 `colab <任何指令>`（或 `colab --auth=oauth2 <任何指令>`）時會觸發瀏覽器授權同意流程（權杖透過 `keyring` 快取在 OS 金鑰圈中）。需要在 `~/.colab-cli-oauth-config.json`（或透過 `-c 路徑` 指定）準備好用戶端設定，並退回使用搭售的設定。瀏覽器授權需要人工介入，因此代理程式請優先使用 `--auth=adc`。
- **一鍵驗證憑證**：使用 `colab sessions`（唯讀，列出伺服器端分配）或 `colab whoami`（隱藏的除錯指令：印出作用中的電子郵件、權限範圍、受眾與過期時間）。當任何呼叫回傳 401 或 403 錯誤時，幾乎都是因為缺少憑證或權限範圍——`colab whoami` 能立即揭示問題所在。
- **請勿將 `colab auth` 與 CLI 本身的身分驗證混淆。** `colab auth` 是將 *VM 端* 的 GCP 憑證注入執行中的核心（以便筆記本程式碼呼叫 BigQuery/GCS）；這與 CLI 本身的身分驗證方式完全無關。絕不可建議使用者「執行 `colab auth`」來修復 CLI 遇到的 401/403 錯誤——該錯誤是權限範圍/身分識別問題，應使用上方的 `gcloud` 指令進行修復。

## 工作流程

### 配置（Provision）
- `colab new -s <工作階段名稱>`（建立 CPU 虛擬機器）。加上 `--gpu A100` 或 `--tpu v6e1` 可啟用加速器。**請務必傳遞 `-s <工作階段名稱>`**——若省略名稱，系統會自動生成隨機的 6 位 16 進位字串作為名稱，這會導致後續指令產生歧義。
- 支援的 `--gpu` 選項：`T4`、`L4`、`G4`、`H100`、`A100`。支援的 `--tpu` 選項：`v5e1`、`v6e1`。
- **常見陷阱**：若輸入了無法識別的 `--gpu` 值，系統會靜默地退回使用 **A100**（這通常會因為配額問題在下一步失敗）。如果在帶有加速器的 `colab new` 中收到 `400` 錯誤，通常代表該帳戶沒有對應的配額或授權——請改用 `--gpu T4` 或省略旗標以使用 CPU。
- 加速器的可用性受到訂閱層級的限制；多數帳戶僅能取得 CPU。請勿預設 GPU/TPU 一定能成功配置。

### 執行（Execute）
- **推薦方式**：`colab exec -s <工作階段名稱> -f <腳本.py>` 會在遠端 VM 上執行本地的腳本（在本地讀取並傳送至核心——無需手動上傳）。
- **管線程式碼**：`echo "print(1)" | colab exec -s <工作階段名稱>` 或 `cat script.py | colab exec -s <工作階段名稱>`。
- **Jupyter 筆記本**：`colab exec -s <工作階段名稱> -f nb.ipynb` 會執行每個程式碼儲存格，並在輸入檔案旁寫入名為 `<主檔名>_output.ipynb` 的結果。儲存格首行的 `# @title 標題` 會作為進度輸出的標籤。
- **結束狀態**：`colab exec` 會以 CPython 語意傳播結束狀態碼，與 `colab run` 一致：未捕捉的例外以 `1` 結束，`sys.exit()`／`sys.exit(0)` 無聲地以 `0` 結束，`sys.exit(N)` 以 `N` 結束，`sys.exit("msg")` 會將 `msg` 印至 `stderr` 並以 `1` 結束（常駐的 IPython 核心會將 `SystemExit` 回報為錯誤訊息以保持存活，因此 CLI 會將其轉譯回來，而不是讓 `argparse`／`unittest` 這類 `sys.exit(0)` 腳本失敗）。執行 `.ipynb` 筆記本時會在第一個非零狀態碼的儲存格處停止，但仍會寫入 `<主檔名>_output.ipynb`。IPython 的 `!cmd` Shell 跳脫在 Shell 以非零狀態結束時**不會**發出核心錯誤——若 Shell 結束狀態重要，請改用 `colab ssh -s <工作階段名稱> -- <指令>` 或 `subprocess.run(..., check=True)`。
- **圖表/圖片**：系統會攔截 PNG/JPEG 輸出。在 `exec`/`repl` 時使用 `--output-image <路徑>` 可以將圖片儲存至指定路徑（否則會印出暫存路徑）。當 stdout 非 TTY 時，終端機內聯圖片逸出字元會被自動抑制，以確保管線或擷取的輸出保持乾淨。
- **Shell**：使用 `colab ssh -s <工作階段名稱> -- <指令>` 執行單次 Shell 指令：它會在 `/content` 中執行，並以該指令的狀態結束。當 stdout 被管線傳輸或重新導向時，輸出會逐位元組精確；ssh 只在 stdin 與 stdout 都是終端機時才配置 PTY，因此在終端機中執行指令的 shell 工具應加上 `</dev/null` 並將輸出重新導向到檔案（管線只有在 `set -o pipefail` 下才保留 `colab ssh` 的結束狀態）。一個參數是一行 shell 指令（管線或 glob 請加引號：`colab ssh -s <工作階段名稱> -- 'nvidia-smi | head -5'`）；多個參數是精確的 argv，因此不可信的值請在程式接受的位置以獨立參數放在 `--` 之後傳入（例如 `colab ssh -s <工作階段名稱> -- ls -- "$f"`），永遠不要放在 shell 行或管線腳本裡面。將多行腳本管線傳給 `colab ssh -s <工作階段名稱> -- bash`。Python 程式碼請使用 `colab exec`。當 ssh 無法運作時（沒有本地 `ssh` 用戶端、沒有 `~/.ssh/id_ed25519` 或 `id_ecdsa` 金鑰且沒有 `-i KEY`、工具不在精簡 ssh 環境的 `PATH` 上如 `gcloud` 或 `node`，或執行期有限的並行 SSH 連線已被使用，伺服器會以 429 回覆，例如有人或 IDE 已連線時），請退回使用帶 IPython `!` 前綴的 `exec`：`echo '!df -h /content' | colab exec -s <工作階段名稱>`（單引號可阻止您的本地 shell 展開 `!`）。每一行 `!` 都在自己的 shell 中執行且沒有輸入（會提示的指令會掛起），IPython 即使在引號內也會將 `{expr}` 評估為 Python，並在單引號外展開 `$name`。多行腳本請以 `%%bash` 行開頭（不要用 `--env`，它會前置 Python 行），使用非互動旗標如 `apt-get -y`，且永遠不要將不可信文字放在 `%%bash` 腳本或 `!` 行中（即使透過 `{var}` 或 `$var`）：請以 `--env NAME=VALUE` 傳入，並從 Python 執行 `subprocess.run(["cmd", "--", os.environ["NAME"]])`。若要在 VM 上使用互動式 shell，請由人類執行 `colab ssh -s <工作階段名稱>`。
- **AI 代理切勿以互動方式執行 `colab repl`、沒有 `-- CMD` 的 `colab ssh`、`colab auth` 或 `colab drivemount`**——`repl`、`auth` 與 `drivemount` 需要 TTY，否則會掛起或失敗，而沒有已儲存工作階段的裸 `colab ssh` 會建立會計費的執行期；互動式 shell 是給人類用的。`repl` 支援管線 `stdin` 且會在 EOF 時退出；而 `auth`/`drivemount` 則必須由人類在終端機前操作。

### 臨時性單次任務（`colab run`）
- `colab run [--gpu T4] [--tpu v6e1] [--keep] [-s 名稱] script.py [參數...]` = 將 `new` + `exec` + `stop` 整合於單一指令中。它會配置一個乾淨的 VM、以傳入的 `sys.argv` 執行該腳本、並將 `__name__ == "__main__"` 設為與原生 `python script.py args` 一致，最後拆除該 VM（除非指定了 `--keep`）。
- **結束代碼傳播**：若腳本中發生未捕獲的異常或呼叫了 `sys.exit(N)`，`colab run` 會以非零代碼結束（符合 CPython 語意：`sys.exit()`/`sys.exit(0)` → 0，`sys.exit(N)` → N，`sys.exit("訊息")` → 1）。
- **串流分離**：`colab run` 會將其自身的 `[colab] ...` 雜訊寫入 **stderr**，而腳本的實際輸出則會寫入 **stdout**——因此使用 `colab run job.py > out.txt` 僅會擷取到腳本的 stdout。（而 `colab exec` 則是將腳本的 stdout/stderr 即時串流至您的 stdout/stderr）。
- **支援 Shebang**：在腳本首行加上 `#!/usr/bin/env -S colab run --gpu T4`，並執行 `chmod +x`，即可將該 `.py` 檔案轉化為「租用 GPU、執行、清理收尾」的自包含腳本。在修改 CLI 行為後，請先重新安裝再測試 Shebang——它們會透過 `$PATH` 解析 `colab`，而非專案的可編輯安裝。
- 若指定了不存在的腳本路徑，系統會在配置 VM **之前**以非零代碼結束（避免浪費運算資源）。

### 自動化（Automate）
- `colab auth -s <工作階段名稱>` —— VM 端 GCP 憑證，在 VM 內部呼叫 GCS/BigQuery 之前必需（具互動性，代理無法自主執行）。
- `colab drivemount -s <工作階段名稱> [掛載路徑]` —— 預設將雲端硬碟掛載於 `/content/drive`（具互動性，代理無法自主執行）。
- `colab install -s <工作階段名稱> 套件1 套件2` —— 透過 `uv pip install --system` 進行安裝，並會退回使用 `pip`。亦支援 `colab install -s <工作階段名稱> -r requirements.txt`。

### 檢查與回報（Inspect & report）
- `colab help`（或 `colab help <指令>`）會列出/解釋指令；清單按字母順序排列。
- `colab sessions` 會列出伺服器端的分配，並自動清除過期的本地記錄。沒有本地記錄的孤兒工作階段會顯示為 `[?]`。
- `colab status [-s <工作階段名稱>]` 顯示硬體、閒置/忙碌狀態（IDLE/BUSY）以及最後執行時間。
- `colab log -s <工作階段名稱> [-n 20] [-t 類型]` 顯示最近的結構化事件；在任務失敗時極具價值。
- `colab log -s <工作階段名稱> -o summary.ipynb` 將工作階段匯出為筆記本（亦可透過副檔名匯出為 `.md`、`.txt`、`.jsonl`）。
- `colab url -s <工作階段名稱>` 會印出瀏覽器網址，可以將 Colab 網頁 UI 附加至您現有的 CLI 工作階段，而無需重新配置新 VM（加上 `--open` 可直接開啟）。
- `colab skill` / `colab readme` 會印出此技能與 README 說明檔（方便自主探索）。

## 安全規範（Safety）
- **完成工作後，務必執行 `colab stop -s <工作階段名稱>`** —— 閒置的虛擬機器會持續消耗您的運算單位。`colab run`（未指定 `--keep` 時）即使在腳本出錯時也會自動清理。
- 本地狀態儲存於 `~/.config/colab-cli/sessions.json`（設定儲存於 `settings.json`，歷史紀錄儲存於 `history/*.jsonl`）。請勿手動修改這些檔案。
- **使用全域 `--config <路徑>` 旗標進行平行/代理執行的隔離**，將工作階段狀態指向一個臨時檔案（例如 `colab --config /tmp/agent.json new -s job`）。

## 復原機制（Recovery）
- 執行時遇到 "Session not found" / 404 / 401 錯誤：代表後端已回收該虛擬機器。`colab exec`/`repl` 會偵測到此情況並自動清理本地狀態——此時請執行 `colab sessions` 並使用 `colab new` 重新建立。
- 執行逾時或核心卡死：執行 `colab restart-kernel -s <工作階段名稱>`（保留 VM，重設核心），或者執行 `colab stop` 隨後 `colab new`。
