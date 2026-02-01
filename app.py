import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, timezone
import calendar
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx
import time as time_lib

# ==========================================
# 1. 全局配置与样式
# ==========================================
st.set_page_config(
    page_title="工厂报餐 / စက်ရုံထမင်းစားစာရင်း",
    page_icon="🍱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* 移动端触控优化 */
    .stButton>button {
        width: 100%; border-radius: 12px; height: 3.8em; font-weight: 600;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stDataFrame { width: 100% !important; }
    div[data-testid="stDateInput"] {
        border: 2px solid #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        background-color: #ffffff;
    }
    /* 专属链接区域样式 */
    .link-box {
        padding: 10px;
        background-color: #e8f5e9;
        border-radius: 8px;
        border: 1px solid #c8e6c9;
        margin-bottom: 15px;
        text-align: center;
        color: #2e7d32;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 业务配置
# ==========================================
try:
    ADMIN_PIN = st.secrets["ADMIN_PIN"]
except:
    ADMIN_PIN = "8888"

THAILAND_OFFSET = timedelta(hours=7)

# ⏰ 截止时间
LUNCH_DEADLINE = time(10, 0)
DINNER_DEADLINE = time(15, 0)
AUTO_SWITCH_HOUR = 18

TRANS = {
    "app_title": "🍱 每日报餐 / နေ့စဉ်ထမင်းစာရင်း",
    "welcome": "你好 / မင်္ဂလာပါ",
    "logout": "退出 / ထွက်ရန်",
    "login_title": "员工登录 / ဝင်ရောက်ပါ",
    "login_ph": "输入手机号 / ဖုန်းနံပါတ်",
    "next_btn": "下一步 / ရှေ့ဆက်ရန်",
    "reg_title": "新员工注册 / ဝန်ထမ်းအသစ်",
    "name_ph": "姓名 / နာမည်",
    "reg_btn": "注册 / စာရင်းသွင်းမည်",
    "err_user_exist": "❌ 已存在 / ရှိပြီးသားပါ",
    "err_name_exist": "❌ 名字重复 / နာမည်တူရှိနေပါသည်",
    "sun_head": "📅 周日 (Sunday) / တနင်္ဂနွေနေ့",
    "sun_rule": "⚠️ 规则：要吃请点【我要吃】 / စားလိုလျှင် 'စားမည်' ကိုနှိပ်ပါ",
    "wd_head": "📅 工作日 (Weekday) / အလုပ်ဖွင့်ရက်",
    "wd_rule": "⚠️ 规则：默认吃饭。不吃请点【我不吃】 / ပုံမှန်စားရမည်။ မစားလိုပါက 'မစားပါ' ကိုနှိပ်ပါ",
    "lunch": "午餐 / နေ့လည်စာ",
    "dinner": "晚餐 / ညစာ",
    "btn_eat": "我要吃 / စားမယ် (Eat)",
    "btn_no": "我不吃 / မစားဘူး (No)",
    "btn_undo": "撤销 / ပြန်ပြင်မယ်",
    "status_eat": "✅ 状态：吃饭 / စားမယ်",
    "status_no": "❌ 状态：不吃 / မစားပါ",
    "locked": "🔒 已截止 / ပိတ်ပါပြီ",
    "help_title": "📲 必看：如何设置免登录？",
    "help_txt": "👉 **最稳妥的方法：**\n1. 点击上方【复制专属链接】\n2. 打开手机浏览器(Chrome/Safari)\n3. 粘贴链接并访问\n4. 将该页面【添加到主屏幕】或【收藏书签】\n\n这样下次打开就是你自己的账号，绝对不用再登录！",
    "admin_entry": "🔐 管理员 / Admin",
    "admin_login": "登录后台 / Login",
    "admin_clean": "🧹 深度修复数据 (合并重复项)",
    "admin_clean_success": "修复完成！",
    "cookie_loading": "🔄 正在检测登录状态...",
    "tab_today": "📅 今日看板 / Daily",
    "tab_month": "📊 月度报表 / Monthly",
    "month_sel": "选择月份 / Select Month",
    "date_label": "📅 选择报餐日期 / ရက်စွဲရွေးပါ",
    "switch_tmr_hint": "🌙 已过18点，默认显示明天 / မနက်ဖြန်စာရင်း",
    "refresh": "刷新数据 / Refresh",
    "copy_link": "🔗 复制我的专属链接 (用于收藏)",
    "copy_success": "✅ 链接已复制！请添加到浏览器书签。",
}

# ==========================================
# 3. 核心数据层
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_thai_time():
    return datetime.now(timezone.utc) + THAILAND_OFFSET

def standardize_phone(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith(".0"): s = s[:-2]
    digits = "".join(filter(str.isdigit, s))
    if len(digits) == 9: digits = '0' + digits
    return digits

def get_db(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if sheet_name == "users" and df.empty:
            return pd.DataFrame(columns=["phone", "name", "reg_date"])
        if sheet_name == "orders" and df.empty:
            return pd.DataFrame(columns=["date", "phone", "name", "meal_type", "action", "time"])
        if 'phone' in df.columns:
            df['phone'] = df['phone'].astype(str).apply(standardize_phone)
        return df
    except:
        return pd.DataFrame()

def write_db(sheet_name, df):
    if 'phone' in df.columns:
        df['phone'] = df['phone'].astype(str).apply(standardize_phone)
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

def admin_clean_database():
    users = get_db("users")
    if not users.empty:
        users = users.drop_duplicates(subset=['phone'], keep='last')
        write_db("users", users)
    orders = get_db("orders")
    if not orders.empty:
        orders = orders.drop_duplicates()
        write_db("orders", orders)

# ==========================================
# 4. 业务逻辑
# ==========================================

def get_user_by_phone(phone):
    df = get_db("users")
    if df.empty: return None
    target = standardize_phone(phone)
    res = df[df['phone'] == target]
    return res.iloc[0] if not res.empty else None

def check_name_exist(name):
    df = get_db("users")
    if df.empty or 'name' not in df.columns: return False
    clean_n = str(name).strip().lower()
    return df['name'].astype(str).str.strip().str.lower().eq(clean_n).any()

def register_new_user(phone, name):
    df = get_db("users")
    clean_p = standardize_phone(phone)
    if not df.empty and clean_p in df['phone'].values: return "PHONE_EXIST"
    if check_name_exist(name): return "NAME_EXIST"
    new_user = pd.DataFrame([{
        "phone": clean_p,
        "name": str(name).strip(),
        "reg_date": get_thai_time().strftime("%Y-%m-%d")
    }])
    updated = pd.concat([df, new_user], ignore_index=True)
    write_db("users", updated)
    return "SUCCESS"

def update_order(phone, name, meal_type, action, target_date_str):
    df = get_db("orders")
    target_p = standardize_phone(phone)
    if not df.empty:
        mask = (df['date'] == target_date_str) & (df['meal_type'] == meal_type) & (df['phone'] == target_p)
        df = df[~mask]
    if action != "DELETE":
        new_row = pd.DataFrame([{
            "date": target_date_str, "phone": target_p, "name": name,
            "meal_type": meal_type, "action": action,
            "time": get_thai_time().strftime("%H:%M:%S")
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    write_db("orders", df)

def get_status(phone, meal_type, target_date_str):
    df = get_db("orders")
    if df.empty: return None
    target_p = standardize_phone(phone)
    res = df[(df['date'] == target_date_str) & (df['meal_type'] == meal_type) & (df['phone'] == target_p)]
    return res.iloc[-1]['action'] if not res.empty else None

def delete_user_logic(phone):
    df = get_db("users")
    target = standardize_phone(phone)
    if not df.empty:
        updated = df[df['phone'] != target]
        write_db("users", updated)

def calculate_monthly_stats(year, month):
    users = get_db("users")
    orders = get_db("orders")
    if users.empty: return None, None
    start_date = f"{year}-{month:02d}-01"
    end_day = calendar.monthrange(year, month)[1]
    end_date = f"{year}-{month:02d}-{end_day}"
    
    if not orders.empty:
        orders['date'] = pd.to_datetime(orders['date'])
        mask = (orders['date'] >= start_date) & (orders['date'] <= end_date)
        month_orders = orders.loc[mask].copy()
        month_orders['date_str'] = month_orders['date'].dt.strftime('%Y-%m-%d')
        month_orders['weekday'] = month_orders['date'].dt.weekday
    else:
        month_orders = pd.DataFrame()

    daily_stats = []
    for day in range(1, end_day + 1):
        d_obj = datetime(year, month, day)
        d_str = d_obj.strftime("%Y-%m-%d")
        is_sun = (d_obj.weekday() == 6)
        total_users = len(users)
        
        if not month_orders.empty:
            day_data = month_orders[month_orders['date_str'] == d_str]
        else:
            day_data = pd.DataFrame()
            
        if is_sun:
            l_cnt = len(day_data[(day_data['meal_type'] == 'Lunch') & (day_data['action'] == 'BOOKED')])
            d_cnt = len(day_data[(day_data['meal_type'] == 'Dinner') & (day_data['action'] == 'BOOKED')])
        else:
            l_canceled = len(day_data[(day_data['meal_type'] == 'Lunch') & (day_data['action'] == 'CANCELED')])
            d_canceled = len(day_data[(day_data['meal_type'] == 'Dinner') & (day_data['action'] == 'CANCELED')])
            l_cnt = total_users - l_canceled
            d_cnt = total_users - d_canceled
        daily_stats.append({"Date": d_str, "Lunch": l_cnt, "Dinner": d_cnt})

    stats_dict = {row['phone']: {'L': 0, 'D': 0, 'Name': row['name']} for _, row in users.iterrows()}
    
    if not month_orders.empty:
        order_lookup = {}
        for _, row in month_orders.iterrows():
            order_lookup[(row['date_str'], row['phone'], row['meal_type'])] = row['action']
            
        for day in range(1, end_day + 1):
            d_obj = datetime(year, month, day)
            d_str = d_obj.strftime("%Y-%m-%d")
            is_sun = (d_obj.weekday() == 6)
            for p in stats_dict:
                act_l = order_lookup.get((d_str, p, 'Lunch'))
                eat_l = (act_l == "BOOKED") if is_sun else (act_l != "CANCELED")
                if eat_l: stats_dict[p]['L'] += 1
                act_d = order_lookup.get((d_str, p, 'Dinner'))
                eat_d = (act_d == "BOOKED") if is_sun else (act_d != "CANCELED")
                if eat_d: stats_dict[p]['D'] += 1
    
    return pd.DataFrame(daily_stats), pd.DataFrame.from_dict(stats_dict, orient='index')

# ==========================================
# 5. 页面渲染
# ==========================================

def render_login():
    st.title(TRANS["app_title"])
    with st.container(border=True):
        st.subheader(TRANS["login_title"])
        phone = st.text_input(TRANS["login_ph"], key="login_phone")
        if st.button(TRANS["next_btn"], type="primary"):
            if phone:
                clean_p = standardize_phone(phone)
                with st.spinner("Checking..."):
                    user = get_user_by_phone(clean_p)
                    if user is not None:
                        perform_login(user['phone'], user['name'])
                    else:
                        st.session_state.temp_phone = clean_p
                        st.rerun()

    if 'temp_phone' in st.session_state:
        st.warning(f"🆕 注册 / Register: {st.session_state.temp_phone}")
        with st.container(border=True):
            st.subheader(TRANS["reg_title"])
            name = st.text_input(TRANS["name_ph"], key="reg_name")
            if st.button(TRANS["reg_btn"], type="primary"):
                if name:
                    with st.spinner("Registering..."):
                        res = register_new_user(st.session_state.temp_phone, name)
                        if res == "SUCCESS":
                            perform_login(st.session_state.temp_phone, name)
                        elif res == "NAME_EXIST":
                            st.error(TRANS["err_name_exist"])
                        elif res == "PHONE_EXIST":
                            st.error(TRANS["err_user_exist"])
                        else:
                            st.error("Error")

def render_admin_panel():
    st.markdown("---")
    with st.expander(TRANS["admin_entry"]):
        if not st.session_state.get('admin_authed', False):
            pin = st.text_input("PIN", type="password")
            if st.button(TRANS["admin_login"]):
                if pin == ADMIN_PIN:
                    st.session_state.admin_authed = True
                    st.rerun()
                else:
                    st.error("Error")
        else:
            c1, c2 = st.columns([3, 1])
            with c1: st.write("### " + TRANS["app_title"])
            with c2: 
                if st.button(TRANS["refresh"]): st.cache_data.clear(); st.rerun()
            
            if st.button(TRANS["admin_clean"], type="secondary"):
                with st.spinner("Processing..."):
                    admin_clean_database()
                    st.success(TRANS["admin_clean_success"])
                    time_lib.sleep(1)
                    st.rerun()
            
            tab1, tab2 = st.tabs([TRANS["tab_today"], TRANS["tab_month"]])
            
            with tab1:
                view_date = st.date_input("查看日期 / View Date", value=get_thai_time().date(), key="admin_date")
                view_date_str = view_date.strftime("%Y-%m-%d")
                
                users = get_db("users")
                orders = get_db("orders")
                
                if not users.empty:
                    l_act = pd.DataFrame(columns=['phone', 'action'])
                    d_act = pd.DataFrame(columns=['phone', 'action'])
                    
                    if not orders.empty:
                        today_orders = orders[orders['date'] == view_date_str]
                        if not today_orders.empty:
                            today_orders['phone'] = today_orders['phone'].astype(str).apply(standardize_phone)
                            l_temp = today_orders[today_orders['meal_type'] == 'Lunch'][['phone', 'action']]
                            if not l_temp.empty: l_act = l_temp
                            d_temp = today_orders[today_orders['meal_type'] == 'Dinner'][['phone', 'action']]
                            if not d_temp.empty: d_act = d_temp
                    
                    master = users.copy()
                    master['phone'] = master['phone'].astype(str).apply(standardize_phone)
                    master = master.merge(l_act, on='phone', how='left').rename(columns={'action': 'L'})
                    master = master.merge(d_act, on='phone', how='left').rename(columns={'action': 'D'})
                    master = master.drop_duplicates(subset=['phone'])
                    
                    is_sun = (view_date.weekday() == 6)
                    def check_eat(act, is_sun):
                        if is_sun: return act == "BOOKED"
                        return act != "CANCELED"
                    
                    master['L_Eat'] = master['L'].apply(lambda x: check_eat(x, is_sun))
                    master['D_Eat'] = master['D'].apply(lambda x: check_eat(x, is_sun))
                    
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Total", len(master))
                    k2.metric("Lunch", master['L_Eat'].sum())
                    k3.metric("Dinner", master['D_Eat'].sum())
                    
                    user_list = master.apply(lambda x: f"{x['name']} ({x['phone']})", axis=1).tolist()
                    sel_user = st.selectbox("Delete User", ["Select..."] + user_list)
                    if st.button("Confirm Delete"):
                        if sel_user != "Select...":
                            target_p = sel_user.split('(')[-1].replace(')', '')
                            delete_user_logic(target_p)
                            st.success("Deleted")
                            time_lib.sleep(1)
                            st.rerun()
                    
                    display_df = master[['name', 'phone', 'L_Eat', 'D_Eat']].copy()
                    display_df['phone'] = display_df['phone'].astype(str)
                    display_df['Lunch'] = display_df['L_Eat'].apply(lambda x: "✅" if x else "❌")
                    display_df['Dinner'] = display_df['D_Eat'].apply(lambda x: "✅" if x else "❌")
                    st.dataframe(display_df[['name', 'phone', 'Lunch', 'Dinner']], use_container_width=True, hide_index=True)

            with tab2:
                now = get_thai_time()
                c_m1, c_m2 = st.columns(2)
                sel_year = c_m1.number_input("Year", min_value=2024, max_value=2030, value=now.year)
                sel_month = c_m2.number_input("Month", min_value=1, max_value=12, value=now.month)
                if st.button("Generate Report"):
                    with st.spinner("Calculating..."):
                        daily_df, person_df = calculate_monthly_stats(sel_year, sel_month)
                        if daily_df is not None:
                            st.bar_chart(daily_df.set_index("Date")[["Lunch", "Dinner"]])
                            person_df = person_df.reset_index().rename(columns={'index': 'Phone'})
                            person_df['Phone'] = person_df['Phone'].astype(str)
                            st.dataframe(person_df[['Name', 'Phone', 'L', 'D']], use_container_width=True, hide_index=True)
                        else:
                            st.warning("No Data")

# ==========================================
# 6. 程序入口与 Cookie
# ==========================================
# 给 CookieManager 指定 key，防止刷新丢失
cookie_manager = stx.CookieManager(key="meal_app_auth")
cookies = cookie_manager.get_all()

def perform_login(phone, name):
    st.session_state.phone = phone
    st.session_state.user_name = name
    # 设置30天过期
    cookie_manager.set("auth_phone", phone, expires_at=datetime.now() + timedelta(days=30))
    # 强制更新 URL 参数
    st.query_params["phone"] = phone
    st.rerun()

def perform_logout():
    cookie_manager.delete("auth_phone")
    st.session_state.phone = None
    st.session_state.user_name = None
    st.session_state.admin_authed = False
    st.query_params.clear()
    st.rerun()

if 'phone' not in st.session_state:
    st.session_state.phone = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# --- 自动登录逻辑升级 ---
if not st.session_state.phone:
    # 1. 优先查 URL (最稳)
    qp = st.query_params
    url_phone = qp.get("phone", None)
    
    # 2. 其次查 Cookie
    cookie_phone = cookies.get("auth_phone") if cookies else None
    
    # 目标号码
    target = url_phone if url_phone else cookie_phone
    
    if target:
        user = get_user_by_phone(target)
        if user is not None:
            st.session_state.phone = user['phone']
            st.session_state.user_name = user['name']
            
            # 如果是 Cookie 登录的，自动补全 URL
            if not url_phone:
                st.query_params["phone"] = user['phone']
            
            # 如果是 URL 登录的，自动补全 Cookie
            if not cookie_phone:
                cookie_manager.set("auth_phone", user['phone'], expires_at=datetime.now() + timedelta(days=30))
            
            st.rerun()

# --- 渲染逻辑 ---
if st.session_state.phone:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.write(f"👋 {TRANS['welcome']}, **{st.session_state.user_name}**")
        st.caption(f"📱 {st.session_state.phone}")
    with c2:
        if st.button(TRANS["logout"]): perform_logout()
    
    # --- 显眼提示：复制链接 ---
    # 构建当前完整链接 (Streamlit 无法直接获取域名，只能提示复制当前URL)
    st.markdown(f'<div class="link-box">{TRANS["copy_link"]}</div>', unsafe_allow_html=True)
    # 提供一个 text_input 方便复制
    full_link = f"请复制浏览器顶部链接，或收藏此页面"
    st.caption("✅ 登录成功！请将当前页面【添加到主屏幕】，下次即可免登录。")
    
    st.markdown("---")
    
    now = get_thai_time()
    current_time = now.time()
    
    default_date = now.date()
    if now.hour >= AUTO_SWITCH_HOUR:
        default_date = now.date() + timedelta(days=1)
        st.info(TRANS["switch_tmr_hint"])
        
    selected_date = st.date_input(TRANS["date_label"], value=default_date)
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    
    is_sun = (selected_date.weekday() == 6)
    
    rule_title = TRANS["sun_head"] if is_sun else TRANS["wd_head"]
    rule_msg = TRANS["sun_rule"] if is_sun else TRANS["wd_rule"]
    st.info(f"**{rule_title}**\n\n{rule_msg}")
    
    is_today_selected = (selected_date == now.date())
    
    col1, col2 = st.columns(2)
    
    # 午餐
    with col1:
        with st.container(border=True):
            st.markdown(f"#### {TRANS['lunch']}")
            stat = get_status(st.session_state.phone, "Lunch", selected_date_str)
            eat = (stat == "BOOKED") if is_sun else (stat != "CANCELED")
            if eat: st.success(TRANS["status_eat"])
            else: st.error(TRANS["status_no"])
            
            is_locked = False
            if is_today_selected and current_time > LUNCH_DEADLINE:
                is_locked = True
                
            if is_locked:
                st.caption(TRANS["locked"])
            else:
                if is_sun:
                    if not eat:
                        if st.button(TRANS["btn_eat"], key="l_e", type="primary"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "BOOKED", selected_date_str); st.rerun()
                    else:
                        if st.button(TRANS["btn_undo"], key="l_u"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "DELETE", selected_date_str); st.rerun()
                else:
                    if eat:
                        if st.button(TRANS["btn_no"], key="l_n", type="primary"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "CANCELED", selected_date_str); st.rerun()
                    else:
                        if st.button(TRANS["btn_undo"], key="l_u"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "DELETE", selected_date_str); st.rerun()

    # 晚餐
    with col2:
        with st.container(border=True):
            st.markdown(f"#### {TRANS['dinner']}")
            stat = get_status(st.session_state.phone, "Dinner", selected_date_str)
            eat = (stat == "BOOKED") if is_sun else (stat != "CANCELED")
            if eat: st.success(TRANS["status_eat"])
            else: st.error(TRANS["status_no"])
            
            is_locked = False
            if is_today_selected and current_time > DINNER_DEADLINE:
                is_locked = True
            
            if is_locked:
                st.caption(TRANS["locked"])
            else:
                if is_sun:
                    if not eat:
                        if st.button(TRANS["btn_eat"], key="d_e", type="primary"): update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "BOOKED", selected_date_str); st.rerun()
                    else:
                        if st.button(TRANS["btn_undo"], key="d_u"): update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "DELETE", selected_date_str); st.rerun()
                else:
                    if eat:
                        if st.button(TRANS["btn_no"], key="d_n", type="primary"): update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "CANCELED", selected_date_str); st.rerun()
                    else:
                        if st.button(TRANS["btn_undo"], key="d_u"): update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "DELETE", selected_date_str); st.rerun()

    st.markdown("---")
    with st.expander(TRANS["help_title"]): st.info(TRANS["help_txt"])
    render_admin_panel()

else:
    # 登录前逻辑优化：不让 loading 卡住界面
    # 尝试渲染登录页，如果 Cookie 加载好了会自动跳转
    render_login()
    render_admin_panel()
