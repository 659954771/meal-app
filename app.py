import streamlit as st
import pandas as pd
import os
from datetime import datetime, time

# ==========================================
# 1. 配置与初始化 / Configuration & Init
# ==========================================
st.set_page_config(page_title="工厂报餐系统 / စက်ရုံထမင်းစားစာရင်း", page_icon="🍚")

USERS_FILE = 'users.csv'
ORDERS_FILE = 'orders.csv'

# 缅甸语翻译字典 / Burmese Translations
TRANS = {
    "login_title": "请输入手机号 / ဖုန်းနံပါတ်ထည့်ပါ",
    "phone_placeholder": "例如: 0812345678",
    "new_user_title": "第一次使用，请输入名字 / နာမည်ထည့်ပါ",
    "name_placeholder": "名字 / နာမည်",
    "register_btn": "注册并登录 / စာရင်းသွင်းပြီး ဝင်ပါ",
    "welcome": "欢迎 / ကြိုဆိုပါတယ်",
    "logout": "退出 / ထွက်ရန်",
    "sunday_header": "📅 今天是周日 (Sunday) / ဒီနေ့ တနင်္ဂနွေနေ့",
    "sunday_rule": "⚠️ 规则：要吃饭请点击“我要吃” / စည်းကမ်းချက် - စားလိုလျှင် 'စားမည်' ကိုနှိပ်ပါ",
    "weekday_header": "📅 今天是工作日 (Weekday) / ဒီနေ့ အလုပ်ဖွင့်ရက်",
    "weekday_rule": "⚠️ 规则：默认吃饭。如果不吃，请点击“我不吃” / ပုံမှန်စားရမည်။ မစားလိုပါက 'မစားပါ' ကိုနှိပ်ပါ",
    "lunch": "午餐 / နေ့လည်စာ",
    "dinner": "晚餐 / ညစာ",
    "eat_btn": "我要吃 / စားမယ် (Eat)",
    "not_eat_btn": "我不吃 / မစားဘူး (Not Eat)",
    "undo_btn": "重新吃饭 / ပြန်စားမယ် (Undo)",
    "booked_msg": "✅ 已预订 / မှာပြီးပါပြီ",
    "canceled_msg": "🚫 已取消 / မစားပါ",
    "default_eat_msg": "✅ 状态：默认吃饭 / အခြေအနေ - ပုံမှန်စားမည်",
    "deadline_msg": "❌ 已截止 / အချိန်ကုန်သွားပြီ",
    "admin_header": "今日统计 / ယနေ့စာရင်း (Admin)",
    "total_users": "总人数 / စုစုပေါင်း",
    "lunch_count": "午餐人数 / နေ့လည်စာ စားမည့်သူ",
    "dinner_count": "晚餐人数 / ညစာ စားမည့်သူ",
    "not_eat_list": "不吃名单 / မစားမည့်သူစာရင်း"
}

def init_db():
    """初始化CSV文件"""
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["phone", "name", "reg_date"]).to_csv(USERS_FILE, index=False)
    
    if not os.path.exists(ORDERS_FILE):
        pd.DataFrame(columns=["date", "phone", "name", "meal_type", "action", "time"]).to_csv(ORDERS_FILE, index=False)

init_db()

# ==========================================
# 2. 数据操作函数 / Data Functions
# ==========================================
def get_user(phone):
    """查找用户"""
    try:
        # 强制将 phone 读取为字符串，防止类型错误
        df = pd.read_csv(USERS_FILE, dtype={'phone': str})
        user = df[df['phone'] == str(phone)]
        return user.iloc[0] if not user.empty else None
    except Exception:
        return None

def register_user(phone, name):
    """注册用户"""
    # 强制将 phone 读取为字符串
    df = pd.read_csv(USERS_FILE, dtype={'phone': str})
    new_user = pd.DataFrame([[str(phone), name, datetime.now().strftime("%Y-%m-%d")]], 
                            columns=["phone", "name", "reg_date"])
    # 简单的防止重复注册逻辑
    if str(phone) not in df['phone'].values:
        new_df = pd.concat([df, new_user], ignore_index=True)
        new_df.to_csv(USERS_FILE, index=False)
    return True

