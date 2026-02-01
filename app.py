import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 系统配置与常量 / Configuration
# ==========================================
st.set_page_config(
    page_title="工厂报餐 / စက်ရုံထမင်းစားစာရင်း", 
    page_icon="🍚",
    layout="centered" # 手机端显示更友好
)

# --- 核心：泰国时间修正 (UTC+7) ---
THAILAND_OFFSET = timedelta(hours=7)
def get_thai_time():
    # 获取服务器时间并强制转换为泰国时间
    return datetime.utcnow() + THAILAND_OFFSET

# --- 核心：截止时间设置 ---
LUNCH_DEADLINE = time(9, 0)   # 早上 9:00
DINNER_DEADLINE = time(15, 0) # 下午 3:00

# --- 语言包 (中/缅) ---
TRANS = {
    "login_title": "请输入手机号 / ဖုန်းနံပါတ်ထည့်ပါ",
    "new_user_title": "第一次使用，请输入名字 / နာမည်ထည့်ပါ",
    "register_btn": "注册并登录 / စာရင်းသွင်းပြီး ဝင်ပါ",
    "welcome": "你好 / မင်္ဂလာပါ",
    "logout": "退出 / ထွက်ရန်",
    "bookmark_hint": "💡 提示：请将本页加入书签，下次自动登录！\nဒီစာမျက်နှာကို save ထားပါ၊ နောက်တစ်ခါ ဖုန်းနံပါတ်ရိုက်စရာမလိုပါ",
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
    "tab_overview": "概览 / အနှစ်ချုပ်",
    "tab_details": "详细名单 / အသေးစိတ်စာရင်း",
    "loading": "正在同步数据... / Data Syncing...",
    "refresh": "刷新数据 / Refresh"
}

# ==========================================
# 2. 数据库连接与操作 / Database Functions
# ==========================================

# 建立 Google Sheets 连接
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    """
    读取数据核心函数
    ttl=0 确保不缓存，每次都读最新数据
    """
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        
        # 1. 处理空表情况，防止报错
        if worksheet_name == "users" and df.empty:
            return pd.DataFrame(columns=["phone", "name", "reg_date"])
        if worksheet_name == "orders" and df.empty:
            return pd.DataFrame(columns=["date", "phone", "name", "meal_type", "action", "time"])
        
        # 2. 数据清洗：强制把手机号转为字符串，防止变成科学计数法
        if 'phone' in df.columns:
            # 先转字符串，再去掉可能存在的 .0 后缀
            df['phone'] = df['phone'].astype(str).str.replace(r'\.0$', '', regex=True)
            
        return df
    except Exception as e:
        # 如果连接失败（通常是 Secrets 没配好），给个友好提示
        st.error(f"数据库连接失败，请检查配置。Error: {e}")
        return pd.DataFrame()

def update_data(worksheet_name, df):
    """写入数据到 Google Sheets"""
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear() # 清除缓存

def get_user(phone):
    df = get_data("users")
    if df.empty: return None
    user = df[df['phone'] == str(phone)]
    return user.iloc[0] if not user.empty else None

def register_user(phone, name):
    df = get_data("users")
    # 检查是否已注册
    if not df.empty and str(phone) in df['phone'].values:
        return True
    
    new_user = pd.DataFrame([{
        "phone": str(phone), 
        "name": name, 
        "reg_date": get_thai_time().strftime("%Y-%m-%d")
    }])
    updated_df = pd.concat([df, new_user], ignore_index=True)
    update_data("users", updated_df)
    return True

def save_order(phone, name, meal_type, action):
    df = get_data("orders")
    date_str = get_thai_time().strftime("%Y-%m-%d")
    time_str = get_thai_time().strftime("%H:%M:%S")
    
    # 逻辑：先删除该用户今天同一餐的旧记录 (覆盖模式)
    if not df.empty:
        df = df[~((df['date'] == date_str) & (df['phone'] == str(phone)) & (df['meal_type'] == meal_type))]
    
    new_record = pd.DataFrame([{
        "date": date_str,
        "phone": str(phone),
        "name": name,
        "meal_type": meal_type,
        "action": action,
        "time": time_str
    }])
    
    updated_df = pd.concat([df, new_record], ignore_index=True)
    update_data("orders", updated_df)

def delete_order(phone, meal_type):
    """撤销操作：物理删除该条记录"""
    df = get_data("orders")
    if df.empty: return
    
    date_str = get_thai_time().strftime("%Y-%m-%d")
    updated_df = df[~((df['date'] == date_str) & (df['phone'] == str(phone)) & (df['meal_type'] == meal_type))]
    update_data("orders", updated_df)

def get_my_status(phone, meal_type):
    """查询我今天的状态"""
    df = get_data("orders")
    if df.empty: return None
    
    date_str = get_thai_time().strftime("%Y-%m-%d")
    # 筛选：今天 + 我的手机号 + 餐次
    record = df[(df['date'] == date_str) & (df['phone'] == str(phone)) & (df['meal_type'] == meal_type)]
    
    if not record.empty:
        return record.iloc[-1]['action']
    return None

# ==========================================
# 3. 页面主逻辑 / Main Interface
# ==========================================

# --- 自动登录逻辑 ---
query_params = st.query_params
url_phone = query_params.get("phone", None)

if 'phone' not in st.session_state:
    st.session_state.phone = url_phone
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# 如果有手机号但没名字（刚从URL进来），查一下名字
if st.session_state.phone and not st.session_state.user_name:
    user = get_user(st.session_state.phone)
    if user is not None:
        st.session_state.user_name = user['name']

