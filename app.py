import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, timezone
import gspread
import json

# ==========================================
# 🚀 1. ページ設定 & デザイン (一番上に置く)
# ==========================================
st.set_page_config(page_title="Phase 4 Dashboard", page_icon="⚡", layout="centered")

# おしゃれCSS（青ボタン & ヘッダー隠し）
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    div.stButton > button {
        width: 100%;
        background-color: #007AFF;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        border: none;
    }
    div.stButton > button:hover { background-color: #0056b3; color: white; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 設定エリア
# ==========================================
SERVICE_ACCOUNT_FILE = 'service_account.json' 
SPREADSHEET_NAME = 'Phase4_Log'
JST = timezone(timedelta(hours=+9), 'JST')

def get_now_jst():
    return datetime.now(JST)

def get_today_str():
    return get_now_jst().strftime('%Y-%m-%d')

# ==========================================
# 🛠 関数定義
# ==========================================
@st.cache_resource
def get_worksheet():
    try:
        if "gcp_json" in st.secrets:
            creds_dict = json.loads(st.secrets["gcp_json"])
            gc = gspread.service_account_from_dict(creds_dict)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        return gc.open(SPREADSHEET_NAME).sheet1
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def routine_block(title, items, key_prefix, target_time_str=None, default_time_val=None):
    done_key = f"{key_prefix}_done"
    time_key = f"{key_prefix}_time"
    picker_key = f"{key_prefix}_picker"

    if done_key not in st.session_state: st.session_state[done_key] = False
    if time_key not in st.session_state: st.session_state[time_key] = "07:00"

    if st.session_state[done_key]:
        with st.container(border=False):
            actual_time = st.session_state[time_key]
            clean_title = title.split('<')[0].strip()
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; color: gray;">
                <h4 style="margin:0; text-decoration: line-through;">{clean_title}</h4>
                <small>✅ Completed at {actual_time}</small>
            </div>
            """, unsafe_allow_html=True)
            if st.button("↺ 修正", key=f"{key_prefix}_undo"):
                st.session_state[done_key] = False
                st.rerun()
        return st.session_state[time_key]
    else:
        with st.container(border=True):
            display_title = title
            if target_time_str:
                display_title = f"{title} <span style='color:#FF4B4B; font-size:0.9em;'>({target_time_str})</span>"
            st.markdown(f"### {display_title}", unsafe_allow_html=True)
            for item in items: st.text(f"• {item}")
            st.markdown("---")
            c1, c2 = st.columns([1, 1])
            with c1:
                initial_value = st.session_state.get(picker_key, default_time_val or time(7, 0))
                input_time = st.time_input("実施時間", value=initial_value, key=picker_key)
            with c2:
                st.write(""); st.write("")
                if st.button("✅ 完了", key=f"{key_prefix}_btn", type="primary", use_container_width=True):
                    st.session_state[done_key] = True
                    st.session_state[time_key] = input_time.strftime('%H:%M')
                    st.rerun()
        return st.session_state[time_key]

# ==========================================
# 📥 データ読み込み & 初期化
# ==========================================
if 'init_done' not in st.session_state:
    st.session_state['init_done'] = False
    st.session_state['wake_up_time'] = time(7, 0)
    st.session_state['workout_type'] = "なし"
    st.session_state['workout_time'] = time(18, 0)
    st.session_state['bed_time'] = time(23, 30)

sheet = get_worksheet()
today_str = get_today_str()

if sheet and not st.session_state['init_done']:
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if not df.empty and 'Date' in df.columns:
            today_data = df[df['Date'] == today_str]
            if not today_data.empty:
                row = today_data.iloc[0]
                st.session_state['wake_up_time'] = datetime.strptime(str(row['WakeTime']), '%H:%M:%S').time()
                st.session_state['workout_type'] = str(row['Workout'])
                progress = json.loads(str(row['Progress']))
                for key, val in progress.items():
                    st.session_state[f"{key}_done"] = True
                    st.session_state[f"{key}_time"] = val
                    try: st.session_state[f"{key}_picker"] = datetime.strptime(val, '%H:%M').time()
                    except: pass
    except: pass
    st.session_state['init_done'] = True

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🔥 Phase 4: Full Routine")
st.caption(f"{today_str} (JST)")

# --- 同期ボタン ---
if st.button("🔄 全データを同期 (Save to Drive)", type="primary", use_container_width=True):
    if not sheet: st.error("Sheet Error")
    else:
        with st.spinner("Saving..."):
            progress_dict = {}
            keys = ["morning_ignition", "morning_muscle", "morning_walk", "morning_breakfast", "lunch", "evening_pre_workout", "evening_workout", "dinner_after", "bedtime_routine"]
            for k in keys:
                if st.session_state.get(f"{k}_done", False):
                    progress_dict[k] = st.session_state.get(f"{k}_time", "")
            
            row_data = [
                today_str, 
                st.session_state['wake_up_time'].strftime('%H:%M:%S'), 
                st.session_state['workout_type'], 
                st.session_state.get('sleep_score', 0), 
                st.session_state.get('body_feeling', ""), 
                st.session_state['workout_time'].strftime('%H:%M:%S'), 
                json.dumps(progress_dict, ensure_ascii=False)
            ]
            try:
                dates = sheet.col_values(1)
                if today_str in dates:
                    row_index = dates.index(today_str) + 1
                    for i, val in enumerate(row_data): sheet.update_cell(row_index, i+1, val)
                    st.success("✅ 保存完了！")
                else:
                    sheet.append_row(row_data)
                    st.success("✅ 新規保存完了！")
            except Exception as e: st.error(f"Error: {e}")

# --- 🛠 進化したスケジュール設定 ---
with st.expander("🛠 スケジュール設定", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        st.session_state['wake_up_time'] = st.time_input("👀 起床", value=st.session_state['wake_up_time'])
        st.session_state['workout_time'] = st.time_input("運動開始予定", value=st.session_state['workout_time'])
    
    with c2:
        # ★動的メニューの実装
        current_w = st.session_state['workout_type']
        # 初期値の判定
        base_options = ["ウォーキング", "エアロバイク", "サウナ", "筋トレ", "なし"]
        default_idx = 4 # なし
        for i, opt in enumerate(base_options):
            if opt in current_w: default_idx = i
        
        menu_type = st.selectbox("🏃 運動種目", base_options, index=default_idx)
        
        final_workout = "なし"
        if menu_type == "ウォーキング":
            val = st.number_input("距離 (km)", value=5.0, step=0.1)
            final_workout = f"ウォーキング ({val}km)"
        elif menu_type == "エアロバイク":
            val = st.number_input("時間 (分)", value=45, step=5)
            final_workout = f"エアロバイク ({val}分)"
        elif menu_type == "サウナ":
            val = st.number_input("セット数", value=3, step=1)
            final_workout = f"サウナ ({val}セット)"
        elif menu_type == "筋トレ":
            val = st.text_input("内容", value="30分")
            final_workout = f"筋トレ ({val})"
        
        st.session_state['workout_type'] = final_workout
        st.session_state['bed_time'] = st.time_input("🛏️ 就寝目標", value=st.session_state['bed_time'])

# --- タイムライン ---
st.markdown("### 🌅 Morning")
today_date = get_now_jst().date()

ign_time = routine_block("1. 爆速点火フェーズ", ["MCTオイル 7g", "カルニチン 2錠", "サプリ各種"], "morning_ignition", default_time_val=time(7, 15))

# 連動時間の計算
try:
    ig_dt = datetime.combine(today_date, datetime.strptime(ign_time, '%H:%M').time())
    target_muscle_str = (ig_dt + timedelta(minutes=30)).strftime('%H:%M')
    target_muscle_val = (ig_dt + timedelta(minutes=30)).time()
except:
    target_muscle_str = "--:--"; target_muscle_val = time(7, 45)

routine_block("2. 筋肉起動 & 温冷浴", ["ヨガ・プランク", "温水3分 ➡ 冷水1分"], "morning_muscle", f"{target_muscle_str} Start", default_time_val=target_muscle_val)
routine_block("3. 朝散歩", ["外気浴 15-20分"], "morning_walk", default_time_val=time(8, 0))
routine_block("4. 朝食 & サプリ", ["ベースブレッド", "サプリ各種"], "morning_breakfast", default_time_val=time(8, 30))

st.markdown("### ☀️ Lunch")
routine_block("5. 昼食 (代謝維持)", ["ベースブレッド", "エビオス等"], "lunch", default_time_val=time(12, 0))

# 運動がある場合のみ表示
workout_type = st.session_state['workout_type']
if "なし" not in workout_type:
    st.markdown("### 🌆 Evening (Extra Burn)")
    w_time = st.session_state['workout_time']
    pre_w_str = (datetime.combine(today_date, w_time) - timedelta(minutes=30)).strftime('%H:%M')
    pre_w_val = (datetime.combine(today_date, w_time) - timedelta(minutes=30)).time()
    
    routine_block(f"6. 運動前準備 ({workout_type})", ["カルニチン 2錠 (30分前)"], "evening_pre_workout", pre_w_str, default_time_val=pre_w_val)
    routine_block(f"7. {workout_type} 実践", ["心拍数管理", "水分補給"], "evening_workout", w_time.strftime('%H:%M'), default_time_val=w_time)

st.markdown("### 🌙 Night & Recovery")
routine_block("8. 夕食後", ["ご飯 MAX 120g", "サプリ各種"], "dinner_after", default_time_val=time(19, 0))

bed_dt = datetime.combine(today_date, st.session_state['bed_time'])
bath_str = (bed_dt - timedelta(minutes=90)).strftime('%H:%M')
bath_val = (bed_dt - timedelta(minutes=90)).time()

routine_block("9. 究極回復セット", ["お風呂 15分", "回復サプリ各種"], "bedtime_routine", f"入浴目安: {bath_str}", default_time_val=bath_val)

st.markdown("---")