import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

st.set_page_config(page_title="Sleep Analyzer", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
# APIキーを設定（Secretsの GOOGLE_API_KEY を使用）
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # Secretsから鍵を取得（名前を gcp_json に統一）
    if "gcp_json" not in st.secrets:
        st.error("Secretsに 'gcp_json' が見つかりません。")
        st.stop()
        
    raw_json = st.secrets["gcp_json"].strip()
    
    # バックスラッシュの Invalid \escape 対策
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # スプレッドシート名とタブ名が正しいか確認
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (安定版を使用)
# ==========================================
def analyze_images(images):
    # 404エラーを避けるため、確実に存在する安定版を使用
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """睡眠スクショからデータを抽出しJSONで返して。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr"""
    
    response = model.generate_content([prompt, *images])
    if not response or not response.text:
        return None
        
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 UI
# ==========================================
st.title("🌙 Sleep Analyzer")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption=[f"画像 {i+1}" for i in range(len(images))], use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_data'] = result
                st.success("解析成功！内容を確認してください。")
                st.json(result)
            except Exception as e:
                st.error(f"解析失敗 (モデル名を確認): {e}")

if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                row = [d.get('date'), d.get('sleep_score'), d.get('total_sleep'), d.get('fall_asleep'), d.get('wake_up'), d.get('rem'), d.get('light'), d.get('deep'), d.get('avg_hr'), d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("保存完了しました！")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")