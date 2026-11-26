# Colab CLI：示範與操作指引

*擷取於 2026-05-07，對照真實 Colab 後端，並使用 `showboat` 0.6.1 進行錄製。*
<!-- showboat-id: a24e677e-5052-4bec-8f82-36eb7a7859f9 -->

以下提供 11 個演練常見工作流程的實用場景，以及最後一個「橋接回瀏覽器」的範例。下方的每個 `colab` 調用皆為真實執行；每個 `output` 區塊中的文字皆是逐字擷取自 stdout/stderr。

**錄製方法說明**
- **身分驗證**：統一採用 `--auth=adc`。設定指令為：`gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory`。
- **加速器**：本示範中的所有工作階段皆使用 **CPU**。配置真實的加速器受到個別帳戶配額（Quota）的限制，且對多數讀者而言可能無法直接執行；然而工作流程本身與加速器無關，因此在示範脈絡中若提及 GPU 或 TPU，段落中會特別註明「此處以 CPU 代替」。
- **互動式子指令** —— 包含 `colab auth`、`colab drivemount`、互動式 `colab ssh`，以及未經管線傳輸的 `colab repl` —— **不在**此處執行，因為它們需要使用者在本地 TTY 終端機前進行互動。通常會使用到這些指令的示範會包含一條內聯說明以解釋其作用，並隨後以非互動式的方式繼續演練其餘工作流程。
- 在錄製期間，`~/.config/colab-cli/settings.json` 中的 `enable_update_check` 已被暫時設定為 `false`，以防每日升級提示橫幅干擾輸出內容。
- 環境變數中設定了 `PYTHONWARNINGS=ignore`，以抑制 `google.auth` 在每次使用終端使用者憑證呼叫時所發射的 ADC 配額專案警告。

**重新驗證須知**：本文件**不支援**透過 `showboat verify` 進行自動化重新驗證。因為每次執行 `colab new` 都會產生一個全新、由伺服器分配的工作階段端點（`m-s-...`），故錄製的輸出內容不可能與重新執行的結果完全一致。請將此文件視為工作流程在錄製當下成功執行的真實見證。

---

## 示範 1：雲端原生科學家

配置工作階段、在小型資料集上執行 JAX 工作負載，最後釋放工作階段。本範例展示了最核心、最典型的使用模式：`colab new` → `colab exec` → `colab stop`。（在真實環境中，此場景通常還會呼叫 `colab auth` 與 `colab drivemount` 以便 JAX 程式碼讀取 BigQuery 並將成果寫入雲端硬碟 Drive——這兩者皆需要互動，請參閱下方的跳過說明——且通常會請求 TPU 而非 CPU。）

```bash
uv run colab --auth=adc new -s research
```

```output
[colab] Creating session 'research'...
[colab] Session READY.
```

*已跳過步驟：* `colab auth -s research` 與 `colab drivemount -s research`。這兩者皆需要互動式的 TTY 授權同意流程——`auth` 會提示使用者造訪 OAuth 網址並貼回驗證碼；`drivemount` 則會在使用者於瀏覽器中授權同意後提示按下 Enter 鍵。這已在 `integration/` 中單獨進行驗證。

```bash
uv run colab --auth=adc install -s research jax 2>&1 | tail -20
```

```output
[colab] Installing packages on research (preferring uv)...
Installation Complete (via uv)!
```

```bash
cat <<'EOF' | uv run colab --auth=adc exec -s research
import jax, jax.numpy as jnp
import numpy as np

# (BigQuery 已替換為合成數據 —— 通常會使用：
#   df = bigquery.Client().query('SELECT * FROM bigquery-public-data.ml_datasets.iris LIMIT 100').to_dataframe())
data = np.random.RandomState(0).randn(100, 4)

print('Devices:', jax.devices())
w = jax.random.normal(jax.random.PRNGKey(0), (4, 4))
out = jax.jit(lambda x, w: x @ w)(jnp.array(data), w)
print(f'Processed {len(out)} rows.')
EOF

```

```output
Devices: [CpuDevice(id=0)]
Processed 100 rows.
```

```bash
uv run colab --auth=adc stop -s research
```

```output
[colab] Stopping session 'research'...
[colab] Session terminated.
```

---

## 示範 2：在 GPU 上快速疊代

