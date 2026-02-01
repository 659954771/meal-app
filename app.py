import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 系统配置 / Configuration
# ==========================================
st.set_page_config(
    page_title="工厂报餐 / စက်ရုံထမင်းစားစာရင်း", 
    page_icon="🍚",
    layout="centered"
)

# 泰国时间修正 (UTC+7)
THAILAND_OFFSET = timedelta(hours=7)
def get_thai_time():
    return datetime.utcnow() + THAILAND_OFFSET

# 截止时间
LUNCH_DEADLINE = time(9, 0)
DINNER_DEADLINE = time(15, 0)

# 语言包
TRANS = {
    "login_title": "请输入手机号 / ဖုန်းနံပါတ်ထည့်ပါ",
    "new_user_title": "第一次使用，请输入名字 / နာမည်ထည့်ပါ",
    "register_btn": "注册并登录 / စာရင်းသွင်းပြီး ဝင်ပါ",
    "welcome": "你好 / မင်္ဂလာပါ",
    "logout": "退出 (切换账号) / ထွက်ရန်",
    "bookmark_hint": "👇 **保存下方链接，下次直接点开不用登录！**\nအောက်ပါလင့်ခ်ကို သိမ်းဆည်းပါ။ နောက်တစ်ကြိမ် ဖုန်းနံပါတ်ရိုက်စရာမလိုပါ",
    "sun_header": "📅 周日 (Sunday) / တနင်္ဂနွေနေ့",
    "sun_rule": "⚠️ 规则：要吃请点【我要吃】 / စားလိုလျှင် 'စားမည်' ကိုနှိပ်ပါ",
    "wd_header": "📅 工作日 (Weekday) / အလုပ်ဖွင့်ရက်",
    "wd_rule": "⚠️ 规则：默认吃饭。不吃请点【我不吃】 / ပုံမှန်စားရမည်။ မစားလိုပါက 'မစားပါ' ကိုနှိပ်ပါ",
    "lunch": "午餐 / နေ့လည်စာ",
    "dinner": "晚餐 / ညစာ",
    "eat_btn": "我要吃 / စားမယ် (Eat)",
    "not_eat_btn": "我不吃 / မစားဘူး (Not Eat)",
    "undo_btn": "撤销 (重置) / ပြန်ပြင်မယ် (Undo)",
    "status_eat": "✅ 状态：吃饭 / စားမယ်",
    "status_not_eat": "❌ 状态：不吃 / မစားပါ",
    "deadline_pass": "🚫 已截止 / အချိန်ကုန်သွားပြီ",
    "admin_title": "👩‍💻 管理员看板 / Admin Dashboard",
    "loading": "处理中... / Processing...",
    "refresh": "刷新数据 / Refresh"
}

# ==========================================
# 2. 数据库核心函数 (防重复/强力清洗)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_phone(phone_input):
    """强力清洗手机号：转字符串、去空格、去.0"""
    if pd.isna(phone_input): return ""
    s = str(phone_input).strip()
    if s.endswith(".0"): s = s[:-2]
    return s

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if worksheet_name == "users" and df.empty:
            return pd.DataFrame(columns=["phone", "name", "reg_date"])
        if worksheet_name == "orders" and df.empty:
            return pd.DataFrame(columns=["date", "phone", "name", "meal_type", "action", "time"])
        if 'phone' in df.columns:
            df['phone'] = df['phone'].apply(clean_phone)
        return df
    except Exception as e:
        st.error(f"连接错误: {e}")
        return pd.DataFrame()

def update_data(worksheet_name, df):
    if 'phone' in df.columns:
        df['phone'] = df['phone'].astype(str)
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

def get_user(phone):
    df = get_data("users")
    if df.empty: return None
    target_phone = clean_phone(phone)
    user = df[df['phone'] == target_phone]
    if not user.empty: return user.iloc[0]
    return None

def register_user(phone, name):
    df = get_data("users")
    target_phone = clean_phone(phone)
    if not df.empty and target_phone in df['phone'].values:
        return True
    new_user = pd.DataFrame([{
        "phone": target_phone, 
        "name": name, 
        "reg_date": get_thai_time().strftime("%Y-%m-%d")
    }])
    updated_df = pd.concat([df, new_user], ignore_index=True)
    update_data("users", updated_df)
    return True

