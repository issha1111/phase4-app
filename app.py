import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, timezone
import gspread
import json

# ==========================================
# 🚀 1. ページ設定 & デザイン
# ==========================================
st.set_page_config(page_title="Phase 4 Dashboard v2.7", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    div.stButton > button {
        width: 100%; background-color: #007AFF; color: white;
        font-weight: bold; border-radius: 10px; padding: 0.5rem 1rem; border: none;
    }
    div.stButton > button:hover { background-color: #0056b3; color: white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 設定エリア
# ==========================================
SPREADSHEET_NAME = 'Phase4_Log' 
WORKSHEET_NAME = 'v2'          
MEAL_WORKSHEET_NAME = 'mealrecord' 
JST = timezone(timedelta(hours=+9), 'JST')

AUTO_SUPPLEMENTS = """MCTオイル 7g
• カルニチン 4錠
• タケダVitC 9錠
• QPコーワα 1錠
• ビタミンD 1錠
• エビオス 30錠
• ビオスリー 6錠
• thoren Stress B complex 2錠
• ビオチン 2錠
• QPコーワヒーリング2錠
• マグネシウム2錠
• テアニン1錠"""

def get_now_jst(): return datetime.now(JST)
def get_today_str(): return get_now_jst().strftime('%Y-%m-%d')

# ==========================================
# 🛠 接続 & 同期関数
# ==========================================
@st.cache_resource
def get_gc():
    try:
        if "gcp_json" not in st.secrets:
            st.error("Secretsに 'gcp_json' が見つかりません。")
            return None
        raw_json = st.secrets["gcp_json"].strip().replace('\\', '\\\\').replace('\\\\n', '\\n')
        creds_dict = json.loads(raw_json, strict=False)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
        return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        st.error(f"GCP Connection Error: {e}"); return None

def get_worksheet(name):
    gc = get_gc()
    if gc:
        try: return gc.open(SPREADSHEET_NAME).worksheet(name)
        except Exception as e: st.error(f"Worksheet Error ({name}): {e}"); return None
    return None

def sync_meal_data():
    sheet = get_worksheet(MEAL_WORKSHEET_NAME)
    if not sheet: return

    with st.spinner("Saving Meal Record..."):
        today_str = get_today_str()
        
        # 書き込むデータ（A列〜E列の5つ）
        meal_row = [
            today_str,
            st.session_state.get('meal_breakfast', ""),
            st.session_state.get('meal_lunch', ""),
            st.session_state.get('meal_dinner', ""),
            AUTO_SUPPLEMENTS
        ]

        try:
            # 1. A列（日付）を全部読み込む
            dates = sheet.col_values(1) 
            
            if today_str in dates:
                # 【上書きモード】既に今日の日付がある場合
                idx = dates.index(today_str) + 1
                # 範囲指定で強制書き込み (A〜E列)
                sheet.update(range_name=f'A{idx}:E{idx}', values=[meal_row])
                st.success(f"✅ mealrecord 更新完了 ({today_str})")
            else:
                # 【新規モード】今日の日付がない場合
                # append_row は使わず、行番号を計算して強制書き込み
                # これで右側に何があってもズレずにA列から書けます
                next_row = len(dates) + 1
                sheet.update(range_name=f'A{next_row}:E{next_row}', values=[meal_row])
                st.success(f"✅ mealrecord 新規保存完了 ({today_str})")

        except Exception as e:
            st.error(f"Meal Sync Error: {e}")

def sync_button(key):
    if st.button("🔄 全データを同期 (Save to Drive)", type="primary", use_container_width=True, key=key):
        sheet = get_worksheet(WORKSHEET_NAME)
        if not sheet: st.error("シートに接続できません。")
        else:
            with st.spinner("Saving..."):
                progress_dict = {}
                keys = ["morning_ignition", "morning_muscle", "morning_walk", "morning_breakfast", "lunch", "evening_pre_workout", "evening_workout", "dinner_after", "bedtime_routine"]
                for k in keys:
                    if st.session_state.get(f"{k}_done", False): progress_dict[k] = st.session_state.get(f"{k}_time", "")
                    elif st.session_state.get(f"{k}_skipped", False): progress_dict[k] = "SKIPPED"
                
                today_str = get_today_str()
                row_data = [
                    today_str, 
                    st.session_state['wake_up_time'].strftime('%H:%M:%S'), 
                    st.session_state['workout_type'], 
                    0, "", 
                    st.session_state['workout_time'].strftime('%H:%M:%S'), 
                    st.session_state['bed_time'].strftime('%H:%M:%S'),
                    json.dumps(progress_dict, ensure_ascii=False),
                    st.session_state['diary_text']
                ]
                try:
                    dates = sheet.col_values(1)
                    if today_str in dates:
                        idx = dates.index(today_str) + 1
                        for i, val in enumerate(row_data): sheet.update_cell(idx, i+1, val)
                        st.success("✅ 同期完了")
                    else:
                        sheet.append_row(row_data)
                        st.success("✅ 新規保存完了")
                except Exception as e: st.error(f"Error: {e}")

def routine_block(title, items, key_prefix, target_time_str=None, default_time_val=None, can_skip=False):
    done_key, time_key, skipped_key, picker_key = f"{key_prefix}_done", f"{key_prefix}_time", f"{key_prefix}_skipped", f"{key_prefix}_picker"
    if done_key not in st.session_state: st.session_state[done_key] = False
    if skipped_key not in st.session_state: st.session_state[skipped_key] = False

    if st.session_state[done_key]:
        with st.container(border=False):
            st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; color: gray;"><h4 style="margin:0; text-decoration: line-through;">{title.split("<")[0].strip()}</h4><small>✅ Completed at {st.session_state[time_key]}</small></div>', unsafe_allow_html=True)
            if st.button("↺ 修正", key=f"{key_prefix}_undo"):
                st.session_state[done_key] = False; st.rerun()
        return st.session_state.get(time_key, "07:00")
    elif st.session_state[skipped_key]:
        with st.container(border=False):
            st.markdown(f'<div style="background-color: #e0e0e0; padding: 10px; border-radius: 10px; color: #9e9e9e;"><h4 style="margin:0;">{title.split("<")[0].strip()}</h4><small>⚠️ Skipped (Rest Day)</small></div>', unsafe_allow_html=True)
            if st.button("↺ 修正して実行", key=f"{key_prefix}_unskip"):
                st.session_state[skipped_key] = False; st.rerun()
        return "SKIPPED"
    else:
        with st.container(border=True):
            display_title = title if not target_time_str else f"{title} <span style='color:#FF4B4B; font-size:0.85em;'>({target_time_str})</span>"
            st.markdown(f"### {display_title}", unsafe_allow_html=True)
            for item in items: st.text(f"• {item}")
            st.markdown("---")
            cols = st.columns([1, 1, 1]) if can_skip else st.columns([1, 1])
            with cols[0]:
                input_time = st.time_input("実施時間", value=st.session_state.get(picker_key, default_time_val or time(7, 0)), key=picker_key)
            with cols[1]:
                st.write(""); st.write("")
                if st.button("✅ 完了", key=f"{key_prefix}_btn", type="primary", use_container_width=True):
                    st.session_state[done_key], st.session_state[time_key] = True, input_time.strftime('%H:%M'); st.rerun()
            if can_skip:
                with cols[2]:
                    st.write(""); st.write("")
                    if st.button("❌ やらない", key=f"{key_prefix}_skip", use_container_width=True):
                        st.session_state[skipped_key] = True
                        if key_prefix == "evening_workout": st.session_state["evening_pre_workout_skipped"] = True
                        st.rerun()
        return st.session_state.get(time_key, "07:00")

# ==========================================
# 📥 データ読み込み & 初期化 (リロード復旧)
# ==========================================
today_str = get_today_str()

if 'init_done' not in st.session_state:
    st.session_state['init_done'] = False
    st.session_state['wake_up_time'] = time(7, 0)
    st.session_state['workout_type'] = "なし"
    st.session_state['workout_time'] = time(18, 0)
    st.session_state['bed_time'] = time(23, 30)
    st.session_state['diary_text'] = ""
    st.session_state['meal_breakfast'] = ""
    st.session_state['meal_lunch'] = ""
    st.session_state['meal_dinner'] = ""

if not st.session_state['init_done']:
    # 1. ルーティーン読込
    sheet = get_worksheet(WORKSHEET_NAME)
    if sheet:
        try:
            raw_routine = sheet.get_all_values()
            if len(raw_routine) > 1:
                headers = [h if (h and h.strip()) else f"COL_{i}" for i, h in enumerate(raw_routine[0])]
                df = pd.DataFrame(raw_routine[1:], columns=headers)
                if 'Date' in df.columns:
                    today_data = df[df['Date'] == today_str]
                    if not today_data.empty:
                        row = today_data.iloc[0]
                        st.session_state['wake_up_time'] = datetime.strptime(str(row['WakeTime']), '%H:%M:%S').time()
                        st.session_state['workout_type'] = str(row['Workout'])
                        st.session_state['workout_time'] = datetime.strptime(str(row['WorkoutTime']), '%H:%M:%S').time()
                        st.session_state['bed_time'] = datetime.strptime(str(row['BedTime']), '%H:%M:%S').time()
                        st.session_state['diary_text'] = str(row.get('Diary', ""))
                        progress = json.loads(str(row['Progress']))
                        for key, val in progress.items():
                            if val == "SKIPPED": st.session_state[f"{key}_skipped"] = True
                            else: st.session_state[f"{key}_done"], st.session_state[f"{key}_time"] = True, val
        except: pass
    
    # 2. 食事記録読込
    m_sheet = get_worksheet(MEAL_WORKSHEET_NAME)
    if m_sheet:
        try:
            raw_m = m_sheet.get_all_values()
            if len(raw_m) > 1:
                headers_m = [h if (h and h.strip()) else f"COL_{i}" for i, h in enumerate(raw_m[0])]
                m_df = pd.DataFrame(raw_m[1:], columns=headers_m)
                if 'DATE' in m_df.columns:
                    target_row = m_df[m_df['DATE'].astype(str) == today_str]
                    if not target_row.empty:
                        m_row = target_row.iloc[0]
                        st.session_state['meal_breakfast'] = str(m_row.get('BREAKFAST', ""))
                        st.session_state['meal_lunch'] = str(m_row.get('LUNCH', ""))
                        st.session_state['meal_dinner'] = str(m_row.get('DINNER', ""))
                        st.toast(f"✅ {today_str} の食事を復元しました")
        except: pass
    st.session_state['init_done'] = True

# ==========================================
# 🖥 メインUI
# ==========================================
st.title("🔥 Phase 4 Dashboard v2.7")
st.caption(f"{today_str} (JST)")

sync_button("top_sync")

# --- スケジュール設定（閉じた状態で開始） ---
with st.expander("🛠 スケジュール設定", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.session_state['wake_up_time'] = st.time_input("👀 起床", value=st.session_state['wake_up_time'])
        st.session_state['workout_time'] = st.time_input("運動開始予定", value=st.session_state['workout_time'])
    with c2:
        base_options = ["ウォーキング", "エアロバイク", "サウナ", "筋トレ", "なし"]
        current_w = st.session_state['workout_type']
        default_idx = next((i for i, opt in enumerate(base_options) if opt in current_w), 4)
        menu_type = st.selectbox("🏃 運動種目", base_options, index=default_idx)
        if menu_type == "ウォーキング": val = st.number_input("距離 (km)", value=5.0, step=0.1); final_w = f"ウォーキング ({val}km)"
        elif menu_type == "エアロバイク": val = st.number_input("時間 (分)", value=45, step=5); final_w = f"エアロバイク ({val}分)"
        elif menu_type == "サウナ": val = st.number_input("セット数", value=3, step=1); final_w = f"サウナ ({val}セット)"
        elif menu_type == "筋トレ": val = st.text_input("内容", value="30分"); final_w = f"筋トレ ({val})"
        else: final_w = "なし"
        st.session_state['workout_type'] = final_w
        st.session_state['bed_time'] = st.time_input("🛏️ 就寝目標", value=st.session_state['bed_time'])

# --- 🍴 食事記録（閉じた状態で開始） ---
with st.expander("🍴 食事記録 (mealrecord)", expanded=False):
    st.caption("サプリメントは同期時に自動付与されます")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.text_area("🍳 BREAKFAST", key="meal_breakfast", height=120)
    with m_col2: st.text_area("🍱 LUNCH", key="meal_lunch", height=120)
    with m_col3: st.text_area("🥩 DINNER", key="meal_dinner", height=120)
    if st.button("🔄 食事記録を同期", use_container_width=True): sync_meal_data()

# --- タイムライン ---
st.markdown("### 🌅 Morning")
today_date = get_now_jst().date()
ign_time = routine_block("1. 爆速点火フェーズ", ["MCTオイル 7g", "マグネシウム 2錠", "クルクミン 2錠", "カルニチン 2錠", "タケダVitC 3錠", "QPコーワα 1錠", "ビタミンD 1錠"], "morning_ignition", default_time_val=time(7, 15))

try:
    ig_dt = datetime.combine(today_date, datetime.strptime(ign_time, '%H:%M').time())
    target_m_str = (ig_dt + timedelta(minutes=30)).strftime('%H:%M'); target_m_val = (ig_dt + timedelta(minutes=30)).time()
except:
    target_m_str = "--:--"; target_m_val = time(7, 45)

routine_block("2. 筋肉起動 & 温冷浴", ["ヨガ・プランク2分・スクワット10", "温水3分 ➡ 冷水1分"], "morning_muscle", f"{target_m_str} Start", default_time_val=target_m_val)
routine_block("3. 朝散歩", ["外気浴 15-20分"], "morning_walk", default_time_val=time(8, 0))
routine_block("4. 朝食 & サプリ", ["ベースブレッド 1個", "エビオス 10錠", "ビオスリー 2錠", "Stress B 1錠", "ビオチン 2錠"], "morning_breakfast", default_time_val=time(8, 30))

st.markdown("### ☀️ Lunch")
routine_block("5. 昼食 (代謝維持)", ["ベースブレッド", "エビオス 10錠", "ビオスリー 2錠", "タケダVitC 2錠"], "lunch", default_time_val=time(12, 0))

workout_type = st.session_state['workout_type']
if "なし" not in workout_type:
    st.markdown("### 🌆 Evening (Extra Burn)")
    w_time = st.session_state['workout_time']
    pre_w_val = (datetime.combine(today_date, w_time) - timedelta(minutes=30)).time()
    routine_block(f"6. 運動前準備 ({workout_type})", ["カルニチン 2錠 (30分前)"], "evening_pre_workout", pre_w_val.strftime('%H:%M'), default_time_val=pre_w_val)
    routine_block(f"7. ガチ運動 ({workout_type})", ["心拍数管理", "水分補給"], "evening_workout", w_time.strftime('%H:%M'), default_time_val=w_time, can_skip=True)

st.markdown("### 🌙 Night & Recovery")
routine_block("8. 夕食後", ["ご飯 MAX 120g", "エビオス 10錠", "ビオスリー 2錠", "Stress B 1錠"], "dinner_after", default_time_val=time(19, 0))

bed_dt = datetime.combine(today_date, st.session_state['bed_time'])
bath_val = (bed_dt - timedelta(minutes=90)).time()
supple_val = (bed_dt - timedelta(minutes=50)).time()
target_label = f"入浴目安: {bath_val.strftime('%H:%M')} / 摂取目標: {supple_val.strftime('%H:%M')}"

bed_items = ["お風呂 15分 (40℃)", "QPコーワヒーリング 2錠", "亜鉛 1錠", "マグネシウム 2錠", "(運動した日はクルクミン 2錠)", "テアニン 1錠", "タケダVitC 2錠"]
if "なし" in workout_type or st.session_state.get("evening_workout_skipped", False):
    bed_items.append("💊 カルニチン 2錠 (夕方分スライド)")
routine_block("9. 究極回復セット", bed_items, "bedtime_routine", target_label, default_time_val=bath_val)

st.markdown("### 📝 Diary")
st.session_state['diary_text'] = st.text_area("今日の振り返り・メモ", value=st.session_state.get('diary_text', ""), height=150)
st.markdown("---")
sync_button("bottom_sync")