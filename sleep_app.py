import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

st.set_page_config(page_title="Sleep Analyzer 2026", page_icon="🌙")

# ==========================================
# ⚙️ 接続設定
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    if "gcp_json" not in st.secrets:
        st.error("Secretsに 'gcp_json' が見つかりません。")
        st.stop()
        
    raw_json = st.secrets["gcp_json"].strip()
    
    # 【Invalid \escape 対策】
    # StreamlitのSecretsから読み込む際のバックスラッシュの挙動を安定させます
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # Google認証用に改行コードを復元
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

# ==========================================
# 🧠 AI解析エンジン (2026年固定)
# ==========================================
def analyze_images(images):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 【2026年問題対策】プロンプトに現在の日付コンテキストを追加
    prompt = """
    睡眠アプリのスクリーンショットからデータを抽出し、JSON形式で返してください。
    【重要】現在は2026年1月です。スクショに年が明記されていない場合は、2026年として扱ってください。
    
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    """
    
    response = model.generate_content([prompt, *images])
    if not response or not response.text:
        return None
        
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# ==========================================
# 🖥 UI
# ==========================================
st.title("🌙 Sleep Analyzer G3 (2026)")

uploaded_files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption=[f"画像 {i+1}" for i in range(len(images))], use_container_width=True)
    
    if st.button("✨ AI解析を実行"):
        with st.spinner("2026年のデータとして解析中..."):
            try:
                result = analyze_images(images)
                st.session_state['sleep_data'] = result
                st.success("解析成功！内容を確認してください。")
                st.json(result) # ここで 2026 になっているかチェック！
            except Exception as e:
                st.error(f"解析失敗: {e}")

if 'sleep_data' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("保存中..."):
            try:
                sheet = get_worksheet()
                d = st.session_state['sleep_data']
                
                # リスト形式でスプレッドシートに追加
                row = [
                    d.get('date'), d.get('sleep_score'), d.get('total_sleep'),
                    d.get('fall_asleep'), d.get('wake_up'), d.get('rem'),
                    d.get('light'), d.get('deep'), d.get('avg_hr'),
                    d.get('min_hr'), d.get('max_hr'), d.get('resting_hr')
                ]
                
                sheet.append_row(row)
                st.balloons()
                st.success("2026年のログとして保存完了しました！")
                del st.session_state['sleep_data']
            except Exception as e:
                st.error(f"保存エラー: {e}")