def save_order(phone, name, meal_type, action):
    df = get_data("orders")
    target_phone = clean_phone(phone)
    date_str = get_thai_time().strftime("%Y-%m-%d")
    time_str = get_thai_time().strftime("%H:%M:%S")
    if not df.empty:
        df = df[~((df['date'] == date_str) & (df['phone'] == target_phone) & (df['meal_type'] == meal_type))]
    new_record = pd.DataFrame([{
        "date": date_str, "phone": target_phone, "name": name,
        "meal_type": meal_type, "action": action, "time": time_str
    }])
    updated_df = pd.concat([df, new_record], ignore_index=True)
    update_data("orders", updated_df)

def delete_order(phone, meal_type):
    df = get_data("orders")
    target_phone = clean_phone(phone)
    if df.empty: return
    date_str = get_thai_time().strftime("%Y-%m-%d")
    updated_df = df[~((df['date'] == date_str) & (df['phone'] == target_phone) & (df['meal_type'] == meal_type))]
    update_data("orders", updated_df)

def get_my_status(phone, meal_type):
    df = get_data("orders")
    target_phone = clean_phone(phone)
    if df.empty: return None
    date_str = get_thai_time().strftime("%Y-%m-%d")
    record = df[(df['date'] == date_str) & (df['phone'] == target_phone) & (df['meal_type'] == meal_type)]
    if not record.empty: return record.iloc[-1]['action']
    return None

# ==========================================
# 3. 页面主逻辑 (优化自动登录)
# ==========================================

# 1. 获取 URL 里的手机号
query_params = st.query_params
url_phone = query_params.get("phone", None)

# 2. 初始化 Session
if 'phone' not in st.session_state:
    if url_phone:
        # 如果 URL 里有，直接尝试用它
        st.session_state.phone = clean_phone(url_phone)
    else:
        st.session_state.phone = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# 3. 自动补全名字 (如果 Session 有电话但没名字)
if st.session_state.phone and not st.session_state.user_name:
    user = get_user(st.session_state.phone)
    if user is not None:
        st.session_state.user_name = user['name']
        # 强制更新 URL (防止用户打开的是旧链接，强制把 phone 写回地址栏)
        st.query_params["phone"] = st.session_state.phone
    else:
        # 如果数据库查不到这个人（可能 URL 是错的），重置状态
        st.session_state.phone = None

# --- A. 登录/注册 ---
if st.session_state.phone is None or st.session_state.user_name is None:
    st.title("🏭 工厂报餐 / စက်ရုံထမင်းစားစာရင်း")
    
    phone_input = st.text_input(TRANS["login_title"], placeholder="08xxxxxxxx")
    
    if st.button("下一步 / ရှေ့ဆက်ရန်", type="primary", use_container_width=True):
        if phone_input:
            clean_input = clean_phone(phone_input)
            with st.spinner(TRANS["loading"]):
                user = get_user(clean_input)
                if user is not None:
                    st.session_state.phone = user['phone']
                    st.session_state.user_name = user['name']
                    # 登录成功，写入 URL
                    st.query_params["phone"] = user['phone']
                    st.rerun()
                else:
                    st.session_state.temp_phone = clean_input
                    st.rerun()
    
    if 'temp_phone' in st.session_state:
        st.info(TRANS["new_user_title"])
        name_input = st.text_input("Name / နာမည်")
        if st.button(TRANS["register_btn"], type="primary", use_container_width=True):
            if name_input:
                with st.spinner(TRANS["loading"]):
                    register_user(st.session_state.temp_phone, name_input)
                    st.session_state.phone = st.session_state.temp_phone
                    st.session_state.user_name = name_input
                    # 注册成功，写入 URL
                    st.query_params["phone"] = st.session_state.temp_phone
                    st.rerun()

