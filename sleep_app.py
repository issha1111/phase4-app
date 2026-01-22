import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# ページ設定
st.set_page_config(page_title="Sleep Analyzer", page_icon="🌙")

# 接続設定
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    if "gcp_json" in st.secrets:
        creds = json.loads(st.secrets["gcp_json"])
        gc = gspread.service_account_from_dict(creds)
    else:
        gc = gspread.service_account(filename='service_account.json')
    return gc.open('Phase4_Log').worksheet('SleepLog')

# AI解析
def analyze_images(images):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = """
    睡眠アプリのスクリーンショットからデータを抽出し、JSON形式で返してください。
    キー名は date, sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr としてください。
    """
    response = model.generate_content([prompt, *images])
    text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

st.title("🌙 AI Sleep Analyzer")
uploaded_files = st.file_uploader("スクショをアップ", type=['png', 'jpg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    if st.button("AI解析実行"):
        with st.spinner("解析中..."):
            result = analyze_images(images)
            st.session_state['result'] = result
            st.json(result)

if 'result' in st.session_state:
    if st.button("シートに保存"):
        sheet = get_worksheet()
        r = st.session_state['result']
        sheet.append_row([r['date'], r['sleep_score'], r['total_sleep'], r['fall_asleep'], r['wake_up'], r['rem'], r['light'], r['deep'], r['avg_hr'], r['min_hr'], r['max_hr'], r['resting_hr']])
        st.success("保存完了！")