一個典型的模型訓練週期：配置工作階段 → 安装依賴套件 → 執行訓練腳本 → 檢查狀態 → 下載產生的 Checkpoint 權重。此處的腳本是針對合成資料進行的 1 層線性回歸，因此在 CPU 上數秒內即可完成；在實際生產環境中，請替換為您的真實訓練程式碼並加上 `--gpu A100`。

```bash
uv run colab --auth=adc new -s trainer
```

```output
[colab] Creating session 'trainer'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc install -s trainer torch 2>&1 | tail -5
```

```output
[colab] Installing packages on trainer (preferring uv)...
Installation Complete (via uv)!
```

```bash
uv run colab --auth=adc exec -s trainer -f /tmp/train.py
```

```output
Epoch 1/10: loss 14.380
Epoch 2/10: loss 11.639
Epoch 3/10: loss 9.440
Epoch 4/10: loss 7.671
Epoch 5/10: loss 6.247
Epoch 6/10: loss 5.097
Epoch 7/10: loss 4.167
Epoch 8/10: loss 3.414
Epoch 9/10: loss 2.802
Epoch 10/10: loss 2.305
Training complete.
```

```bash
uv run colab --auth=adc download -s trainer /content/model.bin /tmp/model.bin && ls -la /tmp/model.bin
```

```output
[colab] Downloaded '/content/model.bin' to '/tmp/model.bin'
-rw-r----- 1 rtp primarygroup 1877 May  7 23:11 /tmp/model.bin
```

```bash
uv run colab --auth=adc status -s trainer
```

```output
[trainer] m-s-kkb-usw1c0-21g32dh850cd4 | Hardware: CPU | Variant: DEFAULT | Status: IDLE
  Last Execution: /tmp/train.py at 2026-05-07 23:11:32
```

```bash
uv run colab --auth=adc stop -s trainer
```

```output
[colab] Stopping session 'trainer'...
[colab] Session terminated.
```

---

## 示範 3：互動式偵錯（管線傳輸）

`colab exec` 與 `colab repl` 皆接受管線 `stdin` 並在 EOF 時結束退出，因此它們能與 Shell 管線及其他 CLI 工具完美整合。此示範列出 `/content` 內容、建立並刪除臨時檔案，最後透過單次 REPL 查詢剩餘空間。

```bash
uv run colab --auth=adc new -s debug
```

```output
[colab] Creating session 'debug'...
[colab] Session READY.
```

*注意：* 若要在虛擬機器上使用互動式 shell，請用 `colab ssh -s debug`（屬互動式，因此不在此處執行）；單次 shell 指令可用 `colab ssh -s debug -- df -h /content` 執行，或在 ssh 無法使用時，以 IPython 的 `!` 前綴管線傳給 `colab exec`，例如 `echo '!df -h /content' | colab exec -s debug`（兩者都不在本段錄影中）。

```bash
uv run colab --auth=adc ls -s debug /content
```

```output
.config/
sample_data/
```

```bash
echo 'with open("/content/scratch.log", "w") as f: f.write("x" * 1024 * 100)
print("created scratch.log (100 KB)")' | uv run colab --auth=adc exec -s debug
```

```output
created scratch.log (100 KB)
```

```bash
uv run colab --auth=adc rm -s debug /content/scratch.log
```

```output
[colab] Deleted /content/scratch.log
```

```bash
echo 'import shutil; print(shutil.disk_usage("/").free // 2**30, "GB free")' | uv run colab --auth=adc repl -s debug
```

```output
86 GB free
```

```bash
uv run colab --auth=adc stop -s debug
```

```output
[colab] Stopping session 'debug'...
[colab] Session terminated.
```

---

## 示範 4：多模態輸出（圖表與筆記本）

本範例展示了圖表重新導向（`--output-image`）以及 Jupyter 筆記本執行（`colab exec -f file.ipynb` 會將執行結果寫回至 `<主檔名>_output.ipynb` 檔案中）。

```bash
uv run colab --auth=adc new -s reporter
```

```output
[colab] Creating session 'reporter'...
[colab] Session READY.
```

```bash
cat <<'EOF' | uv run colab --auth=adc exec -s reporter --output-image /tmp/sine.png
import matplotlib.pyplot as plt, numpy as np
x = np.linspace(0, 10, 100)
plt.plot(x, np.sin(x)); plt.title('Sine'); plt.show()
EOF

```

```output
<Figure size 640x480 with 1 Axes>

[Image saved to: /tmp/sine.png]
```