# --- B. 报餐界面 ---
else:
    # 顶部：醒目的自动登录提示
    st.success(TRANS['bookmark_hint'])
    
    # 顶部导航
    st.caption(f"👤 {st.session_state.user_name} ({st.session_state.phone})")
    
    if st.button(TRANS['logout']):
        st.session_state.phone = None
        st.session_state.user_name = None
        st.query_params.clear() # 登出时清除 URL
        st.rerun()
        
    st.divider()

    now_thai = get_thai_time()
    weekday = now_thai.weekday() # 0=周一, 6=周日
    current_time = now_thai.time()
    is_sunday = (weekday == 6)

    st.subheader(TRANS["sun_header"] if is_sunday else TRANS["wd_header"])
    st.warning(TRANS["sun_rule"] if is_sunday else TRANS["wd_rule"])

    col1, col2 = st.columns(2)

    def render_meal_card(col, meal_label, meal_key, deadline):
        with col:
            st.write(f"### {meal_label}")
            status = get_my_status(st.session_state.phone, meal_key)
            is_expired = current_time > deadline
            
            final_status = "Eat"
            if is_sunday:
                final_status = "Eat" if status == "BOOKED" else "Not Eat"
            else:
                final_status = "Not Eat" if status == "CANCELED" else "Eat"

            if final_status == "Eat":
                st.success(TRANS["status_eat"])
            else:
                st.error(TRANS["status_not_eat"])

            if not is_expired:
                if is_sunday:
                    if final_status == "Not Eat":
                        if st.button(f"{TRANS['eat_btn']} 🍛", key=f"sun_eat_{meal_key}", type="primary", use_container_width=True):
                            with st.spinner(TRANS["loading"]):
                                save_order(st.session_state.phone, st.session_state.user_name, meal_key, "BOOKED")
                                st.rerun()
                    else:
                        if st.button(TRANS['undo_btn'], key=f"sun_undo_{meal_key}", use_container_width=True):
                            with st.spinner(TRANS["loading"]):
                                delete_order(st.session_state.phone, meal_key)
                                st.rerun()
                else:
                    if final_status == "Eat":
                        if st.button(f"{TRANS['not_eat_btn']} 🙅‍♂️", key=f"wd_not_{meal_key}", type="primary", use_container_width=True):
                            with st.spinner(TRANS["loading"]):
                                save_order(st.session_state.phone, st.session_state.user_name, meal_key, "CANCELED")
                                st.rerun()
                    else:
                        if st.button(TRANS['undo_btn'], key=f"wd_undo_{meal_key}", use_container_width=True):
                            with st.spinner(TRANS["loading"]):
                                delete_order(st.session_state.phone, meal_key)
                                st.rerun()
            else:
                st.caption(f"{TRANS['deadline_pass']} ({deadline.strftime('%H:%M')})")

    render_meal_card(col1, TRANS["lunch"], "Lunch", LUNCH_DEADLINE)
    render_meal_card(col2, TRANS["dinner"], "Dinner", DINNER_DEADLINE)

    # ==========================================
    # 4. 管理员看板
    # ==========================================
    st.divider()
    with st.expander(TRANS["admin_title"]):
        if st.button(TRANS["refresh"]):
            st.cache_data.clear()
            st.rerun()
            
        users_df = get_data("users")
        orders_df = get_data("orders")
        
        if not users_df.empty:
            today_str = now_thai.strftime("%Y-%m-%d")
            today_orders = pd.DataFrame()
            if not orders_df.empty:
                today_orders = orders_df[orders_df['date'] == today_str]

            master_df = users_df[['name', 'phone']].copy()
            master_df['phone'] = master_df['phone'].apply(clean_phone)
            
            lunch_data = pd.DataFrame()
            dinner_data = pd.DataFrame()
            if not today_orders.empty:
                today_orders['phone'] = today_orders['phone'].apply(clean_phone)
                lunch_data = today_orders[today_orders['meal_type'] == 'Lunch'][['phone', 'action']]
                dinner_data = today_orders[today_orders['meal_type'] == 'Dinner'][['phone', 'action']]
            
            master_df = master_df.merge(lunch_data, on='phone', how='left').rename(columns={'action': 'L_Stat'})
            master_df = master_df.merge(dinner_data, on='phone', how='left').rename(columns={'action': 'D_Stat'})
            master_df = master_df.drop_duplicates(subset=['phone'])

            def calc_final_status(row, status_col):
                action = row.get(status_col)
                if pd.isna(action): action = None
                if is_sunday:
                    return "✅ 吃" if action == "BOOKED" else "❌ 不吃"
                else:
                    return "❌ 不吃" if action == "CANCELED" else "✅ 吃"

            master_df['Lunch'] = master_df.apply(lambda r: calc_final_status(r, 'L_Stat'), axis=1)
            master_df['Dinner'] = master_df.apply(lambda r: calc_final_status(r, 'D_Stat'), axis=1)

            total = len(master_df)
            l_cnt = len(master_df[master_df['Lunch'].str.contains("✅")])
            d_cnt = len(master_df[master_df['Dinner'].str.contains("✅")])

            st.metric("Total", total)
            c1, c2 = st.columns(2)
            c1.metric("Lunch", l_cnt)
            c2.metric("Dinner", d_cnt)
            st.dataframe(master_df[['name', 'phone', 'Lunch', 'Dinner']], use_container_width=True)
