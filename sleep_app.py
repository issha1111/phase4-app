import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
# 最新のAPIキーを適用
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 新しいサービスアカウントのJSON（gcp_json）を取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 【Invalid \escape 対策】
    # 画像 image_668471.png にある \n を正しく解釈させる魔法
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # スプレッドシート「Phase4_Log」の「SleepLog」タブを開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (リストで確認した正確な名前を指定)
# ==========================================
def analyze_images(images):
    # 画像 IMG_5072.jpg にあった正確なIDを指定
    model_id = 'models/gemini-3-flash-preview'
    model = genai.GenerativeModel(model_id)
    
    # 2026年問題対策：AIに現在の西暦を叩き込む
    prompt = """
    Extract sleep data from the screenshot and return ONLY a JSON object.
    IMPORTANT: The current date is January 22, 2026. Use "2026" for the year.
    JSON keys: date(2026-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    
    # JSON部分だけを確実に抜き出す
    res_text = response.text
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# --- UIレイアウト ---
st.title("🌙 Sleep Analyzer 2026 (G3 Preview)")

files = st.file_uploader("睡眠スクショをアップロード", accept_multiple_files=True)

if files:
    images = [Image.open(f) for f in files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ Gemini 3 で解析を実行"):
        with st.spinner("2026年のログとして最新AIで解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['data'] = result
                st.success("解析成功！")
                st.json(result) # date が 2026 になっているはずです！
            except Exception as e:
                st.error(f"解析失敗（モデル名の確認が必要かも）: {e}")

if 'data' in st.session_state and st.button("📝 スプレッドシートに保存"):
    try:
        sheet = get_worksheet()
        d = st.session_state['data']
        row = [d.get(k) for k in ['date', 'sleep_score', 'total_sleep', 'fall_asleep', 'wake_up', 'rem', 'light', 'deep', 'avg_hr', 'min_hr', 'max_hr', 'resting_hr']]
        sheet.append_row(row)
        st.balloons()
        st.success("2026年のログをスプレッドシートに保存しました！")
        del st.session_state['data']
    except Exception as e:
        st.error(f"保存エラー（Secretsの書き方を確認してください）: {e}")