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
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n')
    creds_dict = json.loads(safe_json, strict=False)
    
    # 3. 秘密鍵の改行を復元
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    gc = gspread.service_account_from_dict(creds_dict)
    return gc.open('Phase4_Log').worksheet('SleepLog')

def normalize_time_field(value):
    """
    Geminiから返ってきた値を必ず H:MM 形式の文字列にする。
    ありうる入力パターン:
      - "0:47" / "00:47"  → そのまま H:MM で返す
      - 57                → 分として H:MM に変換
      - 57.0              → 同上
      - "57"              → 同上
      - "1:18:00"         → H:MM に変換
    """
    if value is None or value == "":
        return "0:00"

    s = str(value).strip()

    # "H:MM" か "HH:MM" の形式なら直接パース
    if ":" in s:
        parts = s.split(":")
        h = int(parts[0])
        m = int(parts[1])
        return f"{h}:{m:02d}"

    # 数値（分）の場合
    try:
        total_minutes = int(float(s))
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}:{m:02d}"
    except ValueError:
        return "0:00"
        

def analyze_images(images):
    # モデル設定
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
    
    # 2026年固定プロンプト
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

# --- UIレイアウト ---
st.title("🌙 Sleep Analyzer 2026 (UI Fix)")

files = st.file_uploader("スクショを選択", accept_multiple_files=True)

if files:
    images = [Image.open(f) for f in files]
    
    # 🔽 ここでレイアウト変更！ボタンを画像より上に配置 🔽
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    # 左側：解析ボタン
    with col1:
        if st.button("✨ 解析実行", use_container_width=True):
            with st.spinner("AI解析中..."):
                try:
                    result = analyze_images(images)
                    st.session_state['sleep_data'] = result
                    st.success("解析成功！")
                except Exception as e:
                    st.error(f"解析失敗: {e}")

    # 右側：保存ボタン（解析データがある時だけ押せるように表示）
    with col2:
        if 'sleep_data' in st.session_state:
            if st.button("📝 保存実行", use_container_width=True):
                with st.spinner("保存中..."):
                    try:
                        sheet = get_worksheet()
                        d = st.session_state['sleep_data']
                        row = [d.get(k) for k in ['date', 'sleep_score', 'total_sleep', 'fall_asleep', 'wake_up', 'rem', 'light', 'deep', 'avg_hr', 'min_hr', 'max_hr', 'resting_hr']]
                        sheet.append_row(row)
                        st.balloons()
                        st.success("保存完了！")
                        del st.session_state['sleep_data']
                    except Exception as e:
                        st.error(f"保存エラー: {e}")

    # 解析結果のJSONも上の方が見やすいのでここに配置
    if 'sleep_data' in st.session_state:
        st.caption("解析結果データ:")
        st.json(st.session_state['sleep_data'])

    # 画像は一番下に追いやる（確認用）
    st.markdown("---")
    with st.expander("アップロードした画像を確認する"):
        st.image(images, use_container_width=True)
