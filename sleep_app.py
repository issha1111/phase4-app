import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ⚙️ 接続設定
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. SecretsからJSONを取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【Invalid \escape 対策】
    # 文字列の中のバックスラッシュを安全な形に変換（char 1094エラーを粉砕します）
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # 3. 秘密鍵の改行をGoogleが求める本物の改行に復元
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    # スプレッドシート名とタブ名を確認
    return gc.open('Phase4_Log').worksheet('SleepLog')

def analyze_images(images):
    # あなたのリスト にあった正確なモデル名
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
    
    # 2026年1月22日であることをAIに叩き込む
    prompt = """
    睡眠スクショからデータを抽出しJSONで返して。
    【最重要】現在は2026年1月です。日付の年は必ず「2026」にしてください。
    項目: date(2026-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    res_text = response.text
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# --- UI ---
st.title("🌙 Sleep Analyzer 2026 (Final)")

files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if files:
    images = [Image.open(f) for f in files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ 2026年のログとして解析"):
        with st.spinner("AI解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_data'] = result
                st.success("解析成功！")
                st.json(result) # ここが 2026 になっていればOK！
            except Exception as e:
                # 期限切れエラー が出たらキーを貼り替えてください
                st.error(f"解析失敗: {e}")

if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("スプレッドシートに保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                row = [d.get(k) for k in ['date', 'sleep_score', 'total_sleep', 'fall_asleep', 'wake_up', 'rem', 'light', 'deep', 'avg_hr', 'min_hr', 'max_hr', 'resting_hr']]
                sheet.append_row(row)
                st.balloons()
                st.success("保存完了！2026年のログが刻まれました。")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")