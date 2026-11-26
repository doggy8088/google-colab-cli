---
log:
2026-11-23：將 CPython 的 `SystemExit` 輔助常式（`_exit_code_from_outputs`、`_make_script_output_hook`）移至 `commands/execution.py`，使 `colab exec` 與 `colab run` 共用相同的結束狀態碼與 `stderr` 訊息語意（包括將非整數 `sys.exit("msg")` 訊息印至 `stderr`）。
2026-09-25：從工作階段的配置與拆除中移除了 keep-alive 守護行程的生成。`--keep` 仍受支援，完成時會跳過取消配置。
2026-08-09：新增 `--high-mem` 旗標（透傳至工作階段建立；受支援時在 assign 時送出 `shape=hm`）。
2026-05-12：設計與實作 `colab run <script.py> [參數...]`。將 `colab new` + `colab exec` + `colab stop` 整合至單一的即發即忘（Fire-and-forget）調用中，使 Python 檔案能以 `#!/usr/bin/env -S colab run` 作為 Shebang 首行，並在全新配置的 Colab VM 上執行。加入了 `--keep`（跳過自動停止）、`--gpu` / `--tpu`（透傳至工作階段建立流程）、`-s/--session`（指定臨時工作階段的名稱），並傳播腳本的結束狀態碼（在核心中發生任何未捕獲異常時回傳非零）。腳本的 `sys.argv` 在核心內部被重新設定，以鏡像反映原生 `python script.py arg1 arg2` 的語意，並將 `__name__` 設為 `"__main__"`。
2026-05-12：實作對腳本主體中 `sys.exit()` / `raise SystemExit(...)` 的原生 CPython 結束代碼語意支援。Colab 核心會將 `SystemExit` 回報為 `output_type=='error'`，若依據舊有邏輯，這會 (a) 印出 IPython 的 Traceback 訊息（`An exception has occurred, use %tb...`）並 (b) 無視整數結束狀態碼而將該次執行標記為失敗。現在：`sys.exit()` / `sys.exit(0)` 將無聲且乾淨地以狀態碼 0 結束；`sys.exit(N)` 以狀態碼 N 結束；`sys.exit('msg')` 以狀態碼 1 結束（與 CPython 一致）。IPython 的 "To exit: use 'exit', 'quit', or Ctrl-D." UserWarning 提示已透過 Prelude 前導程式碼進行過濾。此條款記錄於：在端到端執行 `examples/gpu_hello.py` 並目睹本已成功的 GPU 執行在最後輸出吵雜的 `SystemExit: 0` 追蹤訊息之後。
2026-06-04：將 `--timeout` 旗標的預設值從 10.0s 提升至 30.0s，使短暫但安靜的任務在預設情況下不易遭遇過早被終止。此變更鏡像了對 `colab exec` 的相同修改。
2026-10-24：`--timeout` 現在是閒置上限：只有在無輸出達該秒數時執行才會失敗，所以持續印出輸出的腳本可以依需要執行任意長的時間，且 `--timeout 0` 表示不設上限。CLI 改為自己等待核心訊息，以最長一秒的阻塞切片進行，而不是使用 `jupyter-kernel-client` 的 `execute_interactive`。那個期限涵蓋整個執行過程：1.0.2 會強制執行它，即使執行仍在印出輸出也會在 30 秒後失敗，而 0.8.0／0.9.0 從未強制執行它，超過期限後會以約 100% CPU 輪詢。因此在 0.8.0／0.9.0 上，安靜時間超過 `--timeout` 的腳本現在會失敗（且未指定 `--keep` 時其工作階段會被停止），而過去可以完成。見 #183。
---

# 設計文件：`colab run` —— 相容 Shebang 的單次任務執行

## 設計動機
受到 `llm` shebang 模式的啟發（https://til.simonwillison.net/llms/llm-shebang），使用者應能編寫單個自包含（Self-contained）的 Python 檔案，並在其 Shebang 行中實現：

1. 依據使用者指定的旗標配置 Colab 虛擬機器（CPU / GPU / TPU）。
2. 在該虛擬機器上執行檔案的主體內容。
3. 在執行結束時拆除虛擬機器——除非另有指示。

這是 `colab-cli` 最自然且極致的人體工學體驗：免去繁瑣的樣板程式碼、沒有殘留的工作階段，單一檔案即是最小的工作單元。

## 使用者介面

```
colab run [選項] 腳本 [腳本參數]...
```

| 旗標 | 類型 | 預設值 | 用途 |
|---|---|---|---|
| `SCRIPT` | 位置參數 | — | 本地 `.py` 檔案的路徑。必填。 |
| `SCRIPT_ARGS` | 變長參數 | — | 轉發至腳本、作為 `sys.argv[1:]` 的額外參數。 |
| `-s`, `--session` | 字串 | 自動 | 為臨時工作階段命名（搭配 `--keep` 時非常實用）。若省略，預設自動生成為 `run-<6位16進位>`。 |
| `--gpu` | 字串 | None | 與 `colab new --gpu` 支援的集合一致（T4, L4, G4, H100, A100）。 |
| `--tpu` | 字串 | None | 與 `colab new --tpu` 支援的集合一致（v5e1, v6e1）。 |
| `--high-mem` | 布林值 | False | 與 `colab new --high-mem` 相同 — 受支援時要求高 RAM。 |
| `--keep` | 布林值 | False | 在腳本執行完畢後**不**停止工作階段。 |
| `--timeout` | 浮點數 | 30.0 | 無輸出時等待多少秒才判定失敗，讓卡住或安靜的任務不會永遠阻塞。長時間安靜的任務請提高此值；`0` 表示不設上限。 |

