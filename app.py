import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, timezone
import gspread
import json

# ==========================================
# ⚙️ 設定エリア
# ==========================================
SERVICE_ACCOUNT_FILE = 'service_account.json' 
SPREADSHEET_NAME = 'Phase4_Log'

# ==========================================
# 🇯🇵 日本時間設定
# ==========================================
JST = timezone(timedelta(hours=+9), 'JST')

def get_now_jst():
    return datetime.now(JST)

def get_today_str():
    return get_now_jst().strftime('%Y-%m-%d')

# ==========================================
# 🚀 初期化処理
# ==========================================
st.set_page_config(page_title="Phase 4 Dashboard", page_icon="⚡️", layout="centered")

if 'init_done' not in st.session_state:
    st.session_state['init_done'] = False
    st.session_state['wake_up_time'] = time(7, 0)
    st.session_state['workout_time'] = time(18, 0)
    st.session_state['bed_time'] = time(23, 30)

# ==========================================
# 🛠 関数定義 (MacでもCloudでも動く最強版)
# ==========================================
@st.cache_resource
def get_worksheet():
    try:
        # 1. まずクラウド上の「Secrets」を探す
        if "gcp_json" in st.secrets:
            # クラウドの場合: SecretsからJSON文字列を読み込んで辞書にする
            creds_dict = json.loads(st.secrets["gcp_json"])
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            # 2. なければMac上の「ファイル」を探す
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

    is_done = st.session_state[done_key]

    if is_done:
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
            for item in items:
                st.text(f"• {item}")
            st.markdown("---")
            
            c1, c2 = st.columns([1, 1])
            with c1:
                current_picker_val = st.session_state.get(picker_key)
                if current_picker_val:
                    initial_value = current_picker_val
                elif default_time_val:
                    initial_value = default_time_val
                else:
                    initial_value = time(7, 0)
                input_time = st.time_input("実施時間", value=initial_value, key=picker_key)
            
            with c2:
                st.write("")
                st.write("")
                if st.button("✅ 完了", key=f"{key_prefix}_btn", type="primary", use_container_width=True):
                    st.session_state[done_key] = True
                    st.session_state[time_key] = input_time.strftime('%H:%M')
                    st.rerun()
        return input_time.strftime('%H:%M')

# ==========================================
# 📥 データ読み込み
# ==========================================
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
                try: st.session_state['workout_type'] = str(row['Workout'])
                except: pass
                
                progress = json.loads(str(row['Progress']))
                for key, val in progress.items():
                    st.session_state[f"{key}_done"] = True
                    st.session_state[f"{key}_time"] = val
                    try:
                        st.session_state[f"{key}_picker"] = datetime.strptime(val, '%H:%M').time()
                    except: pass
                st.toast("データ復元完了 (JST)", icon="🇯🇵")
    except: pass
    st.session_state['init_done'] = True

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🔥 Phase 4: Full Routine")
st.caption(f"{today_str} (JST)")

