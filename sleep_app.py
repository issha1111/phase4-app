import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ⚙️ 接続設定
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. あなたが新しく貼った gcp_json を取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【Invalid \escape 対策】
    # 文字列の読み込みエラーを回避するため、特殊記号をエスケープ
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # 3. 秘密鍵の中の改行コードを Google が求める形に復元
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # スプレッドシート名とタブ名を確認
    return gc.open('Phase4_Log').worksheet('SleepLog')

def analyze_images(images):
    # 429エラー回避のため、安定している gemini-1.5-flash を推奨
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 2026年固定の強力な指示
    prompt = """
    Extract sleep data from the screenshot and return ONLY a JSON object.
    IMPORTANT: The current year is 2026. Use "2026" for the date field.
    JSON keys: date(2026-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    res_text = response.text
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# --- UI部分 ---
st.title("🌙 Sleep Analyzer (Final Sync)")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ 2026年のデータとして解析"):
        with st.spinner("AI解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_data'] = result
                st.success("解析成功！")
                st.json(result)
            except Exception as e:
                st.error(f"解析失敗: {e}")

if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("スプレッドシートに書き込み中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                row = [d.get('date'), d.get('sleep_score'), d.get('total_sleep'), d.get('fall_asleep'), d.get('wake_up'), d.get('rem'), d.get('light'), d.get('deep'), d.get('avg_hr'), d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("2026年のデータとして保存完了！")
                del st.session_state['sleep_data']
            except Exception as e:
                # このエラーが出るなら、まだGitHubへのpushが反映されていません
                st.error(f"保存エラー: {e}")