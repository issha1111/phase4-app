import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙")

# ⚙️ 接続設定
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. Secretsからgcp_jsonを取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. Invalid \escape エラーを根絶するための文字列クリーニング
    # バックスラッシュをエスケープしつつ、改行コードは維持する
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    
    # 3. JSONとして読み込む（strict=Falseで制御文字エラーを防ぐ）
    creds_dict = json.loads(safe_json, strict=False)
    
    # 4. 秘密鍵の中の "\\n" を Googleが認識できる本物の改行 "\n" に変換
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    # 5. 認証実行
    gc = gspread.service_account_from_dict(creds_dict)
    
    # スプレッドシート「Phase4_Log」の「SleepLog」タブを開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

def analyze_images(images):
    # 解析精度が高い 1.5 Flash を使用
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    睡眠アプリのスクリーンショットから以下の項目を抽出し、JSON形式でのみ返してください。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    ※JSON以外のテキストは含めないでください。
    """
    
    response = model.generate_content([prompt, *images])
    
    if not response.text:
        return None
        
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# 🖥 UIレイアウト
st.title("🌙 Sleep Analyzer")

uploaded_files = st.file_uploader("スクショをアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption=[f"画像 {i+1}" for i in range(len(images))], use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("解析中..."):
            try:
                result = analyze_images(images)
                if result:
                    st.session_state['sleep_data'] = result
                    st.success("解析成功！内容を確認して保存してください。")
                    st.json(result)
            except Exception as e:
                st.error(f"解析失敗: {e}")

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
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")