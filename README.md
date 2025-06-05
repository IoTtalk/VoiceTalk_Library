# VoiceTalk Github README

VoiceTalk 是一套專為 [IoTtalk](https://github.com/IoTtalk/IoTtalk-py) 平台設計的語音控制外掛子系統，透過大型語言模型（LLM）、CCM子系統以及圖形化介面，讓使用者無需撰寫程式碼，即可建立可被語音控制的物聯網應用。 

本系統可自動將 Google Home 裝置屬性轉換為 IoTtalk 可辨識的設備模型與功能，並整合語音控制介面，使智慧家庭部署更簡便、更彈性。

---

## 🔧 功能特色

- 無需程式碼（No-Code）開發語音控制應用
- 整合 LLM 自動解析 Google Home 設定並轉換為 IoTtalk 設定
- 簡化場域建立流程，自動建立 IoTtalk 裝置模型與控制網路應用
- Web 介面可視化管理與語音控制

---

##    專案目錄結構

```
VoiceTalk_Library/
├── Device_LLM_Agent/                        # 處理第三方智慧家庭控制平台(Google Home) → IoTtalk 的設備資料轉換
│   └── Device_LLM_Agent.py                  # Device LLM Agent 主程式，可進行設備資料轉換與使用 ccm api 批次建立 DM
├── old_version/                             # 舊版本備份程式碼
├── test_audio/                              # 測試語音資料（共 1733 筆）
└── VoiceTalk_library/                       # VoiceTalk 的 Web 前端與主程式以及所需檔案
    ├── Client/                   
    │   ├── instance/                        # 使用者的語音控制錄音
    │   │   └── audios/                      # 單通道音檔
    │   │       └── org_file/                # 上傳時保留的原始語音檔案
    │   ├── static/                          # 靜態網頁資源
    │   │   ├── css/              
    │   │   ├── images/           
    │   │   └── js/               
    │   ├── templates/                       # Flask 用的 HTML 頁面模板
    │   │   └── base.html                    # 頁面共用框架模板（如標頭、載入腳本）
    │   │   └── index.html                   # 語音控制主頁，提供語音輸入與控制功能
    │   │   └── VoiceTalk Management.html    # 語音控制設備管理頁，顯示裝置與控制設定
    │   ├── whisper_model_download/          # Whisper 語音模型檔案
    │   ├── csmapi.py                        # IoTtalk DA 模組 （含 csmapi、DAN、DAI）
    │   ├── DAN.py                           
    │   ├── DAI.py                           
    │   ├── SA.py                            # IoTtalk SA 模組 (VoiceTalk 自動產生 SA 所需的模板)
    │   ├── Dialogflow_API.py                # 語音辨識 API (串接 Google Dialogflow 的 API)
    │   ├── STT_API.py                       # 語音辨識 API (串接 Google Speech-to-Text 的 API)
    │   ├── GPT_API.py                       # LLM API (呼叫 OpenAI GPT 模型的 API，用來執行 SC/CG prompt)
    │   ├── Llama_API.py                     # LLM API (呼叫自架 LLaMA 模型的 API，用來執行 SC/CG prompt)
    │   ├── ccm_utils.py                     # 需用到的 IoTtalk CCM API
    │   ├── config.py                        # server 參數、API 路徑、檔案路徑
    │   ├── server.py                        # 主伺服器程式，處理設備管理、語音輸入與控制流程
    │   └── requirements.txt                 # 安裝所需套件列表
    └── DB/                                  # 儲存金鑰、設備模型對應關係(DM 對應 Trait、Trait 對應 DF)以及場域中的設備資訊
        ├── cmnHantTW/                       # 中文繁體語料與設定
        └── enUS/                            # 英文語料與設定
```

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
3. 在 IoTtalk 中建立 VoiceCtl 裝置，IDF/ODF 可任意選擇，IoTtalk 將自動辨識 DM 名稱為 VoiceCtl 的特殊用途。
4. 使用者於 IoTtalk 專案中的 Model list 點擊「VoiceCtl」。
5. VoiceTalk 透過 CCM 子系統自動完成 IoTtalk 專案。
6. 系統自動產生對應的遙控設備。
7. 自動建立語音控制頁面，並回傳頁面 URL 以 QR Code 呈現於 IoTtalk。
8. 使用者即可透過語音開始控制裝置，指令將由 Voice LLM Agent 處理並傳送至 IoTtalk。

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
    Llama_API_key = 'API_key'
    ```
    目前使用實驗室的共用 Llama API，需要 API key，請參考 [use_ollama](https://github.com/IoTtalk/AgriGraphRAG/blob/master/create_graph/use_ollama.py)
    (目前不使用這個) Llama server 的使用說明可以參考：[🦙LLaMA Server 部署與使用說明](https://hackmd.io/@kiriku0825/rkl6Ph5Zll)
- 使用 ChatGPT：
    ```python
    GPT_API_Key = "sk-proj-..."
    ```
    API 申請方式可以參考：[金鑰申請方法](https://hackmd.io/@claireshen/Hyo-vn9bel)
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