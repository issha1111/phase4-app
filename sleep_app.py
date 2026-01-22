import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer", page_icon="🌙")

# ⚙️ 接続設定
# 新しいAPIキー（AIzaSyD...）をSecretsのGOOGLE_API_KEYに貼ってください
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # Secretsの名前を "gcp_json" に修正
    raw_json = st.secrets["gcp_json"].strip()
    
    # バックスラッシュの Invalid \escape 対策
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # Google認証用の改行復元
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

def analyze_images(images):
    # 404エラー回避のため、確実に存在する安定版モデルを使用
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """睡眠スクショからデータを抽出しJSONで返して。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr"""
    
    response = model.generate_content([prompt, *images])
    if not response.text:
        return None
        
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# 🖥 UI
st.title("🌙 Sleep Analyzer")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption=[f"画像 {i+1}" for i in range(len(images))], use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['result'] = result
                st.success("解析成功！")
                st.json(result)
            except Exception as e:
                st.error(f"解析失敗 (モデル名やキーを確認): {e}")

if 'result' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                r = st.session_state['result']
                row = [r.get('date'), r.get('sleep_score'), r.get('total_sleep'), r.get('fall_asleep'), r.get('wake_up'), r.get('rem'), r.get('light'), r.get('deep'), r.get('avg_hr'), r.get('min_hr'), r.get('max_hr'), r.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("保存完了！")
                del st.session_state['result']
            except Exception as e:
                st.error(f"保存失敗 (Secretsの設定を確認): {e}")