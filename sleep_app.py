import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    raw_json = st.secrets["gcp_json"].strip()
    # Invalid \escape 対策
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン（404エラー回避ロジック）
# ==========================================
def analyze_images(images):
    # 【修正ポイント】モデル名の頭に models/ を付与
    model_name = 'models/gemini-1.5-flash'
    
    try:
        model = genai.GenerativeModel(model_name)
        
        # 2026年固定＆JSON特化プロンプト
        prompt = """
        Extract sleep data from the screenshot and return ONLY a JSON object.
        IMPORTANT: The current year is 2026. Use "2026" for the date field.
        
        JSON keys: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
        """
        
        response = model.generate_content([prompt, *images])
        
        # JSON部分だけを確実に抜き出す
        res_text = response.text
        start = res_text.find('{')
        end = res_text.rfind('}') + 1
        if start == -1: return None
        
        return json.loads(res_text[start:end])
    
    except Exception as e:
        # 万が一 404 が出た場合、利用可能なモデル名をエラーに含めて表示する
        available = [m.name for m in genai.list_models()]
        raise Exception(f"Model error. Available models: {available}. Error: {e}")

# ==========================================
# 🖥 UI
# ==========================================
st.title("🌙 Sleep Analyzer (Model Fix)")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("2026年のログとして解析中..."):
            try:
                result = analyze_images(images)
                if result:
                    st.session_state['sleep_data'] = result
                    st.success("解析成功！")
                    st.json(result)
                else:
                    st.error("データ抽出に失敗しました。")
            except Exception as e:
                st.error(f"解析失敗: {e}")

if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                row = [d.get('date'), d.get('sleep_score'), d.get('total_sleep'), d.get('fall_asleep'), d.get('wake_up'), d.get('rem'), d.get('light'), d.get('deep'), d.get('avg_hr'), d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("保存完了！")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")