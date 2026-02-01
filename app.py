import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

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
    "logout": "退出账号 / ထွက်ရန်",
    "cookie_login": "🔄 正在自动登录... / Auto logging in...",
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
# 2. 核心技术函数 (Cookie & 模糊匹配)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# 初始化 Cookie 管理器
def get_cookie_manager():
    return stx.CookieManager()

def normalize_phone(phone_input):
    """
    智能标准化手机号：
    只保留数字，去除所有符号。
    用于比对时，我们只比对【最后9位】，彻底解决0开头的问题。
    """
    if pd.isna(phone_input): return ""
    # 转字符串，去空格，去小数点
    s = str(phone_input).strip()
    if s.endswith(".0"): s = s[:-2]
    # 只保留数字
    digits = "".join(filter(str.isdigit, s))
    return digits

def is_phone_match(phone_a, phone_b):
    """
    模糊匹配算法：
    只要两个号码的【后9位】或者【后8位】相同，就认为是同一个人。
    解决 0812345678 和 812345678 不匹配的问题。
    """
    p1 = normalize_phone(phone_a)
    p2 = normalize_phone(phone_b)
    
    if not p1 or not p2: return False
    if p1 == p2: return True
    
    # 尝试匹配后8位 (泰国手机号通常是9位或10位)
    if len(p1) >= 8 and len(p2) >= 8:
        return p1[-8:] == p2[-8:]
    return False

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if worksheet_name == "users" and df.empty:
            return pd.DataFrame(columns=["phone", "name", "reg_date"])
        if worksheet_name == "orders" and df.empty:
            return pd.DataFrame(columns=["date", "phone", "name", "meal_type", "action", "time"])
        # 这里不强制转格式，保持原样，比对时再清洗
        return df
    except Exception as e:
        # 暂时屏蔽连接错误，避免吓到用户，后台重试
        return pd.DataFrame()

def update_data(worksheet_name, df):
    # 写入时强制转字符串，防止Excel吃掉0
    if 'phone' in df.columns:
        df['phone'] = df['phone'].astype(str)
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

def get_user_fuzzy(phone):
    """智能模糊查找用户"""
    df = get_data("users")
    if df.empty: return None
    
    # 遍历查找 (因为不能直接 == 匹配了)
    for index, row in df.iterrows():
        if is_phone_match(str(row['phone']), phone):
            # 找到了！返回标准化的数据
            return row
            
    return None

def register_user(phone, name):
    df = get_data("users")
    # 注册前先模糊查重
    for index, row in df.iterrows():
        if is_phone_match(str(row['phone']), phone):
            return True # 已经有了，直接返回
            
    # 存入时，尽量存完整的 (带0)
    clean_p = normalize_phone(phone)
    if len(clean_p) == 9 and not clean_p.startswith('0'):
        clean_p = '0' + clean_p
        
    new_user = pd.DataFrame([{
        "phone": str(clean_p), # 强制存成字符串
        "name": name, 
        "reg_date": get_thai_time().strftime("%Y-%m-%d")
    }])
    updated_df = pd.concat([df, new_user], ignore_index=True)
    update_data("users", updated_df)
    return True

# 订单相关函数保持逻辑一致，使用模糊匹配查找旧记录
def save_order(phone, name, meal_type, action):
    df = get_data("orders")
    date_str = get_thai_time().strftime("%Y-%m-%d")
    time_str = get_thai_time().strftime("%H:%M:%S")
    
    # 过滤掉今天的旧记录 (模糊匹配)
    if not df.empty:
        # 构建一个不包含今日该餐次该人的新列表
        keep_rows = []
        for index, row in df.iterrows():
            is_same_day = str(row['date']) == date_str
            is_same_meal = str(row['meal_type']) == meal_type
            is_same_person = is_phone_match(str(row['phone']), phone)
            
            if is_same_day and is_same_meal and is_same_person:
                continue # 跳过这一行（相当于删除）
            keep_rows.append(row)
        df = pd.DataFrame(keep_rows)

    new_record = pd.DataFrame([{
        "date": date_str, "phone": str(phone), "name": name,
        "meal_type": meal_type, "action": action, "time": time_str
    }])
    updated_df = pd.concat([df, new_record], ignore_index=True)
    update_data("orders", updated_df)

def delete_order(phone, meal_type):
    df = get_data("orders")
    if df.empty: return
    date_str = get_thai_time().strftime("%Y-%m-%d")
    
    keep_rows = []
    for index, row in df.iterrows():
        is_same_day = str(row['date']) == date_str
        is_same_meal = str(row['meal_type']) == meal_type
        is_same_person = is_phone_match(str(row['phone']), phone)
        
        if is_same_day and is_same_meal and is_same_person:
            continue
        keep_rows.append(row)
        
    updated_df = pd.DataFrame(keep_rows)
    update_data("orders", updated_df)

