import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. あなたが設定した gcp_json を取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【Invalid \escape 対策】
    # 文字列の読み込みエラーを物理的に回避
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # 3. Google 認証用に改行コードを復元
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # スプレッドシート名とタブ名を確認
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash 専用)
# ==========================================
def analyze_images_with_g3(images):
    # ご希望のモデル名を指定。もし 404 が出る場合は 'models/gemini-3-flash' を試してください
    model = genai.GenerativeModel('models/gemini-3-flash')
    
    # 【2026年問題対策】
    prompt = """
    Extract sleep data from the screenshot and return ONLY a JSON object.
    IMPORTANT: The current year is 2026. Use "2026" for the date field.
    JSON keys: date(2026-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    
    # AIが余計なことを言っても JSON だけを抜き出す頑丈な処理
    res_text = response.text
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    if start == -1:
        return None
    return json.loads(res_text[start:end])

# ==========================================
# 🖥 UI
# ==========================================
st.title("🌙 Sleep Analyzer G3")
st.write("2026年のログとして Gemini 3 Flash で解析します。")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ Gemini 3 で解析を実行"):
        with st.spinner("AI 解析中..."):
            try:
                result = analyze_images_with_g3(images)
                if result:
                    st.session_state['sleep_data'] = result
                    st.success("解析成功！")
                    st.json(result) # ここで 2026-01-22 等になっているかチェック！
                else:
                    st.error("データの抽出に失敗しました。")
            except Exception as e:
                # もし gemini-3-flash でも 404 が出る場合は、モデル名の微調整が必要です
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
                st.success("スプレッドシートへの保存が完了しました！")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")