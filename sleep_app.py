import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# ==========================================
# 🚀 1. ページ設定 & デザイン
# ==========================================
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙", layout="centered")

st.markdown("""
    <style>
    .stButton > button {
        width: 100%; border-radius: 12px; height: 3.5em;
        background-color: #007AFF; color: white; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 接続設定 (認証エラー対策版)
# ==========================================
# Gemini API 設定
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Secretsに GOOGLE_API_KEY が見つかりません。")

def get_worksheet():
    # 1. 秘密鍵（gcp_json）を読み込む
    if "gcp_json" not in st.secrets:
        st.error("Secretsに gcp_json が見つかりません。")
        st.stop()
        
    raw_json = st.secrets["gcp_json"]
    creds_dict = json.loads(raw_json)
    
    # 2. 【ここが最重要！】バックスラッシュのエラーを無理やり直す
    # 秘密鍵の中の "\\n" を 本物の改行 "\n" に書き換えます
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # 3. 修正した鍵でログイン
    gc = gspread.service_account_from_dict(creds_dict)
    
    # タブ名「SleepLog」を開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash Preview)
# ==========================================
def analyze_images_with_g3(images):
    # 解析実績のある Gemini 3 Flash Preview を使用
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = """
    睡眠アプリのスクリーンショットから以下の項目を抽出し、JSON形式で返してください。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    ※JSON以外の説明文は一切含めないでください。
    """
    
    response = model.generate_content([prompt, *images])
    
    if not response.text:
        return None
        
    # JSON以外の余計な文字（```json など）を削る
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🌙 Sleep Analyzer G3")
st.write("解析が通ることは確認済み。あとは保存するだけです！")

# 画像アップローダー
uploaded_files = st.file_uploader("睡眠スクショを複数選択", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    
    # 画像とキャプションの数を一致させてエラーを回避
    captions = [f"画像 {i+1}" for i in range(len(images))]
    st.image(images, caption=captions, use_container_width=True)
    
    # --- 解析実行 ---
    if st.button("✨ AI解析を実行"):
        with st.spinner("Gemini 3 が思考中..."):
            try:
                result = analyze_images_with_g3(images)
                if result:
                    st.session_state['sleep_result'] = result
                    st.success("解析に成功しました！内容を確認して保存してください。")
                    st.json(result)
                else:
                    st.error("AIからの返答が空でした。再度お試しください。")
            except Exception as e:
                st.error(f"解析エラー: {e}")

# --- 保存処理 ---
if 'sleep_result' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("スプレッドシートに書き込み中..."):
            try:
                sheet = get_worksheet()
                r = st.session_state['sleep_result']
                
                # スプレッドシートの列順に合わせてリスト化
                row = [
                    r.get('date'), r.get('sleep_score'), r.get('total_sleep'),
                    r.get('fall_asleep'), r.get('wake_up'), r.get('rem'),
                    r.get('light'), r.get('deep'), r.get('avg_hr'),
                    r.get('min_hr'), r.get('max_hr'), r.get('resting_hr')
                ]
                
                sheet.append_row(row)
                st.balloons()
                st.success("スプレッドシートへの保存が完了しました！")
                
                # 保存完了後にデータを消去
                del st.session_state['sleep_result']
            except Exception as e:
                st.error(f"保存エラー: {e}")