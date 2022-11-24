# Voicetalk Library

This repository is designed as a library of the DeviceTalk.  
In order to utilize this library, please follow [VoiceTalk User Guide](https://hackmd.io/z-TuqWodS7-G6TmZUWZbvg) to setup VoiceTalk service.  
* For developers to matain and upgrade VoiceTalk, follow [VoiceTalk Developer Guide](https://hackmd.io/ioh87B5cTVqsXU_WukYtgA).
* For furthor description about DeviceTalk, please visit [DeviceTalk Documentation](https://hackmd.io/@Eric-Pwg/SJWlETzj5/https%3A%2F%2Fhackmd.io%2F%40Eric-Pwg%2FB1W18mViq).
* This Library follows the rule of [DeviceTalk: Library file Architecture](https://hackmd.io/@Eric-Pwg/SJWlETzj5/https%3A%2F%2Fhackmd.io%2F%40Eric-Pwg%2FB15oVAaO9).

## Requirement

### For Deployment

The followings are required if the user need full access to microphone on web.

1. Domain name (please contact the organization administrator.)
2. SSL Authentication (check out [certbot official](https://certbot.eff.org/))



### For Quick Testing Purpose
For testing, navigate to `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in any chromium based browser(Chrome, Edge, etc.).
Find and enable the `Insecure origins treated as secure section`. Add the addresses (VoiceTalk address) you want to ignore the secure origin policy for. Remember to include the port number. 
Save and restart the browser.

**Remember this quick testing is for dev purposes only.**


## 1. Setup CkipTagger(zh-TW)

```
cd Voicetalk_library/Client
pip install -U ckiptagger[tf,gdown]
```
CkipTagger is a Traditional Chinese NLP Python library hosted on PyPI.

Requirements:
* python>=3.6
* tensorflow>=1.13.1 / tensorflow-gpu>=1.13.1 (one of them)
* gdown (optional, for downloading model files from google drive)

(Minimum installation) If you have set up tensorflow, and would like to download model files by yourself.
`pip install -U ckiptagger`

(Complete installation) If you have just set up a clean virtual environment, and want everything, including GPU support.

`pip install -U ckiptagger[tfgpu,gdown]`

for more information, visit [ckiptagger official github](https://github.com/ckiplab/ckiptagger)

## 2. Setup spaCy (en-US)

1. Install spaCy
```
cd Voicetalk_library/Client
pip install -U spacy
```

2. Download english model

```
python -m spacy download en_core_web_sm
```

for more information, visit [enspaCy official site](https://spacy.io/usage)



### VoiceTalk Support Browser:
* Chrome
* Edge
* Safari
(Firefox is not support in VoiceTalk due to the limitation of Web Speech API)