# --- A. 登录/注册页 ---
if st.session_state.phone is None or st.session_state.user_name is None:
    st.title("🏭 工厂报餐 / စက်ရုံထမင်းစားစာရင်း")
    
    phone_input = st.text_input(TRANS["login_title"], placeholder="08xxxxxxxx")
    
    if st.button("下一步 / ရှေ့ဆက်ရန်", type="primary", use_container_width=True):
        if phone_input:
            with st.spinner(TRANS["loading"]):
                user = get_user(phone_input)
                if user is not None:
                    # 老用户：登录并更新 URL
                    st.session_state.phone = user['phone']
                    st.session_state.user_name = user['name']
                    st.query_params["phone"] = user['phone']
                    st.rerun()
                else:
                    # 新用户：跳转注册
                    st.session_state.temp_phone = phone_input
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
                    st.query_params["phone"] = st.session_state.temp_phone
                    st.rerun()

# --- B. 员工报餐页 ---
else:
    # 顶部信息栏
    st.caption(f"{TRANS['welcome']}, {st.session_state.user_name}")
    st.info(TRANS['bookmark_hint'])
    
    if st.button(TRANS['logout']):
        st.session_state.phone = None
        st.session_state.user_name = None
        st.query_params.clear()
        st.rerun()
        
    st.divider()

    # 获取当前泰国时间
    now_thai = get_thai_time()
    weekday = now_thai.weekday() # 0=周一, 6=周日
    current_time = now_thai.time()
    is_sunday = (weekday == 6)

    # 调试信息（上线后可注释掉，但留着方便看时间是否正确）
    # st.caption(f"🕒 Thai Time: {now_thai.strftime('%H:%M')}")

    # 显示周日或工作日规则
    st.subheader(TRANS["sun_header"] if is_sunday else TRANS["wd_header"])
    st.warning(TRANS["sun_rule"] if is_sunday else TRANS["wd_rule"])

    col1, col2 = st.columns(2)

    # --- 核心：卡片渲染逻辑 ---
    def render_meal_card(col, meal_label, meal_key, deadline):
        with col:
            st.write(f"### {meal_label}")
            
            # 获取状态
            status = get_my_status(st.session_state.phone, meal_key)
            is_expired = current_time > deadline
            
            # 判断显示状态 (周日 vs 平日)
            if is_sunday:
                final_status = "Eat" if status == "BOOKED" else "Not Eat"
            else:
                final_status = "Not Eat" if status == "CANCELED" else "Eat"

            # 显示结果图标
            if final_status == "Eat":
                st.success(TRANS["status_eat"])
            else:
                st.error(TRANS["status_not_eat"])

            # 显示按钮
            if not is_expired:
                if is_sunday:
                    # 周日：默认不吃。不吃显示“我要吃”，吃了显示“撤销”
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
                    # 平日：默认吃。吃显示“我不吃”，不吃显示“撤销”
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

    # 渲染两张卡片
    render_meal_card(col1, TRANS["lunch"], "Lunch", LUNCH_DEADLINE)
    render_meal_card(col2, TRANS["dinner"], "Dinner", DINNER_DEADLINE)

    # ==========================================
    # 4. 管理员看板 (全员状态)
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
            
            # 过滤今天的订单
            today_orders = pd.DataFrame()
            if not orders_df.empty:
                today_orders = orders_df[orders_df['date'] == today_str]

            # 1. 拿所有用户名单
            master_df = users_df[['name', 'phone']].copy()
            
            # 2. 准备关联数据
            lunch_data = pd.DataFrame()
            dinner_data = pd.DataFrame()
            
            if not today_orders.empty:
                lunch_data = today_orders[today_orders['meal_type'] == 'Lunch'][['phone', 'action']]
                dinner_data = today_orders[today_orders['meal_type'] == 'Dinner'][['phone', 'action']]
            
            # 3. 关联数据 (Left Join)
            # 确保 phone 都是字符串类型，防止匹配失败
            master_df['phone'] = master_df['phone'].astype(str)
            if not lunch_data.empty:
                lunch_data['phone'] = lunch_data['phone'].astype(str)
                master_df = master_df.merge(lunch_data, on='phone', how='left').rename(columns={'action': 'L_Stat'})
            else:
                master_df['L_Stat'] = None
                
            if not dinner_data.empty:
                dinner_data['phone'] = dinner_data['phone'].astype(str)
                master_df = master_df.merge(dinner_data, on='phone', how='left').rename(columns={'action': 'D_Stat'})
            else:
                master_df['D_Stat'] = None

            # 4. 计算最终状态 (核心算法)
            def calc_final_status(row, status_col):
                action = row.get(status_col)
                if pd.isna(action): action = None
                
                if is_sunday:
                    # 周日：有BOOKED记录才算吃
                    return "✅ 吃 (Eat)" if action == "BOOKED" else "❌ 不吃"
                else:
                    # 平日：有CANCELED记录才算不吃，否则都算吃
                    return "❌ 不吃 (Not Eat)" if action == "CANCELED" else "✅ 吃 (Default)"

            master_df['Lunch'] = master_df.apply(lambda r: calc_final_status(r, 'L_Stat'), axis=1)
            master_df['Dinner'] = master_df.apply(lambda r: calc_final_status(r, 'D_Stat'), axis=1)

            # 5. 统计数字
            total_users = len(master_df)
            lunch_count = len(master_df[master_df['Lunch'].str.contains("✅")])
            dinner_count = len(master_df[master_df['Dinner'].str.contains("✅")])

            st.metric("Total Users", total_users)
            c1, c2 = st.columns(2)
            c1.metric("Lunch Count", lunch_count)
            c2.metric("Dinner Count", dinner_count)
            
            st.write("📋 详细名单：")
            st.dataframe(master_df[['name', 'phone', 'Lunch', 'Dinner']], use_container_width=True)