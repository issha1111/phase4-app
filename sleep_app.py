import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
# 新しいAPIキー（AIzaSyC...）をSecretsに貼ってください
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. あなたが新しく作成・貼り付けした gcp_json を取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【Invalid \escape 対策】
    # この2行が char 1094 などのエラーを物理的に消し去ります
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # 3. 秘密鍵の中の改行コードを Google 認証が認識できる形に戻す
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # スプレッドシート名「Phase4_Log」の「SleepLog」タブを開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (2026年固定)
# ==========================================
def analyze_images(images):
    # 429エラー（制限）が出た場合は 'gemini-1.5-flash' に書き換えてください
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Extract sleep data from the screenshot and return ONLY a JSON object.
    IMPORTANT: The current year is 2026. Use "2026" for the year in the date field.
    
    JSON keys: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    res_text = response.text
    # JSON部分だけを強引に抜き出す処理
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# --- UI ---
st.title("🌙 Sleep Analyzer 2026")

files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if files:
    images = [Image.open(f) for f in files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("2026年のログとして解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_result'] = result
                st.success("解析成功！")
                st.json(result) # ここで 2026 になっているかチェック！
            except Exception as e:
                st.error(f"解析失敗: {e}")

if 'sleep_result' in st.session_state and st.button("📝 スプレッドシートに保存"):
    try:
        sheet = get_worksheet()
        d = st.session_state['sleep_result']
        row = [d.get(k) for k in ['date', 'sleep_score', 'total_sleep', 'fall_asleep', 'wake_up', 'rem', 'light', 'deep', 'avg_hr', 'min_hr', 'max_hr', 'resting_hr']]
        sheet.append_row(row)
        st.balloons()
        st.success("2026年のログとして保存完了！")
        del st.session_state['sleep_result']
    except Exception as e:
        st.error(f"保存エラー（コードが反映されていない可能性があります）: {e}")