import streamlit as st
import google.generativeai as genai
import gspread
import json
from datetime import datetime
from PIL import Image

# ==========================================
# 🚀 1. ページ設定
# ==========================================
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙", layout="centered")

# ==========================================
# ⚙️ 接続設定（修正ポイント！）
# ==========================================
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # Secretsから辞書形式で取得
    creds = dict(st.secrets["gcp_service_account"])
    
    # 【重要】Secretsの文字列内の \\n を 実際の改行コード \n に変換します
    # これをしないと、秘密鍵の形式エラーで保存が失敗します
    creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    
    gc = gspread.service_account_from_dict(creds)
    # スプレッドシート「Phase4_Log」の「SleepLog」タブを開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash Preview)
# ==========================================
def analyze_images_with_g3(images):
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = """
    睡眠アプリのスクリーンショットから以下の項目を抽出し、JSONで返してください。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    JSON以外のテキストは含めないでください。
    """
    
    response = model.generate_content([prompt, *images])
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 UIレイアウト
# ==========================================
st.title("🌙 Sleep Analyzer G3")

uploaded_files = st.file_uploader("睡眠スクショをアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    
    # 【修正】画像とキャプションの数を一致させてエラーを回避
    captions = [f"画像 {i+1}" for i in range(len(images))]
    st.image(images, caption=captions, use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("Gemini 3 が解析中..."):
            try:
                result = analyze_images_with_g3(images)
                st.session_state['sleep_data'] = result
                st.success("解析成功！")
                st.json(result)
            except Exception as e:
                st.error(f"解析エラー: {e}")

# ==========================================
# 📝 スプレッドシート保存処理
# ==========================================
if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                
                # 指定の順番でリストを作成
                row = [
                    d.get('date'), d.get('sleep_score'), d.get('total_sleep'),
                    d.get('fall_asleep'), d.get('wake_up'), d.get('rem'),
                    d.get('light'), d.get('deep'), d.get('avg_hr'),
                    d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')
                ]
                
                sheet.append_row(row)
                st.balloons()
                st.success("スプレッドシートへの保存が完了しました！")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")