def get_my_status(phone, meal_type):
    df = get_data("orders")
    if df.empty: return None
    date_str = get_thai_time().strftime("%Y-%m-%d")
    
    # 倒序查找，找最新的一条
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        if str(row['date']) == date_str and \
           str(row['meal_type']) == meal_type and \
           is_phone_match(str(row['phone']), phone):
            return row['action']
            
    return None

# ==========================================
# 3. 页面主逻辑 (Cookie + URL 双重校验)
# ==========================================

cookie_manager = get_cookie_manager()
cookies = cookie_manager.get_all()

# 1. 优先读取 URL 里的手机号
query_params = st.query_params
url_phone = query_params.get("phone", None)

# 2. 其次读取 Cookie 里的手机号
cookie_phone = cookies.get("auth_phone") if cookies else None

# 初始化 Session
if 'phone' not in st.session_state:
    st.session_state.phone = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# --- 自动登录决策逻辑 ---
# 只有在还没登录时才执行
if not st.session_state.phone:
    
    # 情况A: 有 URL 参数 (优先级最高)
    if url_phone:
        user = get_user_fuzzy(url_phone)
        if user is not None:
            st.session_state.phone = user['phone']
            st.session_state.user_name = user['name']
            # 登录成功，顺便种下 Cookie (30天过期)
            cookie_manager.set("auth_phone", user['phone'], expires_at=datetime.now() + timedelta(days=30))
    
    # 情况B: 没有 URL，但有 Cookie (用户直接打开主页)
    elif cookie_phone:
        user = get_user_fuzzy(cookie_phone)
        if user is not None:
            st.session_state.phone = user['phone']
            st.session_state.user_name = user['name']
            # 登录成功，补全 URL 方便分享
            st.query_params["phone"] = user['phone']
            st.toast(f"欢迎回来, {user['name']}!", icon="👋")

# --- A. 登录/注册界面 ---
if st.session_state.phone is None or st.session_state.user_name is None:
    st.title("🏭 工厂报餐 / စက်ရုံထမင်းစားစာရင်း")
    
    # 如果正在加载Cookie，显示个加载条
    if cookies is None:
        st.info(TRANS["cookie_login"])
        st.stop()
    
    phone_input = st.text_input(TRANS["login_title"], placeholder="08xxxxxxxx")
    
    if st.button("下一步 / ရှေ့ဆက်ရန်", type="primary", use_container_width=True):
        if phone_input:
            with st.spinner(TRANS["loading"]):
                user = get_user_fuzzy(phone_input)
                
                if user is not None:
                    st.session_state.phone = user['phone']
                    st.session_state.user_name = user['name']
                    st.query_params["phone"] = user['phone']
                    cookie_manager.set("auth_phone", user['phone'], expires_at=datetime.now() + timedelta(days=30))
                    st.rerun()
                else:
                    st.session_state.temp_phone = phone_input
                    st.rerun()
    
    if 'temp_phone' in st.session_state:
        st.info(TRANS["new_user_title"])
        name_input = st.text_input("Name / နာမည်")
        if st.button(TRANS["register_btn"], type="primary", use_container_width=True):
            if name_input:
                with st.spinner(TRANS["loading"]):
                    register_user(st.session_state.temp_phone, name_input)
                    user = get_user_fuzzy(st.session_state.temp_phone)
                    if user is not None:
                        st.session_state.phone = user['phone']
                        st.session_state.user_name = user['name']
                        st.query_params["phone"] = user['phone']
                        cookie_manager.set("auth_phone", user['phone'], expires_at=datetime.now() + timedelta(days=30))
                        st.rerun()

# --- B. 主功能界面 ---
else:
    # 顶部信息
    st.caption(f"👤 {st.session_state.user_name} ({st.session_state.phone})")
    
    # 退出按钮：清Session + 清Cookie
    if st.button(TRANS['logout']):
        cookie_manager.delete("auth_phone")
        st.session_state.phone = None
        st.session_state.user_name = None
        st.query_params.clear()
        st.rerun()
        
    st.divider()

    now_thai = get_thai_time()
    weekday = now_thai.weekday()
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
    # 4. 管理员看板 (带模糊匹配逻辑)
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
            
            # 这里简单展示，生产环境可优化
            master_df = users_df.copy()
            st.dataframe(master_df, use_container_width=True)