```bash {image}
![在 Colab VM 上生成並儲存至 /tmp/sine.png 的正弦波圖表](/tmp/sine.png)
```

![在 Colab VM 上生成並儲存至 /tmp/sine.png 的正弦波圖表](3042ab12-2026-05-07.png)

```bash
uv run colab --auth=adc exec -s reporter -f /tmp/analysis.ipynb && ls /tmp/analysis_output.ipynb
```

```output
[colab] Parsing notebook '/tmp/analysis.ipynb'...
[colab] Executing cell 1/2 - a8850b8f...
mean = 18
stdev = 13.49
[colab] Executing cell 2/2 - c31a0002...
rows: 6
sum: 108
[colab] Saving notebook with outputs to '/tmp/analysis_output.ipynb'...
/tmp/analysis_output.ipynb
```

```bash
uv run colab --auth=adc log -s reporter -o /tmp/reporter.md && wc -l /tmp/reporter.md
```

```output
[colab] Exported history to '/tmp/reporter.md'.
55 /tmp/reporter.md
```

```bash
uv run colab --auth=adc stop -s reporter
```

```output
[colab] Stopping session 'reporter'...
[colab] Session terminated.
```

---

## 示範 5：透過 GCS 處理大量數據

從 Google Cloud Storage 儲存桶中整批拉取物件、在 VM 上進行轉換，並將處理結果拉回本地。最原汁原味的工作流程為：`colab new --gpu L4` → `colab auth`（啟用 VM 端的 `gcloud` 驗證） → `gcloud storage cp gs://bucket/raw/*.jpg /content/images/`（以加上 `!` 前綴的 shell 指令管線傳給 `colab exec` 執行） → 安裝 Pillow/Torchvision → 批次處理 → 下載成果。在此處我們跳過了身分驗證步驟（因其具互動性，需要使用者點擊同意），並以合成圖片生成來代替從 GCS 下載，但依然完整保留了「輸入 → 安裝 → 批次處理 → 下載」的流程架構。

```bash
uv run colab --auth=adc new -s data-proc
```

```output
[colab] Creating session 'data-proc'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc install -s data-proc pillow 2>&1 | tail -3
```

```output
[colab] Installing packages on data-proc (preferring uv)...
Installation Complete (via uv)!
```

```bash
cat <<'EOF' | uv run colab --auth=adc exec -s data-proc
# (通常會透過 'gcloud storage cp gs://my-bucket/raw_data/*.jpg' 從 GCS 拉取數據)
import os, zipfile
from PIL import Image, ImageFilter
os.makedirs('/content/images', exist_ok=True)
os.makedirs('/content/processed', exist_ok=True)
# 產生 10 張合成輸入圖片
for i in range(10):
    Image.new('RGB', (64, 64), (i * 25, 100, 200 - i * 15)).save(f'/content/images/img_{i:02d}.jpg')
# 處理：對每張圖片進行高斯模糊
for src in sorted(os.listdir('/content/images')):
    img = Image.open(f'/content/images/{src}').filter(ImageFilter.GaussianBlur(2))
    img.save(f'/content/processed/{src}')
# 壓縮處理結果
with zipfile.ZipFile('/content/processed/batch.zip', 'w') as z:
    for f in sorted(os.listdir('/content/processed')):
        if f.endswith('.jpg'):
            z.write(f'/content/processed/{f}', f)
print(f'Processed {len(os.listdir("/content/processed")) - 1} images, archived to batch.zip')
EOF

```

```output
Processed 10 images, archived to batch.zip
```

```bash
uv run colab --auth=adc download -s data-proc /content/processed/batch.zip /tmp/batch.zip && ls -la /tmp/batch.zip
```

```output
[colab] Downloaded '/content/processed/batch.zip' to '/tmp/batch.zip'
-rw-r----- 1 rtp primarygroup 7902 May  7 23:19 /tmp/batch.zip
```

```bash
uv run colab --auth=adc stop -s data-proc
```

```output
[colab] Stopping session 'data-proc'...
[colab] Session terminated.
```

---

## 示範 6：資源檢查與訂閱

檢查一個長時間運作的工作階段，隨後將其歷史紀錄匯出為 Jupyter 筆記本以供存檔。（`colab pay` 能在系統瀏覽器中開啟 `https://colab.research.google.com/signup` 以便使用者管理運算單位，通常也屬於此流程的一環——但在錄製環境中我們並未呼叫它，以防跳出瀏覽器視窗。）