# --- 設定 ---
with st.expander("🛠 スケジュール設定", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        wake_up_time = st.time_input("👀 起床", value=st.session_state['wake_up_time'])
        st.session_state['wake_up_time'] = wake_up_time
    with c2:
        workout_opts = ["なし", "ウォーキング (5km)", "エアロバイク (45分)", "サウナ", "筋トレ"]
        current_workout = st.session_state.get('workout_type', "なし")
        idx = workout_opts.index(current_workout) if current_workout in workout_opts else 0
        workout_type = st.selectbox("🏃 運動メニュー", workout_opts, index=idx)
        st.session_state['workout_type'] = workout_type
    
    c3, c4 = st.columns(2)
    with c3:
        current_w_time = st.session_state.get('workout_time')
        workout_time_input = st.time_input("運動開始予定", value=current_w_time)
        st.session_state['workout_time'] = workout_time_input
    with c4:
        bed_time_input = st.time_input("🛏️ 就寝目標", value=st.session_state.get('bed_time'))
        st.session_state['bed_time'] = bed_time_input

# --- タイムライン ---
st.markdown("### 🌅 Morning")
today_date = get_now_jst().date()

ignition_time_str = routine_block("1. 爆速点火フェーズ", ["MCTオイル 7g", "カルニチン 2錠", "タケダVitC 3錠", "QPコーワα 1錠", "ビタミンD 1錠"], "morning_ignition", None, default_time_val=time(7, 15))

try:
    ig_dt = datetime.strptime(ignition_time_str, '%H:%M')
    ig_dt_full = datetime.combine(today_date, ig_dt.time())
    target_muscle_dt = ig_dt_full + timedelta(minutes=30)
    target_muscle_str = target_muscle_dt.strftime('%H:%M')
except:
    target_muscle_str = "--:--"
    target_muscle_dt = datetime.combine(today_date, time(7, 45))

routine_block("2. 筋肉起動 & 温冷浴", ["ヨガ・プランク2分・スクワット10", "温水3分 ➡ 冷水1分"], "morning_muscle", f"{target_muscle_str} Start", default_time_val=target_muscle_dt.time())
routine_block("3. 朝散歩 (光と風)", ["外気浴散歩 15-20分", "(行けない日はバイク20分)"], "morning_walk", None, default_time_val=time(8, 0))
routine_block("4. 朝食 & サプリ", ["ベースブレッド 1個", "エビオス 10錠", "ビオスリー 2錠", "Stress B 1錠", "ビオチン 2錠"], "morning_breakfast", None, default_time_val=time(8, 30))

st.markdown("### ☀️ Lunch")
routine_block("5. 昼食 (代謝維持)", ["ベースブレッド 1〜2個", "エビオス 10錠", "ビオスリー 2錠", "タケダVitC 2錠"], "lunch", None, default_time_val=time(12, 0))

is_workout_day = (workout_type != "なし")
workout_dt = datetime.combine(today_date, st.session_state['workout_time'])
target_carnitine_dt = workout_dt - timedelta(minutes=30)
target_carnitine_str = target_carnitine_dt.strftime('%H:%M')
target_workout_str = st.session_state['workout_time'].strftime('%H:%M')

if is_workout_day:
    st.markdown("### 🌆 Evening (Extra Burn)")
    routine_block(f"6. 運動前準備 ({workout_type})", ["カルニチン 2錠 (運動30分前)", "軽い運動・準備"], "evening_pre_workout", target_carnitine_str, default_time_val=target_carnitine_dt.time())
    routine_block(f"7. {workout_type} 実践", ["心拍数管理", "水分補給"], "evening_workout", target_workout_str, default_time_val=st.session_state['workout_time'])

st.markdown("### 🌙 Night & Recovery")
routine_block("8. 夕食後", ["ご飯 MAX 120g", "エビオス 10錠", "ビオスリー 2錠", "Stress B 1錠"], "dinner_after", None, default_time_val=time(19, 0))

bed_dt = datetime.combine(today_date, st.session_state['bed_time'])
target_bath_dt = bed_dt - timedelta(minutes=90)
target_bath_str = target_bath_dt.strftime('%H:%M')

bedtime_items = ["お風呂 40℃ 15分 (出てからゆったり)", "QPコーワヒーリング 2錠", "マグネシウム 2錠", "テアニン 1錠", "タケダVitC 2錠"]
if not is_workout_day:
    bedtime_items.append("💊 カルニチン 2錠 (夕方分スライド)")

routine_block("9. 究極回復セット (就寝90分前)", bedtime_items, "bedtime_routine", f"お風呂: {target_bath_str} 頃", default_time_val=target_bath_dt.time())

st.markdown("---")

# ==========================================
# 💾 保存ロジック (エラー回避修正版)
# ==========================================
if st.button("🔄 全データを同期 (Save to Drive)", type="primary", use_container_width=True):
    if not sheet:
        st.error("Sheet Error")
    else:
        with st.spinner("Saving..."):
            progress_dict = {}
            keys = ["morning_ignition", "morning_muscle", "morning_walk", "morning_breakfast", "lunch", "evening_pre_workout", "evening_workout", "dinner_after", "bedtime_routine"]
            for k in keys:
                if st.session_state.get(f"{k}_done", False):
                    progress_dict[k] = st.session_state.get(f"{k}_time", "")
            progress_json = json.dumps(progress_dict, ensure_ascii=False)
            row_data = [today_str, st.session_state['wake_up_time'].strftime('%H:%M:%S'), st.session_state['workout_type'], st.session_state.get('sleep_score', 0), st.session_state.get('body_feeling', ""), st.session_state['workout_time'].strftime('%H:%M:%S'), progress_json]
            
            try:
                dates = sheet.col_values(1)
                if today_str in dates:
                    row_index = dates.index(today_str) + 1
                    for i, val in enumerate(row_data):
                        sheet.update_cell(row_index, i+1, val)
                    st.success("✅ 保存完了！ (JST)")
                else:
                    sheet.append_row(row_data)
                    st.success("✅ 新規保存完了！ (JST)")
            except Exception as e:
                st.error(f"Error: {e}")