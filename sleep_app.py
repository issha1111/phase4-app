import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 1. ページ設定
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙")

# 2. 接続設定
# Gemini API
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # Secretsから [gcp_service_account] の中身を取得
    try:
        creds = dict(st.secrets["gcp_service_account"])
        # 【重要】TOMLで保存された '\\n' (文字) を '\n' (改行コード) に戻す
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        
        gc = gspread.service_account_from_dict(creds)
        # スプレッドシート名とタブ名が正しいか確認
        return gc.open('Phase4_Log').worksheet('SleepLog')
    except Exception as e:
        st.error(f"Google接続エラー: {e}")
        raise e

# 3. AI解析エンジン (Gemini 3 Flash Preview)
def analyze_images(images):
    # 最新モデルを指定
    model = genai.GenerativeModel('gemini-3-flash-preview')
    prompt = """睡眠アプリのスクショから項目を抽出しJSON形式で返して。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr"""
    
    response = model.generate_content([prompt, *images])
    # 余計な記号を削ってJSONとして読み込む
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# 4. UIレイアウト
st.title("🌙 Sleep Analyzer G3")
uploaded_files = st.file_uploader("スクショをアップ", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    # 画像と説明文の数を一致させる（エラー回避）
    captions = [f"画像 {i+1}" for i in range(len(images))]
    st.image(images, caption=captions, use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("最新AIが解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_data'] = result
                st.success("解析完了！内容を確認してください。")
                st.json(result)
            except Exception as e:
                st.error(f"解析失敗: {e}")

# 5. スプレッドシート保存
if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                # スプレッドシートの列順に並べる
                row = [
                    d.get('date'), d.get('sleep_score'), d.get('total_sleep'),
                    d.get('fall_asleep'), d.get('wake_up'), d.get('rem'),
                    d.get('light'), d.get('deep'), d.get('avg_hr'),
                    d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')
                ]
                sheet.append_row(row)
                st.balloons()
                st.success("スプレッドシートに保存しました！")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存失敗: {e}")