import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ⚙️ 接続設定
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. 生のSecrets文字列を取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【最強のInvalid \escape対策】
    # 文字列の中のバックスラッシュを一度安全な形に変換します。
    # これで char 1094 のエラーを物理的に消し去ります。
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    
    # 3. JSONとして辞書に変換（strict=Falseで制御文字エラーも防ぐ）
    creds_dict = json.loads(safe_json, strict=False)
    
    # 4. Google認証用の改行コードを最終調整
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    # 5. 認証実行
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

def analyze_images(images):
    # 安定版の1.5-flashを使用
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 【2026年問題対策】プロンプトで2026年であることを強調
    prompt = """
    睡眠アプリのスクリーンショットからデータを抽出し、JSON形式でのみ返してください。
    【重要】現在は2026年1月です。日付の年は必ず「2026」にしてください。
    項目: date(2026-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# 🖥 UI
st.title("🌙 Sleep Analyzer (2026 Edition)")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("2026年のデータとして解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['data'] = result
                st.success("解析成功！")
                st.json(result) # ここで 2026 になっているか確認できます！
            except Exception as e:
                st.error(f"解析失敗: {e}")

if 'data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                r = st.session_state['data']
                row = [r.get('date'), r.get('sleep_score'), r.get('total_sleep'), r.get('fall_asleep'), r.get('wake_up'), r.get('rem'), r.get('light'), r.get('deep'), r.get('avg_hr'), r.get('min_hr'), r.get('max_hr'), r.get('resting_hr')]
                sheet.append_row(row)
                st.balloons()
                st.success("2026年のログとして保存完了！")
                del st.session_state['data']
            except Exception as e:
                # このエラーが出るならコードが古いままで反映されていません！
                st.error(f"保存エラー: {e}")