def save_order(phone, name, meal_type, action):
    """保存报餐记录"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    
    # 强制读取 phone 为字符串
    df = pd.read_csv(ORDERS_FILE, dtype={'phone': str})
    
    # 移除该用户今天该餐次的旧记录 (覆盖模式)
    df = df[~((df['date'] == date_str) & (df['phone'] == str(phone)) & (df['meal_type'] == meal_type))]
    
    # 添加新记录
    new_record = pd.DataFrame([[date_str, str(phone), name, meal_type, action, time_str]], 
                              columns=["date", "phone", "name", "meal_type", "action", "time"])
    df = pd.concat([df, new_record], ignore_index=True)
    df.to_csv(ORDERS_FILE, index=False)

def delete_order(phone, meal_type):
    """删除今日某餐的记录 (用于反悔/Undo)"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    # 强制读取 phone 为字符串
    df = pd.read_csv(ORDERS_FILE, dtype={'phone': str})
    
    # 删除匹配的行
    df = df[~((df['date'] == date_str) & (df['phone'] == str(phone)) & (df['meal_type'] == meal_type))]
    df.to_csv(ORDERS_FILE, index=False)

def get_order_status(phone, meal_type):
    """获取今日状态: 'BOOKED', 'CANCELED', or None"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    # 强制读取 phone 为字符串
    df = pd.read_csv(ORDERS_FILE, dtype={'phone': str})
    record = df[(df['date'] == date_str) & (df['phone'] == str(phone)) & (df['meal_type'] == meal_type)]
    if not record.empty:
        return record.iloc[-1]['action'] # 返回最后一条操作
    return None

def get_total_users_count():
    # 强制读取 phone 为字符串
    df = pd.read_csv(USERS_FILE, dtype={'phone': str})
    return len(df)

def get_daily_stats(is_sunday):
    date_str = datetime.now().strftime("%Y-%m-%d")
    # 强制读取 phone 为字符串
    orders = pd.read_csv(ORDERS_FILE, dtype={'phone': str})
    today_orders = orders[orders['date'] == date_str]
    
    total_users = get_total_users_count()
    
    stats = {"lunch": 0, "dinner": 0, "lunch_not_eat_list": [], "dinner_not_eat_list": []}
    
    if is_sunday:
        # 周日：只算 BOOKED
        stats["lunch"] = len(today_orders[(today_orders['meal_type'] == 'Lunch') & (today_orders['action'] == 'BOOKED')])
        stats["dinner"] = len(today_orders[(today_orders['meal_type'] == 'Dinner') & (today_orders['action'] == 'BOOKED')])
    else:
        # 工作日：总人数 - CANCELED
        lunch_canceled = today_orders[(today_orders['meal_type'] == 'Lunch') & (today_orders['action'] == 'CANCELED')]
        dinner_canceled = today_orders[(today_orders['meal_type'] == 'Dinner') & (today_orders['action'] == 'CANCELED')]
        
        stats["lunch"] = total_users - len(lunch_canceled)
        stats["dinner"] = total_users - len(dinner_canceled)
        
        stats["lunch_not_eat_list"] = lunch_canceled[['name', 'time']]
        stats["dinner_not_eat_list"] = dinner_canceled[['name', 'time']]
        
    return stats

# ==========================================
# 3. 页面逻辑 / UI Logic
# ==========================================

# Session State 初始化
if 'phone' not in st.session_state:
    st.session_state.phone = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# --- A. 登录页面 (Login) ---
if st.session_state.phone is None:
    st.title("🏭 工厂报餐 / စက်ရုံထမင်းစားစာရင်း")
    
    phone_input = st.text_input(TRANS["login_title"], placeholder=TRANS["phone_placeholder"])
    
    if st.button("下一步 / ရှေ့ဆက်ရန်", type="primary", use_container_width=True):
        if phone_input:
            user = get_user(phone_input)
            if user is not None:
                # 老用户登录
                st.session_state.phone = user['phone']
                st.session_state.user_name = user['name']
                st.rerun()
            else:
                # 标记需要注册
                st.session_state.temp_phone = phone_input
    
    # 注册逻辑
    if 'temp_phone' in st.session_state:
        st.info(TRANS["new_user_title"])
        name_input = st.text_input(TRANS["name_placeholder"])
        
        if st.button(TRANS["register_btn"], type="primary", use_container_width=True):
            if name_input:
                register_user(st.session_state.temp_phone, name_input)
                st.session_state.phone = st.session_state.temp_phone
                st.session_state.user_name = name_input
                del st.session_state.temp_phone
                st.rerun()

# --- B. 主界面 (Dashboard) ---
else:
    # 顶部栏
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{TRANS['welcome']}, {st.session_state.user_name}")
    with col2:
        if st.button(TRANS['logout']):
            st.session_state.phone = None
            st.session_state.user_name = None
            st.rerun()
    
    st.divider()
    
    # 时间逻辑
    now = datetime.now()
    weekday = now.weekday() # 0=Mon, 6=Sun
    current_time = now.time()
    is_sunday = (weekday == 6)
    
    # ----------------------------------
    # 场景 A: 周日 (Opt-in)
    # ----------------------------------
    if is_sunday:
        st.info(TRANS["sunday_header"])
        st.warning(TRANS["sunday_rule"])
        
        col_l, col_d = st.columns(2)
        
        # --- 周日午餐 ---
        with col_l:
            st.write(f"### {TRANS['lunch']}")
            status = get_order_status(st.session_state.phone, "Lunch")
            
            if status == "BOOKED":
                st.success(TRANS["booked_msg"])
            else:
                if current_time < time(9, 0): # 9:00 AM 截止
                    if st.button(f"{TRANS['eat_btn']} 🍛", key="sun_lunch", type="primary", use_container_width=True):
                        save_order(st.session_state.phone, st.session_state.user_name, "Lunch", "BOOKED")
                        st.rerun()
                else:
                    st.error(TRANS["deadline_msg"])

        # --- 周日晚餐 ---
        with col_d:
            st.write(f"### {TRANS['dinner']}")
            status = get_order_status(st.session_state.phone, "Dinner")
            
            if status == "BOOKED":
                st.success(TRANS["booked_msg"])
            else:
                if current_time < time(15, 0): # 15:00 PM 截止
                    if st.button(f"{TRANS['eat_btn']} 🍜", key="sun_dinner", type="primary", use_container_width=True):
                        save_order(st.session_state.phone, st.session_state.user_name, "Dinner", "BOOKED")
                        st.rerun()
                else:
                    st.error(TRANS["deadline_msg"])

    # ----------------------------------
    # 场景 B: 周一至周六 (Opt-out)
    # ----------------------------------
    else:
        st.success(TRANS["weekday_header"])
        st.warning(TRANS["weekday_rule"])
        
        col_l, col_d = st.columns(2)
        
        # --- 工作日午餐 ---
        with col_l:
            st.write(f"### {TRANS['lunch']}")
            status = get_order_status(st.session_state.phone, "Lunch")
            
            if status == "CANCELED":
                st.error(TRANS["canceled_msg"])
                # 反悔功能：删除 'CANCELED' 记录，恢复默认吃饭状态
                if st.button(TRANS["undo_btn"], key="undo_lunch"):
                     delete_order(st.session_state.phone, "Lunch")
                     st.rerun()
            else:
                st.caption(TRANS["default_eat_msg"])
                # 也可以加上截止时间判断，如果需要的话
                if st.button(f"{TRANS['not_eat_btn']} 🙅‍♂️", key="wd_lunch", type="primary", use_container_width=True):
                    save_order(st.session_state.phone, st.session_state.user_name, "Lunch", "CANCELED")
                    st.rerun()

        # --- 工作日晚餐 ---
        with col_d:
            st.write(f"### {TRANS['dinner']}")
            status = get_order_status(st.session_state.phone, "Dinner")
            
            if status == "CANCELED":
                st.error(TRANS["canceled_msg"])
                # 反悔功能：删除 'CANCELED' 记录，恢复默认吃饭状态
                if st.button(TRANS["undo_btn"], key="undo_dinner"):
                     delete_order(st.session_state.phone, "Dinner")
                     st.rerun()
            else:
                st.caption(TRANS["default_eat_msg"])
                if st.button(f"{TRANS['not_eat_btn']} 🙅‍♂️", key="wd_dinner", type="primary", use_container_width=True):
                    save_order(st.session_state.phone, st.session_state.user_name, "Dinner", "CANCELED")
                    st.rerun()

    # ==========================================
    # 4. 管理员统计区域 / Admin Stats
    # ==========================================
    st.divider()
    with st.expander(TRANS["admin_header"]):
        stats = get_daily_stats(is_sunday)
        
        st.metric(TRANS["total_users"], get_total_users_count())
        
        c1, c2 = st.columns(2)
        c1.metric(TRANS["lunch_count"], f"{stats['lunch']} 人")
        c2.metric(TRANS["dinner_count"], f"{stats['dinner']} 人")
        
        if not is_sunday:
            st.write("---")
            st.write(f"❌ {TRANS['lunch']} - {TRANS['not_eat_list']}")
            if not stats['lunch_not_eat_list'].empty:
                st.dataframe(stats['lunch_not_eat_list'], use_container_width=True)
            else:
                st.caption("无 / မရှိပါ")
                
            st.write(f"❌ {TRANS['dinner']} - {TRANS['not_eat_list']}")
            if not stats['dinner_not_eat_list'].empty:
                st.dataframe(stats['dinner_not_eat_list'], use_container_width=True)
            else:
                st.caption("无 / မရှိပါ")