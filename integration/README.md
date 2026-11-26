# 整合測試

與 `tests/` 目錄下的模擬（Mock）單元測試不同，此目錄包含針對**真實 Colab 後端**執行的端到端（End-to-End）測試。

## 前置條件
- 具有 Colab 存取權限的 Google 帳戶。
- 已安裝 `uv`。
- 具備有效的作用中身分驗證憑證——可透過 `colab sessions` 進行驗證。

## 測試場景

| 目錄 | 涵蓋範疇 |
| --- | --- |
| `repro_plot_redirection/` | 測試 `colab exec` 執行 matplotlib 腳本，並使用 `--output-image` 進行圖表重新導向。 |
| `repro_run_command/` | `colab run <script.py>` 在全新虛擬機器上執行本地腳本並清理；`--keep` 則讓工作階段保持存活。 |
| `repro_variable_persistence/` | 驗證在同一個工作階段中，變數可在多次 `colab exec` 呼叫之間持續留存。 |
| `repro_bundled_oauth/` | 快速冒煙測試（約 5 秒）：驗證當遺失本地設定時，系統會自動載入搭售的遞補 OAuth 設定，並以預設的用戶端 ID 啟動 OAuth 流程。 |
| `repro_legacy_token_migration/` | 快速冒煙測試（約 5 秒，不需虛擬機器）：將金鑰圈（keyring）出現之前留下的 `~/.config/colab-cli/token.json` 遷移進入金鑰圈並刪除；若金鑰圈已有權杖則直接刪除；若金鑰圈無法存取則保留檔案（並在 stderr 顯示警告）。使用臨時 HOME 與檔案型測試金鑰圈。 |
| `repro_ssh/` | 快速冒煙測試（約 5 秒）：`--help` 有列出相關旗標，且未知的工作階段會直接結束。慢速浸泡測試（約 95 秒）：真實端到端測試會配置一台 CPU 虛擬機器，透過 `colab ssh --proxy-mode` 執行真正的遠端指令。 |
| `repro_windows_ssh/` | Windows 原生真實 CPU 測試：Windows OpenSSH 啟動產生的 ProxyCommand、執行遠端標記指令，並釋放所記錄的執行期。需要 OS 金鑰圈中快取的 OAuth2 憑證；缺少前置條件時以 77 結束。 |

## 如何執行
```bash
uv run bash integration/repro_run_command/test.sh
```
`uv run` 可確保本地專案的 `colab` 進入點被置於 `PATH` 中。

若要執行 Windows 原生 SSH 檢查，請在 repo 目錄下用 PowerShell 執行：

```powershell
uv run python integration/repro_windows_ssh/test.py
```

請先以 `uv run colab --auth=oauth2 sessions` 完成驗證。Windows 測試不使用 Bash 或 WSL，也會保留其他無關的作用中工作階段。

## 如何新增測試場景
1. 建立 `repro_<簡短描述>/` 目錄。
2. 新增展示或驗證特定問題的腳本檔案（`.sh` 或 `.py`）。
3. 在上方表格中新增一行，並註明該測試是快速（冒煙測試）還是慢速（浸泡測試）。
