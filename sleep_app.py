import streamlit as st
import google.generativeai as genai
import gspread
import json
from PIL import Image

# 🚀 ページ設定
st.set_page_config(page_title="Sleep Analyzer G3", page_icon="🌙")

# ⚙️ 接続設定
# 最新のAPIキーを適用
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_worksheet():
    # 1. Secretsからgcp_jsonを取得
    raw_json = st.secrets["gcp_json"].strip()
    
    # 2. 【最重要】Invalid \escape エラーを根絶するクリーニング
    # バックスラッシュをエスケープしつつ、改行コードはJSONとして維持する
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    
    # 3. JSONとして読み込む（strict=Falseで制御文字エラーを防ぐ）
    creds_dict = json.loads(safe_json, strict=False)
    
    # 4. 秘密鍵の中の改行コードを、Googleが認識できる本物の改行 "\n" に変換
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    # 5. 認証実行
    gc = gspread.service_account_from_dict(creds_dict)
    
    # スプレッドシート名「Phase4_Log」、タブ名「SleepLog」を開く
    return gc.open('Phase4_Log').worksheet('SleepLog')

def analyze_images_with_g3(images):
    # 最新モデル gemini-3-flash を使用
    # もし404エラーが出る場合は 'gemini-1.5-flash' に戻してください
    model = genai.GenerativeModel('gemini-3-flash')
    
    prompt = """
    睡眠アプリのスクリーンショットから以下の項目を抽出し、JSON形式でのみ返してください。
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    ※JSON以外の説明文は一切含めないでください。
    """
    
    response = model.generate_content([prompt, *images])
    
    if not response.text:
        return None
        
    # 余計なマークダウン装飾を削除
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# 🖥 UIレイアウト
st.title("🌙 Sleep Analyzer G3")
st.write("最新の gemini-3-flash で睡眠ログを自動化します。")

uploaded_files = st.file_uploader("睡眠スクショをアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    st.image(images, caption=[f"画像 {i+1}" for i in range(len(images))], use_container_width=True)
    
    # --- 解析実行 ---
    if st.button("✨ AI解析を実行"):
        with st.spinner("Gemini 3 が解析中..."):
            try:
                result = analyze_images_with_g3(images)
                if result:
                    st.session_state['sleep_result'] = result
                    st.success("解析成功！データを確認してください。")
                    st.json(result)
            except Exception as e:
                st.error(f"解析失敗（モデル名またはAPIキーを確認）: {e}")

# --- 保存処理 ---
if 'sleep_result' in st.session_state:
    if st.button("📝 スプレッドシートに保存"):
        with st.spinner("スプレッドシートに保存中..."):
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
                del st.session_state['sleep_result']
            except Exception as e:
                st.error(f"保存エラー（Secretsの設定を確認してください）: {e}")