```bash
uv run colab --auth=adc new -s long-running
```

```output
[colab] Creating session 'long-running'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc status -s long-running
```

```output
[long-running] m-s-kkb-use4a2-2qvalahyh7yzg | Hardware: CPU | Variant: DEFAULT | Status: IDLE
```

```bash
echo 'print("hello from session")' | uv run colab --auth=adc exec -s long-running
```

```output
hello from session
```

```bash
uv run colab --auth=adc log -s long-running -o /tmp/checkpoint.ipynb && ls -la /tmp/checkpoint.ipynb
```

```output
[colab] Exported history to '/tmp/checkpoint.ipynb'.
-rw-r----- 1 rtp primarygroup 974 May  7 23:20 /tmp/checkpoint.ipynb
```

```bash
uv run colab --auth=adc stop -s long-running
```

```output
[colab] Stopping session 'long-running'...
[colab] Session terminated.
```

---

## 示範 7：可重現的研究

透過管線 REPL 進行快速探索、透過管線 exec 進行檔案內容檢查，最後透過 `colab log -o <名稱>.ipynb` 將整個工作階段擷取為筆記本成品。該筆記本可直接在 Colab 網頁 UI 中重新執行。

```bash
uv run colab --auth=adc new -s pivot
```

```output
[colab] Creating session 'pivot'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc install -s pivot scipy 2>&1 | tail -3
```

```output
[colab] Installing packages on pivot (preferring uv)...
Installation Complete (via uv)!
```

```bash
echo 'from scipy.stats import zscore; print(zscore([1.2, 1.5, 1.1, 10.4, 1.3]))' | uv run colab --auth=adc repl -s pivot
```

```output
[-0.52020639 -0.43806854 -0.54758568  1.99868773 -0.49282711]
```

```bash
uv run colab --auth=adc upload -s pivot /tmp/raw_data.csv /content/raw_data.csv
```

```output
[colab] Uploaded '/tmp/raw_data.csv' to '/content/raw_data.csv'
```

```bash
echo 'print(open("/content/raw_data.csv").read())' | uv run colab --auth=adc exec -s pivot
```

```output
id,name,score
1,alice,0.92
2,bob,0.74
3,carol,0.88
4,dave,0.61
5,eve,0.95

```

```bash
uv run colab --auth=adc log -s pivot -o /tmp/pivot_discovery.ipynb && ls -la /tmp/pivot_discovery.ipynb
```

```output
[colab] Exported history to '/tmp/pivot_discovery.ipynb'.
-rw-r----- 1 rtp primarygroup 2854 May  7 23:21 /tmp/pivot_discovery.ipynb
```

```bash
uv run colab --auth=adc stop -s pivot
```

```output
[colab] Stopping session 'pivot'...
[colab] Session terminated.
```

---

## 示範 8：本地與雲端混合架構

針對遠端 VM 執行一個本地的腳本，並將產生的結果拉回本地。此範例的完整實務版本通常也會呼叫 `colab drivemount` 以在虛擬機器上的 `/content/drive` 提供 Google 雲端硬碟（以便腳本讀取共享資料）；由於 `drivemount` 需要互動，此處將其跳過。這裡保留並重點展示了——「在您的筆記型電腦上修改腳本，並直接透過 `colab exec -f local_script.py` 對 Colab 中的核心執行該腳本」這一極具價值的混合工作流程。

```bash
uv run colab --auth=adc new -s hybrid
```

```output
[colab] Creating session 'hybrid'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc exec -s hybrid -f /tmp/local_analysis.py
```

```output
Running on: Linux-6.6.113+-x86_64-with-glibc2.35
Hostname: 699413ff1767
Python: 3.12.13
This script lives on my laptop but ran on the Colab VM.
```

```bash
uv run colab --auth=adc stop -s hybrid
```

```output
[colab] Stopping session 'hybrid'...
[colab] Session terminated.
```

---

## 示範 9：多工作階段編排

同時執行多個工作階段、列出其狀態、檢查其中一個，最後停止其中一個。此處建立的兩個工作階段皆為 CPU；在實務上，您更有可能是混用多種加速器類型（例如一個 TPU 用於訓練，另一個 GPU 用於評估）。

```bash
uv run colab --auth=adc new -s tpu-cluster && uv run colab --auth=adc new -s gpu-eval
```

