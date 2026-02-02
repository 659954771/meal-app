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
    /* 留饭时间按钮样式 */
    .late-time-btn {
        margin: 2px;
    }
    /* 专属链接区域样式 */
    .link-box {
        padding: 15px;
        background-color: #e3f2fd;
        border-radius: 8px;
        border: 1px solid #bbdefb;
        margin-bottom: 15px;
        color: #0d47a1;
        font-size: 14px;
        line-height: 1.6;
        text-align: center;
    }
    .url-text {
        font-family: monospace;
        background: #fff;
        padding: 5px;
        border-radius: 4px;
        border: 1px solid #ddd;
        word-break: break-all;
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

LUNCH_DEADLINE = time(10, 0)
DINNER_DEADLINE = time(15, 0)
AUTO_SWITCH_HOUR = 18

# 新增：留饭时间选项 (分别配置午餐和晚餐)
LUNCH_LATE_OPTIONS = ["12:30", "13:00"]
DINNER_LATE_OPTIONS = ["19:00", "20:00", "21:00"]

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
    "btn_late": "留饭 / ထမင်းချန်မယ်", 
    "btn_undo": "撤销 / ပြန်ပြင်မယ်",
    "status_eat": "✅ 状态：正常吃饭 / ပုံမှန်စားမယ်",
    "status_no": "❌ 状态：不吃 / မစားပါ",
    "status_late": "🥡 状态：留饭 / ထမင်းချန်ထား",
    "lbl_late_title": "留饭/晚回 / ထမင်းချန်မယ် (Late):",
    "locked": "🔒 已截止 / ပိတ်ပါပြီ",
    "help_title": "📲 必看：如何添加到桌面不掉登录？",
    "help_txt": "👉 **关键步骤：**\n1. 确保你现在已经登录成功（能看到名字）。\n2. **检查浏览器地址栏**，必须包含 `?phone=xxxx`。\n3. 点击浏览器【分享/菜单】 -> 【添加到主屏幕】。\n\n⚠️ 如果添加后的图标点开还需要登录，请先**删除旧图标**，重新按上述步骤添加。",
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
    "ios_alert": "📱 **设置免登录图标：**\n请点击浏览器底部的【分享按钮】📤 -> 选择【添加到主屏幕】。\n这样下次直接点图标就能进！",
    "chef_view": "👨‍🍳 厨师/留饭看板 (Chef)", 
    "chef_view_title": "🥣 留饭/打包清单 / ထမင်းချန်စာရင်း",
    "chef_lunch_sec": "☀️ 午餐留饭 / နေ့လည်စာ ထမင်းချန်",
    "chef_dinner_sec": "🌙 晚餐留饭 / ညစာ ထမင်းချန်",
    "chef_pickup": "取餐 / ယူရန်",
    "chef_total": "共 / စုစုပေါင်း",
    "chef_people": "人 / ယောက်",
    "chef_empty": "暂无留饭 / ထမင်းချန်သူမရှိပါ",
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

# 修改：update_order 现在支持传入 action_value (例如 LATE_19:00)
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

# 核心逻辑：判断某个人在某天某顿饭的状态
# 返回: "NORMAL", "LATE_xx:xx", "NO"
def resolve_meal_status(action, is_sun):
    if pd.isna(action) or action is None:
        return "NO" if is_sun else "NORMAL"
    
    s_act = str(action)
    if s_act == "CANCELED": return "NO"
    if s_act == "DELETE": return "NO" if is_sun else "NORMAL"
    if s_act == "BOOKED": return "NORMAL"
    if s_act.startswith("LATE"): return s_act # e.g., LATE_19:00
    
    return "NO" if is_sun else "NORMAL"

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
            
        # 统计午餐
        l_eaters = 0
        d_eaters = 0
        
        # 简单统计逻辑：遍历所有用户判断
        # (这种方式比直接count dataframe更准确，因为涉及默认规则)
        user_phones = users['phone'].tolist()
        for u_p in user_phones:
            # Lunch
            l_act = None
            if not day_data.empty:
                row = day_data[(day_data['meal_type'] == 'Lunch') & (day_data['phone'] == u_p)]
                if not row.empty: l_act = row.iloc[-1]['action']
            if resolve_meal_status(l_act, is_sun) != "NO":
                l_eaters += 1
                
            # Dinner
            d_act = None
            if not day_data.empty:
                row = day_data[(day_data['meal_type'] == 'Dinner') & (day_data['phone'] == u_p)]
                if not row.empty: d_act = row.iloc[-1]['action']
            if resolve_meal_status(d_act, is_sun) != "NO":
                d_eaters += 1

        daily_stats.append({"Date": d_str, "Lunch": l_eaters, "Dinner": d_eaters})

    # 个人统计
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
                if resolve_meal_status(act_l, is_sun) != "NO": stats_dict[p]['L'] += 1
                
                act_d = order_lookup.get((d_str, p, 'Dinner'))
                if resolve_meal_status(act_d, is_sun) != "NO": stats_dict[p]['D'] += 1
    
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
            
            tab1, tab2, tab3 = st.tabs([TRANS["tab_today"], TRANS["tab_month"], TRANS["chef_view"]])
            
            # --- Tab 1: 原始列表 ---
            with tab1:
                view_date = st.date_input("查看日期 / View Date", value=get_thai_time().date(), key="admin_date")
                view_date_str = view_date.strftime("%Y-%m-%d")
                
                users = get_db("users")
                orders = get_db("orders")
                
                if not users.empty:
                    master = users.copy()
                    master['phone'] = master['phone'].astype(str).apply(standardize_phone)
                    
                    # 构建 lookup map
                    l_map = {}
                    d_map = {}
                    if not orders.empty:
                        today_orders = orders[orders['date'] == view_date_str]
                        for _, r in today_orders.iterrows():
                            if r['meal_type'] == 'Lunch': l_map[standardize_phone(r['phone'])] = r['action']
                            if r['meal_type'] == 'Dinner': d_map[standardize_phone(r['phone'])] = r['action']

                    is_sun_view = (view_date.weekday() == 6)
                    
                    master['L_Status'] = master['phone'].apply(lambda p: resolve_meal_status(l_map.get(p), is_sun_view))
                    master['D_Status'] = master['phone'].apply(lambda p: resolve_meal_status(d_map.get(p), is_sun_view))
                    
                    # 统计数字
                    k1, k2, k3 = st.columns(3)
                    k1.metric("总人数", len(master))
                    k2.metric("午餐", len(master[master['L_Status'] != 'NO']))
                    k3.metric("晚餐", len(master[master['D_Status'] != 'NO']))
                    
                    # 删除用户逻辑
                    user_list = master.apply(lambda x: f"{x['name']} ({x['phone']})", axis=1).tolist()
                    sel_user = st.selectbox("Delete User", ["Select..."] + user_list)
                    if st.button("Confirm Delete"):
                        if sel_user != "Select...":
                            target_p = sel_user.split('(')[-1].replace(')', '')
                            delete_user_logic(target_p)
                            st.success("Deleted")
                            st.rerun()
                    
                    st.dataframe(master[['name', 'phone', 'L_Status', 'D_Status']], use_container_width=True, hide_index=True)

            # --- Tab 2: 月报 ---
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

            # --- Tab 3: 厨师看板 (更新了午餐和缅甸语) ---
            with tab3:
                st.subheader(f"{TRANS['chef_view_title']} ({view_date_str})")
                
                # --- 午餐留饭区域 ---
                st.markdown(f"### {TRANS['chef_lunch_sec']}")
                lunch_late_people = master[master['L_Status'].str.startswith("LATE")]
                if lunch_late_people.empty:
                    st.caption(TRANS["chef_empty"])
                else:
                    lunch_late_people['Time'] = lunch_late_people['L_Status'].apply(lambda x: x.split('_')[1] if '_' in x else 'Unknown')
                    l_grouped = lunch_late_people.groupby('Time')
                    for time_slot, group in l_grouped:
                        with st.container(border=True):
                            st.markdown(f"#### ⏰ {time_slot} {TRANS['chef_pickup']}")
                            st.warning(f"{TRANS['chef_total']} {len(group)} {TRANS['chef_people']}")
                            cols = st.columns(3)
                            for idx, (_, row) in enumerate(group.iterrows()):
                                cols[idx % 3].write(f"🏷️ **{row['name']}**")
                
                st.markdown("---")
                
                # --- 晚餐留饭区域 ---
                st.markdown(f"### {TRANS['chef_dinner_sec']}")
                dinner_late_people = master[master['D_Status'].str.startswith("LATE")]
                if dinner_late_people.empty:
                    st.caption(TRANS["chef_empty"])
                else:
                    dinner_late_people['Time'] = dinner_late_people['D_Status'].apply(lambda x: x.split('_')[1] if '_' in x else 'Unknown')
                    d_grouped = dinner_late_people.groupby('Time')
                    for time_slot, group in d_grouped:
                        with st.container(border=True):
                            st.markdown(f"#### ⏰ {time_slot} {TRANS['chef_pickup']}")
                            st.warning(f"{TRANS['chef_total']} {len(group)} {TRANS['chef_people']}")
                            cols = st.columns(3)
                            for idx, (_, row) in enumerate(group.iterrows()):
                                cols[idx % 3].write(f"🏷️ **{row['name']}**")

# ==========================================
# 6. 程序入口与 Cookie
# ==========================================
cookie_manager = stx.CookieManager(key="meal_app_auth")
cookies = cookie_manager.get_all()

def perform_login(phone, name):
    st.session_state.phone = phone
    st.session_state.user_name = name
    # 1. Cookie
    cookie_manager.set("auth_phone", phone, expires_at=datetime.now() + timedelta(days=30))
    # 2. URL 参数 (重要！这是桌面图标的关键)
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

# --- 自动登录决策 ---
if not st.session_state.phone:
    qp = st.query_params
    url_phone = qp.get("phone", None)
    cookie_phone = cookies.get("auth_phone") if cookies else None
    
    # 优先使用 URL 参数 (因为它不会被 iOS 沙盒隔离)
    target = url_phone if url_phone else cookie_phone
    
    if target:
        user = get_user_by_phone(target)
        if user is not None:
            st.session_state.phone = user['phone']
            st.session_state.user_name = user['name']
            
            # 查漏补缺
            if not url_phone: st.query_params["phone"] = user['phone']
            if not cookie_phone: cookie_manager.set("auth_phone", user['phone'], expires_at=datetime.now() + timedelta(days=30))
            st.rerun()

# --- 渲染路由 ---
if st.session_state.phone:
    # 强制锁定 URL，确保添加到桌面的链接永远是对的
    if st.query_params.get("phone") != st.session_state.phone:
        st.query_params["phone"] = st.session_state.phone

    c1, c2 = st.columns([3, 1])
    with c1:
        st.write(f"👋 {TRANS['welcome']}, **{st.session_state.user_name}**")
        st.caption(f"📱 {st.session_state.phone}")
    with c2:
        if st.button(TRANS["logout"]): perform_logout()
    
    # 顶部显眼提示
    st.markdown(f'<div class="link-box">{TRANS["ios_alert"]}</div>', unsafe_allow_html=True)
    
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
    
    # --- 午餐逻辑 (更新：加入留饭) ---
    with col1:
        with st.container(border=True):
            st.markdown(f"#### {TRANS['lunch']}")
            act_raw = get_status(st.session_state.phone, "Lunch", selected_date_str)
            current_status = resolve_meal_status(act_raw, is_sun)
            
            # 显示当前状态
            if current_status == "NORMAL": st.success(TRANS["status_eat"])
            elif current_status.startswith("LATE"): st.warning(f"{TRANS['status_late']} {current_status.split('_')[1]}")
            else: st.error(TRANS["status_no"])
            
            is_locked = False
            if is_today_selected and current_time > LUNCH_DEADLINE:
                is_locked = True
                
            if is_locked:
                st.caption(TRANS["locked"])
            else:
                # 只有当不是“不吃”状态时，才显示“不吃”按钮
                if current_status != "NO":
                     if st.button(TRANS["btn_no"], key="l_n", type="primary"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "CANCELED", selected_date_str); st.rerun()
                
                # 只有当不是“正常吃”状态时，才显示“我要吃”或“撤销”
                if current_status != "NORMAL":
                    if is_sun: # 周日默认不吃，显示我要吃
                        if st.button(TRANS["btn_eat"], key="l_e", type="primary"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "BOOKED", selected_date_str); st.rerun()
                    elif current_status == "NO": # 工作日且当前是不吃，显示撤销回到默认
                        if st.button(TRANS["btn_undo"], key="l_u"): update_order(st.session_state.phone, st.session_state.user_name, "Lunch", "DELETE", selected_date_str); st.rerun()

                st.markdown("---")
                # 午餐留饭区域
                st.write(f"**{TRANS['lbl_late_title']}**")
                # 生成午餐时间按钮
                cols = st.columns(len(LUNCH_LATE_OPTIONS))
                for idx, t_opt in enumerate(LUNCH_LATE_OPTIONS):
                    # 检查这个时间是否已被选中
                    is_active = (current_status == f"LATE_{t_opt}")
                    if cols[idx].button(t_opt, key=f"lunch_late_{t_opt}", disabled=is_active):
                         update_order(st.session_state.phone, st.session_state.user_name, "Lunch", f"LATE_{t_opt}", selected_date_str)
                         st.rerun()

    # --- 晚餐逻辑 (保持，仅引用新的翻译) ---
    with col2:
        with st.container(border=True):
            st.markdown(f"#### {TRANS['dinner']}")
            act_raw = get_status(st.session_state.phone, "Dinner", selected_date_str)
            current_status = resolve_meal_status(act_raw, is_sun)
            
            # 显示当前状态
            if current_status == "NORMAL": st.success(TRANS["status_eat"])
            elif current_status.startswith("LATE"): st.warning(f"{TRANS['status_late']} {current_status.split('_')[1]}")
            else: st.error(TRANS["status_no"])
            
            is_locked = False
            if is_today_selected and current_time > DINNER_DEADLINE:
                is_locked = True
            
            if is_locked:
                st.caption(TRANS["locked"])
            else:
                # 只有当不是“不吃”状态时，才显示“不吃”按钮
                if current_status != "NO":
                    if st.button(TRANS["btn_no"], key="d_n", type="primary"): 
                        update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "CANCELED", selected_date_str)
                        st.rerun()
                
                # 只有当不是“正常吃”状态时，才显示“我要吃”或“撤销”
                if current_status != "NORMAL":
                     if is_sun:
                         if st.button(TRANS["btn_eat"], key="d_e"): 
                             update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "BOOKED", selected_date_str)
                             st.rerun()
                     elif current_status == "NO": # 工作日且当前是不吃，显示撤销回到默认
                         if st.button(TRANS["btn_undo"], key="d_u"): 
                             update_order(st.session_state.phone, st.session_state.user_name, "Dinner", "DELETE", selected_date_str)
                             st.rerun()

                st.markdown("---")
                # 晚餐留饭区域
                st.write(f"**{TRANS['lbl_late_title']}**")
                # 生成晚餐时间按钮
                cols = st.columns(len(DINNER_LATE_OPTIONS))
                for idx, t_opt in enumerate(DINNER_LATE_OPTIONS):
                    # 检查这个时间是否已被选中
                    is_active = (current_status == f"LATE_{t_opt}")
                    if cols[idx].button(t_opt, key=f"late_{t_opt}", disabled=is_active):
                         update_order(st.session_state.phone, st.session_state.user_name, "Dinner", f"LATE_{t_opt}", selected_date_str)
                         st.rerun()

    st.markdown("---")
    with st.expander(TRANS["help_title"]): st.info(TRANS["help_txt"])
    render_admin_panel()

else:
    # 登录前
    render_login()
    render_admin_panel()
