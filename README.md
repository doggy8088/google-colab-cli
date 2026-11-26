# Colab CLI

Google Colab 的命令列介面（Command-Line Interface）。讓您直接在終端機中配置高效能 CPU、GPU 及 TPU 執行期（Runtimes）、執行本地程式碼、管理遠端檔案，並編排自動化的雲端管線。

旨在提供無縫的開發人員生產力、無介面（Headless）自動化，以及 AI 代理（AI Agent）整合。

[示範影片](https://github.com/user-attachments/assets/656226a9-af13-4fdb-8eda-d7de747336a2)

> [!NOTE]
> **支援平台**：Colab CLI 目前僅支援 **Linux 與 macOS**。現階段不支援 Windows。

> [!TIP]
> 正在尋找筆記本內聯、互動式且有代理輔助的編碼體驗，而非終端機工作流程嗎？請參閱 [Colab MCP 伺服器](https://github.com/googlecolab/colab-mcp)。

---

## 關鍵特性

* **即時配置虛擬機器**：數秒內即可啟動 CPU、GPU（T4, L4, G4, H100, A100）或 TPU（v5e1, v6e1）執行期。
* **強大的程式碼執行能力**：可執行本地 Python 腳本、Jupyter 筆記本（`.ipynb`）或管線傳送的 `stdin` 程式碼；亦可啟動互動式 REPL 或 SSH shell（`colab ssh`）。
* **臨時性任務執行器（`colab run`）**：單一指令即可配置乾淨的 VM、執行帶有轉發參數的本地腳本、擷取輸出檔案，並自動拆除（Tear down）執行期。
* **以活動為準的存活機制**：只要核心仍在活動，工作階段就會保持存活，Colab 後端會自動維持其存活狀態。
* **無縫的工作空間自動化**：掛載 Google 雲端硬碟（Google Drive）、驗證 Google Cloud Platform (GCP) 憑證，並透過高效能的 `uv` 套件管理工具安裝依賴項目。
* **狀態與日誌存檔**：檢查本地工作階段狀態，或將互動式歷史紀錄日誌匯出為標準的 Jupyter 筆記本、Markdown 或結構化 JSONL 檔案。

---

## 安裝方式

建議使用 `uv`（推薦）或標準的 `pip` 安裝此套件：

```bash
# 使用 uv（推薦）
uv tool install google-colab-cli

# 使用 pip
pip install google-colab-cli
```

---

## 快速入門

啟動 CPU 虛擬機器執行期、執行程式碼，並清理資源：

```bash
# 1. 配置新的工作階段
colab new

# 2. 從 stdin 執行程式碼
echo 'print("Hello from Google Colab!")' | colab exec

# 3. 停止並釋放虛擬機器資源
colab stop
```

> [!NOTE]
> 當只有一個工作階段處於作用中時，您可以省略 `-s, --session` 選項，CLI 會自動識別該工作階段。

---

## 指令索引

執行 `colab <指令> --help` 即可檢視特定指令的選項、預設值與詳細說明。

### 工作階段管理
| 指令 | 說明 |
| --- | --- |
| `colab new [-s 名稱] [--gpu GPU] [--tpu TPU] [--high-mem]` | 配置一個新的 CPU、GPU 或 TPU 虛擬機器執行期（可選高 RAM） |
| `colab sessions` | 列出目前在後端作用中的所有工作階段 |
| `colab status [-s 名稱]` | 顯示作用中工作階段的硬體資訊、機器規格、狀態與本地中繼資料 |
| `colab restart-kernel [-s 名稱]` | 重設作用中工作階段的 Jupyter 核心 |
| `colab stop [-s 名稱]` | 結束虛擬機器工作階段並釋放其資源 |
| `colab url [-s 名稱] [--open]` | 印出或直接在瀏覽器開啟連接至作用中工作階段的網址 |

### 執行
| 指令 | 說明 |
| --- | --- |
| `colab run [--gpu GPU] [--tpu TPU] [--high-mem] [--keep] 腳本 [參數...]` | 在乾淨的 VM 上執行本地腳本並轉發參數，完成後將其釋放 |
| `colab exec [-s 名稱] [-f 檔案] [--output-image 路徑]` | 執行來自 stdin、本地 `.py` 檔案或 `.ipynb` 筆記本的 Python 程式碼 |
| `colab repl [-s 名稱] [--output-image 路徑]` | 在 VM 上啟動互動式 Python REPL（在管線 EOF 時會乾淨退出） |
| `colab ssh [-s 名稱] [--proxy-mode] [-i 金鑰] [--gpu GPU] [--tpu TPU] [--high-mem] [-- 指令 ...]` | 透過 WebSocket 在執行期上開啟 SSH shell、執行單次遠端指令（`-- 指令`），或作為 OpenSSH `ProxyCommand` 橋接，供 IDE 遠端開發使用 |

### 檔案操作
| 指令 | 說明 |
| --- | --- |
| `colab ls [-s 名稱] [路徑]` | 列出虛擬機器上的遠端檔案 |
| `colab upload [-s 名稱] 本地 遠端` | 將本地檔案上傳至虛擬機器檔案系統 |
| `colab download [-s 名稱] 遠端 本地` | 自虛擬機器檔案系統下載遠端檔案至本地 |
| `colab rm [-s 名稱] 路徑` | 刪除虛擬機器檔案系統上的遠端檔案 |
| `colab edit [-s 名稱] 路徑` | 使用本地 `$EDITOR` 編輯器直接就地（In-place）編輯遠端檔案 |

### 自動化與工具
| 指令 | 說明 |
| --- | --- |
| `colab auth [-s 名稱]` | 為虛擬機器驗證 GCP 服務（BigQuery, GCS 等）的存取權限 |
| `colab logout` | 清除本機 OAuth2 與快取的執行期權杖，以登出或切換帳戶 |
| `colab drivemount [-s 名稱] [路徑]` | 在虛擬機器上掛載 Google 雲端硬碟（預設為 `/content/drive`） |
| `colab install [-s 名稱] [-r 檔案 \| 套件...]` | 使用 `uv` 在虛擬機器上安裝套件（亦會退回使用 `pip`） |
| `colab log [-s 名稱] [-n 數量] [-o 檔案]` | 檢視或匯出工作階段歷史紀錄（支援 `.ipynb`, `.md`, `.txt`, `.jsonl`） |
| `colab usage` | 顯示帳戶的運算單位使用率與餘額 |
| `colab pay` | 開啟 Colab 訂閱頁面以管理您的運算單位 |
| `colab version` | 印出已安裝的 CLI 版本 |
| `colab update [--install]` | 檢查是否有新版本（並可選擇直接就地升級 CLI） |

### 全域選項
* `--auth {oauth2,adc}` —— 存取 Colab API 的身分驗證策略（預設為 `oauth2`）。若要以應用程式預設憑證（Application Default Credentials，`--auth adc`）驗證，請執行：
  ```bash
  gcloud auth application-default login \
      --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory
  ```
* `-c, --client-oauth-config 路徑` —— 公開的 OAuth 用戶端憑證設定檔路徑（預設為 `~/.colab-cli-oauth-config.json`）。
* `--config 路徑` —— 本地工作階段中繼資料的儲存路徑（預設為 `~/.config/colab-cli/sessions.json`）。
* `--logtostderr` —— 將偵錯日誌輸出直接導向至 stderr。

---

## 實用範例

### 加速器訓練與 Checkpoint 下載

配置 A100 GPU、安裝需要的套件、執行本地訓練腳本、下載產生的模型權重，最後結束該虛擬機器：

```bash
colab new -s trainer --gpu A100
colab install -s trainer torch transformers
colab exec -s trainer -f train.py
colab download -s trainer checkpoints/model.bin ./model.bin
colab stop -s trainer
```

### 結合雲端硬碟的分析筆記本執行

掛載 Google 雲端硬碟、針對 VM 核心執行本地筆記本（輸出會寫回至 `report_output.ipynb` 檔案中）、匯出執行的 Markdown 日誌，最後清理資源：

```bash
colab new -s analysis
colab drivemount -s analysis
colab exec -s analysis -f report.ipynb
colab log -s analysis -o execution_log.md
colab stop -s analysis
```

---

## 使用須知

* **機器規格**：在 `colab new`、`colab run` 或 `colab ssh`（自動建立執行期時）加上 `--high-mem`，即可要求高 RAM 的機器規格。受支援的加速器（CPU、T4、A100 等）需要 Colab Pro 或 Pro+ 資格。L4 與 TPU 執行期只有一種規格，因此會忽略此旗標。機器規格會顯示在 `colab sessions` 與 `colab status` 中。
* **TTY 需求**：`colab repl` 與互動式 `colab ssh` 需要本地 TTY。在自動化腳本或管線中執行時，請將 stdin 管線傳給 `colab repl`（例如 `echo "print(1)" | colab repl`）以觸發其非互動模式，或用 `colab ssh -s 名稱 -- 指令` 執行單次 shell 指令（例如 `colab ssh -s 名稱 -- ls /content`）；不可信的值請以獨立參數傳入（在程式接受的位置放在 `--` 之後），因為單一參數會被視為一整行遠端 shell 指令。`colab ssh` 需要本地的 `ssh` 用戶端與金鑰，因此在無法使用 ssh 的情況下（沒有用戶端或金鑰、工具不在精簡 ssh 環境的 `PATH` 上，或執行期的並行 SSH 連線已用完），請將指令以 IPython 的 `!` 前綴管線傳給 `colab exec`（例如 `echo '!ls /content' | colab exec`）；每一行 `!` 都是獨立的 shell，且 IPython 會展開其中的 `{expr}` 與 `$name`，所以多行腳本請以 `%%bash` 開頭，並讓不可信文字不要出現在 `!` 行中。
* **透明的程式碼執行**：呼叫 `colab exec -f file.py` 時，CLI 會在本地讀取檔案並將其內容傳輸至遠端核心。您無需在執行前手動上傳腳本。
* **儲存與狀態路徑**：工作階段金鑰與中繼資料儲存於 `~/.config/colab-cli/sessions.json`。全域 CLI 設定位於 `~/.config/colab-cli/settings.json`。這些路徑皆可透過全域的 `--config` 旗標進行自訂或隔離。

### 臨時性加速器任務

使用 `colab run` 可在專用硬體上執行本地腳本，而無需手動管理工作階段的生命週期。CLI 會自動處理虛擬機器的配置、腳本執行，並在完成後立即進行拆除：

```bash
# 在 T4 GPU 上執行 train.py，並在完成後釋放虛擬機器
colab run --gpu T4 train.py
```

### 支援 Shebang 執行

若要直接在遠端加速器上執行本地檔案，可將 `colab run` 直譯器置於 Shebang 行中：

```python
#!/usr/bin/env -S colab run --gpu L4 --keep
import torch

print("L4 GPU Available:", torch.cuda.is_available())
print("Device Name:", torch.cuda.get_device_name(0))
```

賦予腳本執行權限（`chmod +x script.py`）並執行它： `./script.py`。`--keep` 選項會指示 CLI 在完成時保留工作階段虛擬機器，以便您重新執行或檢查日誌。

---

## 深入探索文件

關於系統架構的完整概述以及特定 CLI 子系統的深入探討，請參閱以下詳細文件：

* [工作階段管理架構](docs/01_session_management.md)
* [互動式與非互動式執行設計](docs/02_execution_and_interactive.md)
* [檔案管理與 Jupyter Contents API](docs/03_file_management.md)
* [身分驗證提供者與虛擬機器自動化](docs/04_automation_and_utility.md)
* [臨時性任務執行器設計](docs/05_run_command.md)

若要檢視 11 個真實自動化場景的互動式指引，請參考 [示範指引 (Demo Walkthroughs)](docs/demos.md)。

---

## 參與貢獻

我們非常歡迎任何回饋與貢獻！詳情請參閱 [`CONTRIBUTING.md`](./CONTRIBUTING.md)。

---

## 法律與隱私

請參閱 Colab 的[服務條款](https://research.google.com/colaboratory/tos_v6.html)與 [Google 隱私權政策](https://policies.google.com/privacy)，兩者皆適用於本 CLI 的使用。
