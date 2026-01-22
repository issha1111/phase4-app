import streamlit as st
import google.generativeai as genai
import gspread
import json
from datetime import datetime
from PIL import Image

# ==========================================
# 🚀 1. ページ設定 & デザイン
# ==========================================
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙", layout="centered")

# iOSアプリ風のボタンデザイン
st.markdown("""
    <style>
    .stButton > button {
        width: 100%; border-radius: 12px; height: 3.5em;
        background-color: #007AFF; color: white; font-weight: bold;
        border: none; margin-top: 10px;
    }
    .stButton > button:active {
        background-color: #0051a8;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 接続設定
# ==========================================
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # Streamlit CloudのSecretsから認証情報を取得
    creds = json.loads(st.secrets["gcp_json"])
    gc = gspread.service_account_from_dict(creds)
    # スプレッドシート「Phase4_Log」の「SleepLog」タブを指定
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash Preview)
# ==========================================
def analyze_images_with_g3(images):
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = """
    あなたは健康管理のスペシャリストです。提供された睡眠アプリの画像から、以下の項目を抽出し、JSON形式でのみ回答してください。
    
    【抽出項目】
    - date: 睡眠日 (YYYY-MM-DD)
    - sleep_score: スコア (数値)
    - total_sleep: 合計睡眠時間 (例: 6h43m)
    - fall_asleep: 入眠時刻 (HH:MM)
    - wake_up: 起床時刻 (HH:MM)
    - rem: レム睡眠 (例: 58m)
    - light: 浅い眠り (例: 4h31m)
    - deep: 深い眠り (例: 1h14m)
    - avg_hr: 平均心拍数 (数値)
    - min_hr: 最小心拍数 (数値)
    - max_hr: 最大心拍数 (数値)
    - resting_hr: 安静時心拍数 (数値)
    """
    
    response = model.generate_content([prompt, *images])
    # JSON以外の余計な文字（```jsonなど）を除去
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🌙 Sleep Analyzer G3")
st.write("画像をアップロードして、AI解析を開始してください。")

uploaded_files = st.file_uploader("睡眠のスクショをアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    
    # 【修正ポイント】画像の数に合わせてキャプションのリストを作成
    captions = [f"解析対象の画像 {i+1}" for i in range(len(images))]
    st.image(images, caption=captions, use_container_width=True)
    
    if st.button("✨ AIで睡眠データを解析"):
        with st.spinner("Gemini 3 が画像を読み取っています..."):
            try:
                result = analyze_images_with_g3(images)
                st.session_state['sleep_result'] = result
                st.success("解析完了！")
                st.json(result)
            except Exception as e:
                st.error(f"解析に失敗しました: {e}")

# 保存処理
if 'sleep_result' in st.session_state:
    if st.button("📝 スプレッドシートへ保存"):
        with st.spinner("保存しています..."):
            try:
                sheet = get_worksheet()
                r = st.session_state['sleep_result']
                
                # スプレッドシートの列順(Date〜RestingHR)に並べ替え
                row_data = [
                    r.get('date'), r.get('sleep_score'), r.get('total_sleep'),
                    r.get('fall_asleep'), r.get('wake_up'), r.get('rem'),
                    r.get('light'), r.get('deep'), r.get('avg_hr'),
                    r.get('min_hr'), r.get('max_hr'), r.get('resting_hr')
                ]
                
                sheet.append_row(row_data)
                st.balloons()
                st.success("スプレッドシートの 'SleepLog' に保存しました！")
                del st.session_state['sleep_result']
            except Exception as e:
                st.error(f"保存エラー: {e}")