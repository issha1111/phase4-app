import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# ==========================================
# 🚀 1. ページ設定
# ==========================================
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙", layout="centered")

# スタイルの調整
st.markdown("""
    <style>
    .stButton > button {
        width: 100%; border-radius: 10px; height: 3em;
        background-color: #007AFF; color: white; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 接続設定 (認証エラー対策版)
# ==========================================
# Gemini APIの設定
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Secretsに GOOGLE_API_KEY が見つかりません。")

def get_worksheet():
    # --- あなたが修正した鉄壁の認証ロジック ---
    raw_json = st.secrets["gcp_json"].strip() # 前後のゴミを削除
    creds_dict = json.loads(raw_json)
    
    if "private_key" in creds_dict:
        # 改行コードを整えつつ、さらに余計なスペースを削除
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # ---------------------------------------
    
    # タブ名「SleepLog」を開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash Preview)
# ==========================================
def analyze_images_with_g3(images):
    # 最新の Gemini 3 Flash Preview を指定
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = """
    睡眠アプリのスクリーンショットから以下の項目を抽出し、JSON形式でのみ返してください。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    ※余計な解説は一切不要です。
    """
    
    response = model.generate_content([prompt, *images])
    
    if not response.text:
        return None
        
    # JSON以外の装飾文字を削除
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🌙 Sleep Analyzer G3")
st.write("認証エラーを修正した最新版です。")

# 画像アップローダー
uploaded_files = st.file_uploader("睡眠スクショをアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    
    # 画像とキャプションの数を一致させる
    captions = [f"画像 {i+1}" for i in range(len(images))]
    st.image(images, caption=captions, use_container_width=True)
    
    # --- 解析実行 ---
    if st.button("✨ AI解析を実行"):
        with st.spinner("Gemini 3 が解析中..."):
            try:
                result = analyze_images_with_g3(images)
                if result:
                    st.session_state['sleep_data_v3'] = result
                    st.success("解析に成功しました！内容を確認してください。")
                    st.json(result)
            except Exception as e:
                st.error(f"解析エラー: {e}")

# --- 保存処理 ---
if 'sleep_data_v3' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("スプレッドシートに保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data_v3']
                
                # スプレッドシートの列順に合わせてリスト化
                row = [
                    d.get('date'), d.get('sleep_score'), d.get('total_sleep'),
                    d.get('fall_asleep'), d.get('wake_up'), d.get('rem'),
                    d.get('light'), d.get('deep'), d.get('avg_hr'),
                    d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')
                ]
                
                sheet.append_row(row)
                st.balloons()
                st.success("スプレッドシートへの保存が完了しました！")
                
                # 保存完了後にセッションデータを消去
                del st.session_state['sleep_data_v3']
            except Exception as e:
                st.error(f"保存エラー: {e}")