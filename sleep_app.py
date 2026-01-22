import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

st.set_page_config(page_title="Sleep Analyzer", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
# 最新のAPIキーを設定
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    raw_json = st.secrets["gcp_json"].strip()
    
    # バックスラッシュの Invalid \escape 対策
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (404エラーを回避する自動選択)
# ==========================================
def analyze_images(images):
    # 利用可能なモデルを確認して、最適な名前をセットする
    # 基本は 'models/gemini-1.5-flash' だが、SDKによって違う場合があるため
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # 候補の中から最初に見つかったものを使う（優先順位順）
    target_model = 'models/gemini-1.5-flash' # デフォルト
    for candidate in ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-pro-vision']:
        if candidate in available_models:
            target_model = candidate
            break
    
    model = genai.GenerativeModel(target_model)
    
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
st.write("モデル名を自動調整して接続します。")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("AIが最適なルートを探して解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_result'] = result
                st.success("解析成功！")
                st.json(result)
            except Exception as e:
                st.error(f"解析失敗 (404対策済みですがエラーが出ました): {e}")

if 'sleep_result' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                r = st.session_state['sleep_result']
                row = [r.get('date'), r.get('sleep_score'), r.get('total_sleep'), r.get('fall_asleep'), r.get('wake_up'), r.get('rem'), r.get('light'), r.get('deep'), r.get('avg_hr'), r.get('min_hr'), r.get('max_hr'), r.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("保存完了しました！")
                del st.session_state['sleep_result']
            except Exception as e:
                st.error(f"保存エラー: {e}")