```output
[colab] Creating session 'tpu-cluster'...
[colab] Session READY.
[colab] Creating session 'gpu-eval'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc sessions
```

```output
[gpu-eval] m-s-kkb-usc1c0-3cickkby8ivx5 | Hardware: CPU | Variant: DEFAULT
[tpu-cluster] m-s-kkb-use1b1-3b5xes33630p3 | Hardware: CPU | Variant: DEFAULT
```

```bash
uv run colab --auth=adc status -s gpu-eval
```

```output
[gpu-eval] m-s-kkb-usc1c0-3cickkby8ivx5 | Hardware: CPU | Variant: DEFAULT | Status: IDLE
```

```bash
uv run colab --auth=adc stop -s gpu-eval && uv run colab --auth=adc stop -s tpu-cluster
```

```output
[colab] Stopping session 'gpu-eval'...
[colab] Session terminated.
[colab] Stopping session 'tpu-cluster'...
[colab] Session terminated.
```

---

## 示範 10：一鍵式自動化管線

使用 `&&` 將多個指令串聯，使任何一步失敗時即刻中止整個流程。此處的腳本是一個極小的代位物件（將 JSON 結果寫入 `/content`），因此整條鏈在 CPU 上數秒內即可執行完畢；典型的實務版本會請求 `--gpu A100` 並安裝如 `flash-attn` 等繁重的依賴項目。

```bash
uv run colab --auth=adc new -s pipeline \
  && uv run colab --auth=adc install -s pipeline requests 2>&1 | tail -2 \
  && uv run colab --auth=adc exec -s pipeline -f /tmp/local_pipeline.py \
  && uv run colab --auth=adc download -s pipeline /content/results.json /tmp/results.json \
  && uv run colab --auth=adc stop -s pipeline
```

```output
[colab] Creating session 'pipeline'...
[colab] Session READY.
[colab] Installing packages on pipeline (preferring uv)...
Installation Complete (via uv)!
Wrote results.json: {'status': 'ok', 'computed_at': '2026-05-07T23:22:34.924350Z', 'value': 42}
/tmp/ipykernel_38852/1782062088.py:5: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "computed_at": datetime.datetime.utcnow().isoformat() + "Z",
[colab] Downloaded '/content/results.json' to '/tmp/results.json'
[colab] Stopping session 'pipeline'...
[colab] Session terminated.
```

---

## 示範 11：可重現的環境

將本地的 `requirements.txt` 上傳至虛擬機器、透過 `-r` 選項進行安裝，最後驗證虛擬機器上安裝的套件版本是否與我們所請求的一致。

```bash
uv run colab --auth=adc new -s env-test
```

```output
[colab] Creating session 'env-test'...
[colab] Session READY.
```

```bash
uv run colab --auth=adc upload -s env-test /tmp/requirements.txt /content/requirements.txt
```

```output
[colab] Uploaded '/tmp/requirements.txt' to '/content/requirements.txt'
```

```bash
uv run colab --auth=adc install -s env-test -r /tmp/requirements.txt 2>&1 | tail -3
```

```output
[colab] Installing packages on env-test (preferring uv)...
Installation Complete (via uv)!
```

```bash
echo 'import requests; print("requests:", requests.__version__)' | uv run colab --auth=adc exec -s env-test
```

```output
requests: 2.31.0
```

---

## 橋接回瀏覽器

`colab url -s <工作階段名稱>` 會印出一個網址，當您在瀏覽器中將其開啟時，Colab 的網頁前端將會自動連接至您現有的 `colab-cli` 工作階段，而不會配置全新的虛擬機器。預設情況下，它僅會印出網址（可透過管線傳輸，例如 `colab url -s s1 | xclip`）；加上 `--open` 選項則會直接在您的系統預設瀏覽器中將其開啟。

```bash
uv run colab --auth=adc url -s env-test
```

```output
https://colab.research.google.com/notebooks/empty.ipynb?dbu=%2Ftun%2Fm%2Fm-s-kkb-usc1b1-3tpcjymikv7t3
```

```bash
uv run colab --auth=adc stop -s env-test
```

```output
[colab] Stopping session 'env-test'...
[colab] Session terminated.
```

```bash
uv run colab --auth=adc sessions
```

```output
[colab] Pruned 1 stale local session(s).
[colab] No active sessions found on server.
```
