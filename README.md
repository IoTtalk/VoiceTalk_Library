# VoiceTalk Library

VoiceTalk 是一套專為 [IoTtalk](https://github.com/IoTtalk/IoTtalk-py) 平台設計的語音控制外掛子系統，透過大型語言模型（LLM）、CCM子系統以及圖形化介面，讓使用者無需撰寫程式碼，即可建立可被語音控制的物聯網應用。 

本系統可自動將 Google Home 裝置屬性轉換為 IoTtalk 可辨識的設備模型與功能，並整合語音控制介面，使智慧家庭部署更簡便、更彈性。

---

## 🔧 功能特色

- 無需程式碼（No-Code）開發語音控制應用
- 整合 LLM 自動解析 Google Home 設定並轉換為 IoTtalk 設定
- 簡化場域建立流程，自動建立 IoTtalk 裝置模型與控制網路應用
- Web 介面可視化管理與語音控制

---

## 📐 系統架構概覽

VoiceTalk 架構中的主要功能：

- **Device LLM Agent**：自動將 Google Home 資料格式（Device Type、Trait、Command）轉換為 IoTtalk 的 DM / DF 架構。
- **Voice LLM Agent**：處理語音輸入，並經過 LLM 兩階段提示（Prompt）機制，將語音轉為可執行的 IoT 指令。
- **VoiceCtl Generator**：自動完成 IoTtalk 專案內容，並產生語音控制所需的 input device。
- **Info Generator**：記錄場域設備資訊，並儲存至 VoiceTalk Database。

整體流程如下：
1. Device LLM Agent 從 Google Home 結構匯入設備資訊。
2. Device LLM Agent 自動建立對應 DM/DF。
3. 使用者於 IoTtalk 專案中的 Model list 點擊「VoiceCtl」。
4. VoiceTalk 透過 CCM 子系統自動完成 IoTtalk 專案。
5. 系統自動產生對應的遙控設備。
6. 自動建立語音控制頁面，並回傳頁面 URL 以 QR Code 呈現於 IoTtalk。
7. 使用者即可透過語音開始控制裝置，指令將由 Voice LLM Agent 處理並傳送至 IoTtalk。

---

## 🧰 安裝與使用方式

### 環境需求

- linux 系統
- Python 3.9
- 建議使用虛擬環境 (venv)


### 下載程式碼

```bash=
git clone https://github.com/IoTtalk/VoiceTalk_Library.git
cd VoiceTalk_Library
```

### 建立並啟用虛擬環境

```bash=
python3.9 -m venv <venv_name>
source <venv_name>/bin/activate
```

### 更新 pip 並安裝套件

```bash=
python -m pip install --upgrade pip
cd VoiceTalk_library/Client
pip install -r requirements.txt
```

### 設定 config

路徑：`/VoiceTalk_library/Client/config.py`，需設定以下參數：

#### IoTtalk 伺服器 URL

```python
SERVER_URL = "https://XXX.iottalk.tw/"
GUI_SERVER_URL = "http://XXX.iottalk.tw:7788/"
```

#### ASR 工具的 API 金鑰（如需使用 Google Dialogflow 或 Speech-to-Text）
請將金鑰檔放於 `/VoiceTalk_library/DB/` 資料夾，並設定如下：
```python
Dia_API_key = "../DB/Dialogflow_test20250507.json"
STT_client_file = "../DB/stt-20250506.json"
```

- Dialogflow 使用以及金鑰產生方式可參考：[Google Dialogflow 教學](https://hackmd.io/@kiriku0825/rJp3vwdbgl)
- Speech-to-Text 使用以及金鑰產生方式可參考：[Google Speech-to-Text 教學](https://hackmd.io/@kiriku0825/ryd5SDuWlx)


#### LLM 模型設定（二擇一）
- 使用 Llama：
    ```python
    Llama_API_url = "<domain>:<port>/chat"
    ```
- 使用 ChatGPT：
    ```python
    GPT_API_Key = "sk-proj-..."
    ```
    並修改 `/VoiceTalk_library/Client/server.py` 中的以下兩處程式碼：
    1. 在 SentenceCorrection() 中：
        - 解除 [GPT 區塊](https://github.com/IoTtalk/VoiceTalk_Library/blob/f3007a5f014ba476542d88b1043148db46d7c72e/VoiceTalk_library/Client/server.py#L433~L434) 注解
        - 註解 [Llama 的區塊](https://github.com/IoTtalk/VoiceTalk_Library/blob/f3007a5f014ba476542d88b1043148db46d7c72e/VoiceTalk_library/Client/server.py#L437~L438)。
    2. 在 generate_command_and_response() 中：
        - 解除 [GPT 區塊](https://github.com/IoTtalk/VoiceTalk_Library/blob/f3007a5f014ba476542d88b1043148db46d7c72e/VoiceTalk_library/Client/server.py#L274~L275) 注解
        - 註解 [Llama 的區塊](https://github.com/IoTtalk/VoiceTalk_Library/blob/f3007a5f014ba476542d88b1043148db46d7c72e/VoiceTalk_library/Client/server.py#L279)。
    
#### 修改 port
```python
Port = ...
```

### 執行 VoiceTalk 主程式

```bash
python server.py
```
---

## 🖥️ Device LLM Agent 與管理介面

若要透過網頁管理裝置，或使用 Device LLM Agent 批次產生預設的 Device Model / Trait / DF，可參考以下說明：

👉 [Device LLM Agent & VoiceTalk Management 使用教學](https://hackmd.io/@claireshen/S1d9EOKbgx)

---

## 🎬 Demo 影片

以下為 VoiceTalk 的實際操作展示：
👉 [Demo 影片連結](https://youtu.be/Ib2J3VtBXIw)

---

## 🔊 語音資料來源說明

本專案共使用 **1,733 筆語音資料**，包含：

- **723 筆錄音**：由作者與朋友實際錄製，帶有中文口音與背景雜音，用以模擬真實場景。
- **1,010 筆合成語音**：透過 **OpenAI Text-to-Speech** 工具產生，用以測試語音合成在控制任務中的效能。

上述資料僅供**非營利的學術研究與模型測試**使用，並遵循 OpenAI 的 [使用政策](https://openai.com/policies/terms-of-use)。所有音檔已包含於本專案的 `test_audio/` 目錄中。