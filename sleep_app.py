import streamlit as st
import google.generativeai as genai
import gspread
import json
import re
from PIL import Image

# ==========================================
# 🚀 1. ページ設定
# ==========================================
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定 (Invalid \escape 対策版)
# ==========================================
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. Secretsから生データを取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【魔法のクリーニング】
    # Invalid \escape エラー（char 1094など）を回避するため、
    # 文字列の中のバックスラッシュをJSONが許容する形に強制変換します
    # 一度全てのバックスラッシュをエスケープし、必要な \n だけ元に戻す手法です
    cleaned_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    
    # 3. JSONとして読み込み（strict=Falseで制御文字にも寛容にする）
    try:
        creds_dict = json.loads(cleaned_json, strict=False)
    except Exception:
        # もし上記でダメなら、元のままで再トライ
        creds_dict = json.loads(raw_json, strict=False)
    
    # 4. 秘密鍵の中の改行コードを最終調整
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    # 5. 認証実行
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (Gemini 3 Flash Preview)
# ==========================================
def analyze_images_with_g3(images):
    model = genai.GenerativeModel('gemini-3-flash-preview')
    prompt = """睡眠アプリのスクショからデータを抽出しJSONで返して。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr"""
    
    response = model.generate_content([prompt, *images])
    if not response.text:
        return None
        
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🌙 Sleep Analyzer G3")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption=[f"画像 {i+1}" for i in range(len(images))], use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("Gemini 3 が解析中..."):
            try:
                result = analyze_images_with_g3(images)
                if result:
                    st.session_state['sleep_data_final'] = result
                    st.success("解析成功！")
                    st.json(result)
            except Exception as e:
                st.error(f"解析失敗: {e}")

if 'sleep_data_final' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data_final']
                row = [d.get('date'), d.get('sleep_score'), d.get('total_sleep'), d.get('fall_asleep'), d.get('wake_up'), d.get('rem'), d.get('light'), d.get('deep'), d.get('avg_hr'), d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("保存完了！")
                del st.session_state['sleep_data_final']
            except Exception as e:
                st.error(f"保存エラー: {e}")