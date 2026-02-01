import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx
import time as time_lib

# ==========================================
# 1. 全局配置与样式 (Global Config)
# ==========================================
st.set_page_config(
    page_title="工厂报餐 / စက်ရုံထမင်းစားစာရင်း",
    page_icon="🍱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入企业级 CSS：隐藏无关菜单，优化触控体验
st.markdown("""
    <style>
    /* 隐藏 Streamlit 默认菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 移动端卡片优化 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.8em;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.1s;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    
    /* 状态栏样式 */
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 业务常量与词典 (Constants)
# ==========================================

# 管理员密码 (可在此修改)
ADMIN_PIN = "8888"

# 时间修正 (UTC+7)
THAILAND_OFFSET = timedelta(hours=7)

# 截止时间 (可随时调整)
LUNCH_DEADLINE = time(23, 59) # 调试模式：全天开放
DINNER_DEADLINE = time(23, 59)

# 翻译词典 (中/缅)
TRANS = {
    # 标题与通用
    "app_title": "🍱 每日报餐系统 / နေ့စဉ်ထမင်းစာရင်း",
    "welcome": "你好 / မင်္ဂလာပါ",
    "logout": "退出登录 / ထွက်ရန်",
    "refresh": "刷新数据 / Refresh",
    "loading": "正在处理... / လုပ်ဆောင်နေသည်...",
    
    # 登录注册
    "login_title": "员工登录 / ဝင်ရောက်ပါ",
    "login_ph": "请输入手机号 (仅数字) / ဖုန်းနံပါတ်",
    "next_btn": "下一步 / ရှေ့ဆက်ရန်",
    "reg_title": "新员工注册 / ဝန်ထမ်းအသစ်",
    "name_ph": "真实姓名 / နာမည်အရင်း",
    "reg_btn": "确认注册 / စာရင်းသွင်းမည်",
    "err_user_exist": "❌ 该手机号已存在 / ဖုန်းနံပါတ်ရှိပြီးသားပါ",
    "err_name_exist": "❌ 该名字已被使用，请联系管理员 / ဒီနာမည်ရှိပြီးသားပါ",
    
    # 规则与状态
    "sun_head": "📅 周日 (Sunday) / တနင်္ဂနွေနေ့",
    "sun_rule": "⚠️ 规则：要吃请点【我要吃】\nစားလိုလျှင် 'စားမည်' ကိုနှိပ်ပါ",
    "wd_head": "📅 工作日 (Weekday) / အလုပ်ဖွင့်ရက်",
    "wd_rule": "⚠️ 规则：默认吃饭。不吃请点【我不吃】\nပုံမှန်စားရမည်။ မစားလိုပါက 'မစားပါ' ကိုနှိပ်ပါ",
    
    # 操作按钮
    "lunch": "午餐 / နေ့လည်စာ",
    "dinner": "晚餐 / ညစာ",
    "btn_eat": "我要吃 / စားမယ် (Eat)",
    "btn_no": "我不吃 / မစားဘူး (No)",
    "btn_undo": "撤销重置 / ပြန်ပြင်မယ်",
    "status_eat": "✅ 状态：吃饭 / စားမယ်",
    "status_no": "❌ 状态：不吃 / မစားပါ",
    "locked": "🔒 已截止 / ပိတ်ပါပြီ",
    
    # 帮助与管理员
    "help_title": "📲 如何添加到桌面 (免登录) / App ကဲ့သို့သုံးနည်း",
    "help_txt": "1. 安卓: 浏览器菜单 -> 添加到主屏幕\n2. 苹果: 分享按钮 -> 添加到主屏幕",
    "admin_entry": "🔐 管理员入口 / Admin Only",
    "admin_pin_ph": "输入管理密码 / Password",
    "admin_login": "进入后台 / Login",
    "admin_dash": "管理后台 / Dashboard",
    "admin_del_user": "删除员工 (离职) / Delete User",
    "admin_del_btn": "确认删除 / Delete",
    "admin_del_success": "员工已删除 / Deleted",
}

# ==========================================
# 3. 数据层：中间件与清洗 (Middleware)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_thai_time():
    return datetime.utcnow() + THAILAND_OFFSET

def clean_phone(val):
    """【核心清洗】强制清洗手机号为纯数字字符串"""
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith(".0"): s = s[:-2]
    # 只保留数字
    return "".join(filter(str.isdigit, s))

def get_db(sheet_name):
    """读取并清洗数据"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        # 初始化表结构
        if sheet_name == "users" and df.empty:
            return pd.DataFrame(columns=["phone", "name", "reg_date"])
        if sheet_name == "orders" and df.empty:
            return pd.DataFrame(columns=["date", "phone", "name", "meal_type", "action", "time"])
        
        # 强制清洗关键列
        if 'phone' in df.columns:
            df['phone'] = df['phone'].apply(clean_phone)
        return df
    except:
        return pd.DataFrame()

def write_db(sheet_name, df):
    """写入数据"""
    if 'phone' in df.columns:
        df['phone'] = df['phone'].astype(str)
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# ==========================================
# 4. 业务逻辑层 (Business Logic)
# ==========================================

def get_user_by_phone(phone):
    df = get_db("users")
    if df.empty: return None
    target = clean_phone(phone)
    # 精确查找 (因为已经清洗过了)
    res = df[df['phone'] == target]
    return res.iloc[0] if not res.empty else None

def check_name_availability(name):
    """检查名字是否可用 (防重名)"""
    df = get_db("users")
    if df.empty or 'name' not in df.columns: return True
    # 忽略大小写和空格
    clean_n = str(name).strip().lower()
    exists = df['name'].astype(str).str.strip().str.lower().eq(clean_n).any()
    return not exists

def register_new_user(phone, name):
    df = get_db("users")
    clean_p = clean_phone(phone)
    
    # 1. 手机号查重
    if not df.empty and clean_p in df['phone'].values:
        return "PHONE_EXIST"
    
    # 2. 名字查重
    if not check_name_availability(name):
        return "NAME_EXIST"
        
    # 3. 执行注册
    # 智能补全泰国手机号前缀0
    if len(clean_p) == 9 and not clean_p.startswith('0'):
        clean_p = '0' + clean_p
        
    new_user = pd.DataFrame([{
        "phone": clean_p,
        "name": str(name).strip(),
        "reg_date": get_thai_time().strftime("%Y-%m-%d")
    }])
    updated = pd.concat([df, new_user], ignore_index=True)
    write_db("users", updated)
    return "SUCCESS"

def delete_user_logic(phone):
    """管理员删除用户"""
    df = get_db("users")
    target = clean_phone(phone)
    if df.empty: return
    # 过滤掉该用户
    updated = df[df['phone'] != target]
    write_db("users", updated)

def update_order_status(phone, name, meal_type, action):
    """更新报餐状态 (今日)"""
    df = get_db("orders")
    today = get_thai_time().strftime("%Y-%m-%d")
    target_p = clean_phone(phone)
    
    # 1. 删除今日该餐次的旧记录
    if not df.empty:
        mask = (df['date'] == today) & (df['meal_type'] == meal_type) & (df['phone'] == target_p)
        df = df[~mask]
        
    # 2. 如果不是"DELETE"(撤销)，则添加新记录
    if action != "DELETE":
        new_row = pd.DataFrame([{
            "date": today,
            "phone": target_p,
            "name": name,
            "meal_type": meal_type,
            "action": action,
            "time": get_thai_time().strftime("%H:%M:%S")
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        
    write_db("orders", df)

def get_current_status(phone, meal_type):
    """查询今日状态"""
    df = get_db("orders")
    if df.empty: return None
    today = get_thai_time().strftime("%Y-%m-%d")
    target_p = clean_phone(phone)
    
    # 筛选
    res = df[(df['date'] == today) & (df['meal_type'] == meal_type) & (df['phone'] == target_p)]
    if not res.empty:
        return res.iloc[-1]['action']
    return None

# ==========================================
# 5. UI 组件层 (View Components)
# ==========================================

def render_login():
    """渲染登录页"""
    st.title(TRANS["app_title"])
    
    # 登录卡片
    with st.container(border=True):
        st.subheader(TRANS["login_title"])
        phone = st.text_input(TRANS["login_ph"], key="login_phone")
        
        if st.button(TRANS["next_btn"], type="primary"):
            if phone:
                clean_p = clean_phone(phone)
                user = get_user_by_phone(clean_p)
                if user is not None:
                    # 登录成功
                    perform_login(user['phone'], user['name'])
                else:
                    # 去注册
                    st.session_state.temp_phone = clean_p
                    st.rerun()

    # 注册卡片 (仅当检测到新号码时显示)
    if 'temp_phone' in st.session_state:
        st.warning(f"🆕 正在注册 / Registering: {st.session_state.temp_phone}")
        with st.container(border=True):
            st.subheader(TRANS["reg_title"])
            name = st.text_input(TRANS["name_ph"])
            
            if st.button(TRANS["reg_btn"], type="primary"):
                if name:
                    res = register_new_user(st.session_state.temp_phone, name)
                    if res == "SUCCESS":
                        perform_login(st.session_state.temp_phone, name)
                    elif res == "NAME_EXIST":
                        st.error(TRANS["err_name_exist"])
                    else:
                        st.error("Error occurred")

def render_dashboard():
    """渲染主功能页"""
    # 1. 顶部栏
    c1, c2 = st.columns([3, 1])
    with c1:
        st.write(f"👋 {TRANS['welcome']}, **{st.session_state.user_name}**")
        st.caption(f"📱 {st.session_state.phone}")
    with c2:
        if st.button(TRANS["logout"]):
            perform_logout()
    
    st.markdown("---")

    # 2. 日期与规则
    now = get_thai_time()
    is_sunday = (now.weekday() == 6)
    current_time = now.time()
    
    rule_title = TRANS["sun_head"] if is_sunday else TRANS["wd_head"]
    rule_msg = TRANS["sun_rule"] if is_sunday else TRANS["wd_rule"]
    
    # 使用 info 框展示规则，颜色区分
    st.info(f"**{rule_title}**\n\n{rule_msg}")

    # 3. 报餐卡片
    col1, col2 = st.columns(2)
    render_meal_card(col1, "Lunch", TRANS["lunch"], LUNCH_DEADLINE, is_sunday, current_time)
    render_meal_card(col2, "Dinner", TRANS["dinner"], DINNER_DEADLINE, is_sunday, current_time)

    # 4. 底部帮助
    st.markdown("---")
    with st.expander(TRANS["help_title"]):
        st.info(TRANS["help_txt"])

def render_meal_card(col, m_key, title, deadline, is_sunday, cur_time):
    """渲染单个餐次卡片"""
    with col:
        with st.container(border=True):
            st.markdown(f"#### {title}")
            
            # 获取状态
            status_code = get_current_status(st.session_state.phone, m_key)
            
            # 逻辑判定
            is_closed = cur_time > deadline
            user_eating = (status_code == "BOOKED") if is_sunday else (status_code != "CANCELED")
            
            # 显示状态
            if user_eating:
                st.success(TRANS["status_eat"])
            else:
                st.error(TRANS["status_no"])
            
            # 截止时间
            time_display = "24H" if deadline.hour==23 else deadline.strftime('%H:%M')
            st.caption(f"🕒 截止: {time_display}")
            
            # 按钮区
            if is_closed:
                st.caption(TRANS["locked"])
            else:
                if is_sunday:
                    # 周日逻辑
                    if not user_eating:
                        if st.button(TRANS["btn_eat"], key=f"btn_{m_key}", type="primary"):
                            update_order_status(st.session_state.phone, st.session_state.user_name, m_key, "BOOKED")
                            st.rerun()
                    else:
                        if st.button(TRANS["btn_undo"], key=f"undo_{m_key}"):
                            update_order_status(st.session_state.phone, st.session_state.user_name, m_key, "DELETE")
                            st.rerun()
                else:
                    # 平日逻辑
                    if user_eating:
                        if st.button(TRANS["btn_no"], key=f"btn_{m_key}", type="primary"):
                            update_order_status(st.session_state.phone, st.session_state.user_name, m_key, "CANCELED")
                            st.rerun()
                    else:
                        if st.button(TRANS["btn_undo"], key=f"undo_{m_key}"):
                            update_order_status(st.session_state.phone, st.session_state.user_name, m_key, "DELETE")
                            st.rerun()

def render_admin_panel():
    """渲染管理员后台"""
    st.markdown("---")
    with st.expander(TRANS["admin_entry"]):
        # 验证逻辑
        if not st.session_state.get('admin_authed', False):
            pin = st.text_input(TRANS["admin_pin_ph"], type="password")
            if st.button(TRANS["admin_login"]):
                if pin == ADMIN_PIN:
                    st.session_state.admin_authed = True
                    st.rerun()
                else:
                    st.error("密码错误 / Wrong Password")
        else:
            # 已验证，显示后台
            st.subheader(TRANS["admin_dash"])
            if st.button(TRANS["refresh"]):
                st.cache_data.clear()
                st.rerun()
                
            # 获取全量数据
            users = get_db("users")
            orders = get_db("orders")
            
            # 1. 统计数据
            if not users.empty:
                # 构造今日大表
                today = get_thai_time().strftime("%Y-%m-%d")
                today_orders = orders[orders['date'] == today] if not orders.empty else pd.DataFrame()
                
                master = users.copy()
                
                # 计算逻辑 (复用)
                l_act = pd.DataFrame()
                d_act = pd.DataFrame()
                
                if not today_orders.empty:
                    l_act = today_orders[today_orders['meal_type'] == 'Lunch'][['phone', 'action']]
                    d_act = today_orders[today_orders['meal_type'] == 'Dinner'][['phone', 'action']]
                
                master = master.merge(l_act, on='phone', how='left').rename(columns={'action': 'L'})
                master = master.merge(d_act, on='phone', how='left').rename(columns={'action': 'D'})
                master = master.drop_duplicates(subset=['phone']) # 防重显示
                
                is_sun = (get_thai_time().weekday() == 6)
                
                def check_eat(act, is_sun):
                    if is_sun: return act == "BOOKED"
                    return act != "CANCELED"
                
                master['Lunch_Eat'] = master['L'].apply(lambda x: check_eat(x, is_sun))
                master['Dinner_Eat'] = master['D'].apply(lambda x: check_eat(x, is_sun))
                
                # 指标卡
                k1, k2, k3 = st.columns(3)
                k1.metric("总人数", len(master))
                k2.metric("午餐数", master['Lunch_Eat'].sum())
                k3.metric("晚餐数", master['Dinner_Eat'].sum())
                
                # 2. 详细名单与删除功能
                st.write("---")
                st.write("📋 人员管理 / Manage Users")
                
                # 选择要删除的人
                user_list = master.apply(lambda x: f"{x['name']} ({x['phone']})", axis=1).tolist()
                selected_user = st.selectbox(TRANS["admin_del_user"], ["选择员工..."] + user_list)
                
                if st.button(TRANS["admin_del_btn"], type="primary"):
                    if selected_user != "选择员工...":
                        # 提取手机号 (括号里的内容)
                        target_p = selected_user.split('(')[-1].replace(')', '')
                        delete_user_logic(target_p)
                        st.success(f"{TRANS['admin_del_success']}: {target_p}")
                        time_lib.sleep(1)
                        st.rerun()
                
                # 展示表格
                view_df = master[['name', 'phone', 'Lunch_Eat', 'Dinner_Eat']].copy()
                view_df['Lunch'] = view_df['Lunch_Eat'].apply(lambda x: "✅" if x else "❌")
                view_df['Dinner'] = view_df['Dinner_Eat'].apply(lambda x: "✅" if x else "❌")
                st.dataframe(view_df[['name', 'phone', 'Lunch', 'Dinner']], use_container_width=True)

# ==========================================
# 6. 程序入口与 Cookie 管理
# ==========================================

cookie_manager = stx.CookieManager()
cookies = cookie_manager.get_all()

def perform_login(phone, name):
    st.session_state.phone = phone
    st.session_state.user_name = name
    # 写入 Cookie (30天)
    cookie_manager.set("auth_phone", phone, expires_at=datetime.now() + timedelta(days=30))
    st.rerun()

def perform_logout():
    cookie_manager.delete("auth_phone")
    st.session_state.phone = None
    st.session_state.user_name = None
    st.session_state.admin_authed = False # 退出管理员
    st.rerun()

# 初始化 Session
if 'phone' not in st.session_state:
    st.session_state.phone = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# 自动登录检查 (仅一次)
if not st.session_state.phone:
    # 1. 检查 Cookie
    c_phone = cookies.get("auth_phone") if cookies else None
    if c_phone:
        user = get_user_by_phone(c_phone)
        if user is not None:
            st.session_state.phone = user['phone']
            st.session_state.user_name = user['name']
            st.rerun()

# 路由分发
if st.session_state.phone:
    render_dashboard()
    render_admin_panel() # 只有登录后才显示管理员入口(在底部)
else:
    # 如果 Cookie 还没加载完，等待一下，避免闪烁
    if cookies is None:
        st.info(TRANS["cookie_loading"])
        st.stop()
    render_login()
    render_admin_panel() # 未登录也能看到管理员入口(方便管理员维护)