### Shebang 使用方式
將 `--keep` 與 `--gpu` 寫入 Shebang 首行，整個單檔案工作負載即精簡為：

```python
#!/usr/bin/env -S colab run --gpu T4
import torch
print(torch.cuda.get_device_name(0))
```

賦予執行權限（`chmod +x`）後，執行 `./script.py` 便能一鍵實現「配置 GPU、執行、歸還資源」。

> 提示：在 Linux/macOS 上，`env` 的 `-S` 旗標是必需的，它允許在 Shebang 行中將多個單字作為 `colab run` 的參數；若無此旗標，系統核心會將後半部所有內容合併為單一參數傳遞。

## 執行行為

1. **配置（Allocate）**：建立全新的工作階段（全程鏡像 `colab new` 的行為：`assign` → 持久化儲存 `SessionState`）。工作階段名稱預設為 `run-<6位16進位>`。
2. **執行（Execute）**：讀取腳本檔案。在首部注入確定性的前導程式碼（Prelude），重新設定 `sys.argv` 與 `__name__`，使腳本主體看見與執行 `python script.py arg1 arg2` 完全一致的執行脈絡：
   ```python
   import sys
   sys.argv = ['<basename>', 'arg1', 'arg2', ...]
   __name__ = '__main__'
   ```
   隨後在同一個核心儲存格中執行該腳本主體，以確保能正確觸發 `if __name__ == "__main__":` 防護閘。
3. **錯誤偵測（Detect failure）**：若核心回傳任何 `output_type == "error"` 的輸出（如未捕獲異常、語法錯誤等），CLI 將以非零狀態碼結束。
4. **拆除與回收（Tear down）**：在 `finally` 區塊中，除非指定了 `--keep`，否則 CLI 會：
   - 傳送 `runtime.stop(shutdown_kernel=True)`（盡力而為）。
   - 呼叫 `state.client.unassign(endpoint)` 以釋放會計費的 VM 資源。
   - 自 `StateStore` 中移除該工作階段。
   - 記錄 `session_terminated` 事件，並註明 `reason="run_completed"`（或 `"run_failed"`）。

如果設定了 `--keep`，該工作階段在 `colab sessions` 與 `colab status` 中仍會保持可見，並能透過 `colab exec -s <名稱>`、`colab repl -s <名稱>` 等重複使用，直至使用者手動執行 `colab stop`（或後端因閒置而回收它）。

## 遵循之代理指引約束 (AGENTS.md)
- **條款 7（即發即忘）**：不建立任何背景執行緒或守護行程；指令執行完畢即乾淨結束。
- **條款 10（即時探測會配置實際資源）**：拆除與回收放置於 `try/finally` 中，因此即使執行期間發生異常，仍能確實釋放 VM。測試中斷言了即使在腳本出錯時，`unassign` 仍會被呼叫。

## 測試策略 (TDD)

### 單元測試 (`tests/test_run.py`)
1. **`test_run_basic_flow`** —— 正常路徑：建立工作階段、執行腳本、退出時取消配置。模擬 `client.assign`、`client.unassign`、`ColabRuntime`。斷言 `unassign` 被確實呼叫。
2. **`test_run_keep_skips_unassign`** —— 帶有 `--keep` 選項時，不應呼叫 `unassign`，且工作階段應保留在儲存庫中。
3. **`test_run_passes_argv`** —— 執行 `colab run script.py a b c` 會使核心的 `execute_code` 呼叫負載中包含 `sys.argv = ['script.py', 'a', 'b', 'c']`。
4. **`test_run_sets_dunder_main`** —— 執行負載中包含 `__name__ = '__main__'`。
5. **`test_run_propagates_error_exit_code`** —— 當 `runtime.execute_code` 回傳的輸出為 `output_type == "error"` 時，CLI 會以非零代碼結束，且**仍會**呼叫 `unassign`。
6. **`test_run_with_gpu_flag`** —— 執行 `colab run --gpu T4 script.py` 會呼叫 `client.assign(..., variant=GPU, accelerator=T4)`。
7. **`test_run_missing_script_errors`** —— 未指定腳本路徑時拋出錯誤（Typer 層級）。
8. **`test_run_nonexistent_script_errors_before_assign`** —— 執行不存在的腳本路徑 `colab run does-not-exist.py` 必須在呼叫 `client.assign` **之前**以非零狀態碼結束，防止使用者因拼寫錯誤而平白租用虛擬機器。
9. **`test_run_unassign_called_on_exception_during_execute`** —— 若 `runtime.execute_code` 拋出異常，仍會確實呼叫 `unassign`（由 try/finally 保證）。

### 整合測試 (`integration/repro_run_command/test.sh`)
- 編寫一個會印出其 `argv` 並以 0 結束的極小腳本。
- 執行 `colab run /tmp/script.py hello world`。
- 斷言 stdout 中包含 `argv=['script.py', 'hello', 'world']`。
- 斷言隨後執行 `colab sessions` 會回傳 "No active sessions"（確認已確實清理收尾）。
- 搭配 `--keep` 重複上述測試：斷言工作階段會顯示在 `colab sessions` 中，隨後呼叫 `colab stop` 進行清理。
