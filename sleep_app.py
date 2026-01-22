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

st.markdown("""
    <style>
    .stButton > button {
        width: 100%; border-radius: 12px; height: 3em;
        background-color: #007AFF; color: white; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 接続設定
# ==========================================
# Gemini API設定
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # Streamlit CloudのSecretsからJSONを読み込む
    creds = json.loads(st.secrets["gcp_json"])
    gc = gspread.service_account_from_dict(creds)
    # スプレッドシート名「Phase4_Log」の「SleepLog」タブを開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash Preview)
# ==========================================
def analyze_images_with_g3(images):
    # モデルの指定を Gemini 3 Flash Preview に変更
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = """
    あなたはプロの健康データアナリストです。
    提供された睡眠アプリのスクリーンショットから、以下の項目を正確に抽出し、JSON形式で返してください。
    
    【抽出項目】
    - date: 睡眠日 (YYYY-MM-DD 形式)
    - sleep_score: 睡眠スコア (数値)
    - total_sleep: 合計睡眠時間 (例: 6h43m)
    - fall_asleep: 入眠時刻 (HH:MM 24時間表記)
    - wake_up: 起床時刻 (HH:MM 24時間表記)
    - rem: レム睡眠時間 (例: 58m)
    - light: 浅い眠りの時間 (例: 4h31m)
    - deep: 深い眠りの時間 (例: 1h14m)
    - avg_hr: 平均心拍数 (数値)
    - min_hr: 最小心拍数 (数値)
    - max_hr: 最大心拍数 (数値)
    - resting_hr: 安静時心拍数 (数値)

    ※必ずJSON以外のテキストは含めないでください。
    """
    
    response = model.generate_content([prompt, *images])
    # JSONのパース（余計な装飾文字を削除）
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🌙 Sleep Analyzer G3")
st.write("最新の Gemini 3 Flash があなたの睡眠を解析します。")

# 画像アップローダー
uploaded_files = st.file_uploader("睡眠スクショをアップロード（3枚程度）", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption="解析対象の画像", use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("Gemini 3 が思考中..."):
            try:
                result = analyze_images_with_g3(images)
                st.session_state['sleep_data'] = result
                st.success("解析に成功しました！内容を確認してください。")
                st.json(result)
            except Exception as e:
                st.error(f"解析エラーが発生しました: {e}")

# 保存ボタン
if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                
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
                # 保存後はセッションをクリア
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")