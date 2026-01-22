import streamlit as st 
import google.generativeai as genai 
import gspread 
import json 
from PIL import Image 

# 🚀 ページ設定
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
    
    # 【対策1】JSON読み込み前のバックスラッシュ洗浄
    # これにより char 1094 などの Invalid \escape エラーを物理的に防ぎます
    safe_json = raw_json.replace('\\', '\\\\').replace('\\\\n', '\\n') 
    
    # 読み込み（strict=Falseで制御文字への許容度を上げる）
    creds_dict = json.loads(safe_json, strict=False) 
    
    # 【対策2】秘密鍵内の改行をGoogleが認識できる形（\n）に復元
    if "private_key" in creds_dict: 
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip() 
        
    gc = gspread.service_account_from_dict(creds_dict) 
    return gc.open('Phase4_Log').worksheet('SleepLog') 

# ========================================== 
# 🧠 AI解析エンジン (2026年対応プロンプト) 
# ========================================== 
def analyze_images(images): 
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    # 【2026年問題対策】プロンプトに現在の日付コンテキストを追加
    prompt = """
    睡眠スクショからデータを抽出しJSONで返して。
    【重要】現在は2026年1月です。スクショに年が記載されていない場合は、必ず2026年として扱ってください。
    
    項目: date(YYYY-MM-DD), sleep_score, total_sleep, fall_asleep, wake_up, rem, light, deep, avg_hr, min_hr, max_hr, resting_hr
    ※JSONデータのみを出力してください。
    """ 
    
    response = model.generate_content([prompt, *images]) 
    if not response or not response.text: 
        return None 
        
    clean_text = response.text.replace('```json', '').replace('```', '').strip() 
    return json.loads(clean_text) 

# ========================================== 
# 🖥 UI 
# ========================================== 
st.title("🌙 Sleep Analyzer (2026 Edition)") 

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
                st.json(result) 
            except Exception as e: 
                st.error(f"解析失敗: {e}") 

# スプレッドシート保存処理
if 'sleep_data' in st.session_state: 
    if st.button("📝 スプレッドシートに保存"): 
        with st.spinner("スプレッドシートに書き込み中..."): 
            try: 
                sheet = get_worksheet() 
                d = st.session_state['sleep_data'] 
                
                # リストの作成
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