# 設計文件：檔案管理 (`ls`, `rm`, `upload`, `download`, `edit`)

## 概述
在 Colab 虛擬機器上的檔案管理將透過 Jupyter Contents API 實作。

## 實作方法

### 1. 列出檔案 (`colab ls`)
- **API**：`GET /api/contents/<path>`（如 HAR 軌跡 L68181 所示）。
- **參數**： 
    - `authuser`：0
    - `colab-runtime-proxy-token`：`<session_token>`
- **回應**：JSON 格式，其中 `content` 欄位包含目錄項目的陣列。
- **呈現**：美化輸出清單（類似於 `ls -F` 或格式化的表格）。

### 2. 上傳檔案 (`colab upload`)
- **API**：`PUT /api/contents/<remote_path>`（如 HAR 軌跡所示）。
- **承載資料（Payload）**：JSON 主體：
    ```json
    {
      "name": "filename.txt",
      "path": "path/filename.txt",
      "type": "file",
      "format": "text",
      "content": "..."
    }
    ```
- **Base64 編碼**：針對二進位檔案使用 `format: base64`。
- **進度指示**：透過分塊（Chunking）或提供狀態更新，針對大型上傳實作簡易的進度條。

### 3. 下載檔案 (`colab download`)
- **API**：`GET /api/contents/<remote_path>?content=1`（如 HAR 軌跡所示）。
- **回應**：包含 `content` 欄位的 JSON。
- **處理**：依據 `format`（`base64`、`json` 或純 `text`）對內容進行解碼並儲存於本地。
- **逾時**：每個 Contents API 請求皆使用 `(connect, read)` 逾時 `(30, 300)` 秒。讀取逾時限制的是位元組之間的等待時間，而非整個傳輸，因此大型檔案仍可完成傳輸，而中斷的連線會以錯誤失敗，不會讓 `ls`、`rm`、`upload`、`download` 或 `edit` 無限掛起。

### 4. 刪除檔案 (`colab rm`)
- **API**：`DELETE /api/contents/<remote_path>`。

### 5. 編輯檔案 (`colab edit`)
- **方法**：整合了下載遠端檔案、在本地以使用者的 `$EDITOR` 開啟，並在檔案發生變更時隨後上傳修改後的檔案。
- **狀態追蹤**：使用 SHA-256 雜湊值安全且確定性地追蹤呼叫編輯器前後的檔案變更。
- **遞補機制（Fallback）**：若 Colab 執行期上的目標檔案尚不存在，則在本地建立一個空的暫存檔案，本質上類似於 `touch` 的作用。

## 實作細節
- **基準網址（Base URL）**：在工作階段配置期間獲取的後端網址。
- **代理代杖（Proxy Token）**：每個請求皆需要附帶 `colab-runtime-proxy-token`。
- **錯誤處理**：妥善處理 404（找不到檔案）與 403（未授權）錯誤。
- **大型檔案**：Contents API 對於非常巨大的檔案可能存在限制。若是如此，我們將實作透過核心（Kernel）串流分塊的遞補機制。

## 測試策略
所有檔案管理功能皆必須遵循測試驅動開發（TDD）。

### 1. 模擬 Contents API
- **測試案例**：驗證 `colab ls` 是否能正確解析 Jupyter `contents` 的 JSON 回應（包含 `type: directory` 與 `type: file`）。
- **測試案例**：驗證 `colab upload` 是否能正確將本地二進位檔案進行 Base64 編碼以作為 `PUT` 請求的承載資料。
- **測試案例**：驗證 `colab download` 是否能正確從 `GET` 回應的 `content` 欄位解碼並儲存於本地。
- **測試案例**：驗證 `colab edit` 是否能安全地處理檔案有修改或未修改的情況。
- **測試案例**：驗證 `colab edit` 是否能透過模擬安全地開啟系統編輯器，且不會導致測試環境掛起。

### 2. 異常案例
- **測試案例**：驗證 404 回應是否能被正確捕獲，並向使用者呈現「找不到檔案」的錯誤。
- **測試案例**：驗證透過核心串流處理超出 API 限制的大型檔案上傳。