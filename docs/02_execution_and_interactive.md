---
log:
2026-11-23：與 `colab exec` 共用 `colab run` 的 CPython `SystemExit` 處理（`_exit_code_from_outputs`、`_make_script_output_hook`），並在 `exec` 設定期間靜默 IPython 的 `"To exit: use ..."` 警告。由於常駐的 IPython 核心會捕捉 `SystemExit` 並以 `output_type == "error"` 發出以避免終止核心行程，將每個核心錯誤輸出都視為結束狀態 1，會錯誤地使呼叫 `sys.exit(0)` 的腳本（例如 `argparse --help`、`unittest.main()`）失敗，並將 `sys.exit(N)` 的狀態碼壓縮為 1。

2026-11-23：`colab exec` 現在會在執行的程式碼產生核心 `error` 輸出時以狀態碼 1 結束（先記錄歷史紀錄，並為筆記本儲存 `*_output.ipynb`、停止執行後續的筆記本儲存格）(#250)。

2026-05-07：修復了 `colab console` 管線 `stdin` 的處理。先前透過管線調用（例如 `echo 'cmd' | colab console -s s`）會在發送指令後無限掛起，因為舊版的 EOF 處理常式僅發送了單純的 `\x04` (Ctrl-D)，而遠端在 tmux 中包裝的 Bash 會將其視為一般字元，而非工作階段終止符。新版的處理常式會發送 `exit\n`（此為 Bash 能實際結束的指令），並在短暫的寬限期（`PIPED_EOF_GRACE_SECONDS = 0.5s`）後從用戶端關閉 WebSocket，確保殘留的輸出（如 Bash 的 `logout`、tmux 的 `[exited]`）能順利傳回給使用者。TTY 模式則保持不變：真實終端機的 EOF 仍留給遠端 Shell 處理。已在實體環境驗證：`echo 'echo HELLO' | colab console -s s` 現在可在約 1.2 秒內結束而不再掛起。

2026-05-07：修復了 `print_kitty`（由 `colab exec --output-image` 與任何會產生圖片的 exec 使用），使其在 `sys.stdout.isatty()` 為 false 時執行無操作（No-op）。當 stdout 為檔案或管線時，Kitty 圖形協定的逸出序列毫無意義，且會視覺上破壞所擷取的輸出（數 KB 的 Base64 PNG 區塊會掉進日誌檔案、grep 目標或展示擷取中）。圖片位元組仍會透過 `handle_image` 的檔案寫入路徑儲存至磁碟；僅抑制了終端機內聯顯示的嘗試。

2026-06-04：將 `colab exec` 的預設 `--timeout`（以及對應的 `colab run` 預設值）從 10 秒提升至 30 秒，以降低簡短且安靜的任務遭遇過早觸發 `TimeoutError` 的機率。明確指定 `--timeout` 的覆寫設定不受影響。

2026-10-24：`colab exec`（與 `colab run`）的 `--timeout` 現在是「閒置上限」：只有在無輸出達該秒數時執行才會失敗，所以持續印出輸出的程式碼永遠不會被中途切斷，且 `--timeout 0` 表示不設上限。在 0.8.0／0.9.0 上舊的期限從未被強制執行，因此安靜時間超過 `--timeout` 的程式碼，現在會失敗，而過去可以完成。`colab repl` 與 `colab install` 不傳入逾時，會等到執行完成，或等到核心死亡或重啟為止。它們在等待時都不會忙碌迴圈。`colab auth` 與 `colab drivemount` 不變。見 #183。

2026-10-29：移除了 `colab console` 子指令及其 `/colab/tty` 傳輸（`console.py`、其測試與 `integration/repro_piped_console/`）。互動式 shell 請改用 `colab ssh -s NAME`，單次指令請用 `colab ssh -s NAME -- CMD`，或在 ssh 無法使用時，將加上 `!` 前綴的 shell 指令以管線傳給 `colab exec`。
---

# 設計文件：執行與互動式互動 (`repl`, `exec`)

## 概述
執行涉及將 Python 程式碼（或 Shell 指令）傳送至在 Colab VM 上執行的 Jupyter 核心（Jupyter Kernel），並處理輸出的訊息串流。

## 實作方法

### 1. REPL (`colab repl`)
- **傳輸協定**：WebSocket（若允許，使用 `websockets` 函式庫；若嚴格要求僅用標準庫，則使用基於 `http.client` 的自訂長輪詢實作）。
- **通訊**：Jupyter 核心訊息協定（Jupyter Kernel Messaging Protocol）。
    - `execute_request`：傳送程式碼字串。
    - `execute_reply`：獲取執行狀態。
    - `iopub.stream`：擷取 `stdout` 與 `stderr`。
- **互動模式**：使用標準 Python 的 `cmd.Cmd` 或 `code.InteractiveConsole` 來處理本地的輸入與輸出。
- **管線支援**：偵測 `sys.stdin.isatty()`。若非 TTY，則讀取所有輸入並將其作為單一執行請求傳送。

### 2. 執行 (`colab exec`)
- **檔案處理**：
    - 若檔案路徑為本地：讀取內容，並將其作為程式碼傳送。
    - 若檔案路徑為遠端：執行 `!python <path>`。
- **多模態輸出**：處理 `display_data` 訊息（例如 `image/png`、`text/html`）。對於 CLI 而言，我們會將圖片儲存至暫存檔案並印出其路徑；若終端機支援（例如 iTerm2），則將圖片內聯（Inline）顯示。
- **逾時設定**：暴露 `--timeout` 旗標（預設為 30 秒）：執行失敗前允許的最長安靜時間。請提高此值，讓執行時間較長且無輸出的任務（如模型編譯或資料下載）不會過早被終止；`0` 表示不設上限。
- **錯誤與 `SystemExit` 語意**：
    - 任何未捕捉的例外（`ValueError`、`SyntaxError` 等）都會使 `colab exec` 以狀態碼 `1` 結束
    - 任何回傳 `output_type == "error"` 的已執行程式碼區塊都會使 colab 以狀態碼 `1` 結束
    - 任何結束狀態碼都會停止 `.ipynb` 筆記本中剩餘的儲存格，同時仍會寫入 `*_output.ipynb`。
    - **為何 `SystemExit` 需要特別處理**：與 CPython 不同——在 CPython 中 `sys.exit(...)` 會直接終止行程——IPython/Jupyter 核心必須在多次執行之間保持存活，因此它會捕捉 `SystemExit` 並將其回報為 `output_type == "error"`（`ename == "SystemExit"`），同時伴隨互動式的 `"An exception has occurred, use %tb..."` 橫幅與 `"To exit: use 'exit', 'quit', or Ctrl-D."` `UserWarning`。將 `SystemExit` 視為未捕捉的例外，會破壞傳給 `colab exec -f script.py` 的正規腳本（例如 `argparse --help`、`unittest.main()`，或呼叫 `sys.exit(0)` 的提早結束守衛），並遺失自訂的整數結束狀態碼（`sys.exit(N)`）。因此 `colab exec` 共用 `colab run` 的 CPython 對應：`sys.exit()`／`sys.exit(None)`／`sys.exit(0)` 會無聲地以 `0` 結束，`sys.exit(N)` 會以 `N` 結束，`sys.exit("msg")` 會將 `msg` 印至 `stderr` 並以 `1` 結束。

## 實作細節
- **核心管理**：`ColabRuntime`（來自 `colab-agent`）已負責處理訊息簽署與訊息類型。
- **輸出串流**：採用持續輪詢或非同步訊息處理，以提供即時的輸出呈現。
- **管線範例**：`cat script.py | colab exec -s my-session`。

## 測試策略
所有執行相關功能皆必須遵循測試驅動開發（TDD）。

### 1. 模擬核心用戶端
- **測試案例**：驗證 `ColabRuntime` 是否能正確透過 WebSocket 傳送 `execute_request` 訊息。
- **測試案例**：驗證 `iopub.stream` 訊息是否被正確處理並即時印出至 `stdout`。
- **測試案例**：驗證 `display_data`（特別是 `image/png`）是否觸發正確的本地處理（儲存或顯示）。
- **測試案例**：驗證當核心發出 `error` 輸出時，`colab exec` 會以狀態碼 1 結束，並在失敗的儲存格處停止多儲存格 `.ipynb` 的執行，同時仍儲存 `*_output.ipynb`。
- **測試案例**：驗證 `colab exec` 套用 CPython 的 `SystemExit` 語意（`sys.exit(0)`／`None` → 無聲地以 `0` 結束、`sys.exit(N)` → `N`、`sys.exit("msg")` → 將 `msg` 印至 `stderr` 並以 `1` 結束），且不帶 IPython 的 `%tb` 或結束警告雜訊。

### 2. TTY 與管線傳輸
- **測試案例**：模擬 `sys.stdin.isatty()` 以驗證 `colab repl` 是否能正確在互動模式與單次管線執行之間切換。
- **測試案例**：驗證大型管線輸入是否被妥善處理，且不會發生緩衝區溢位或內容擷斷。
- **測試案例**：當 `sys.stdout.isatty()` 為 false 時，`print_kitty` 執行無操作（迴歸預防：先前會將 ANSI/Base64 發射至管線與檔案中）。
