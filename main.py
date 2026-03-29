"""
智能计薪系统 - Android App
基于 Flask Web 版的完整复刻
"""
import os
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
import calendar

Window.softinput_mode = 'below_target'

# ===== 数据库 =====
DB_PATH = os.path.join(os.path.dirname(__file__), 'salary.db')

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        is_admin INTEGER DEFAULT 0,
        salary_type TEXT DEFAULT 'monthly',
        base_salary REAL DEFAULT 10000,
        hourly_rate REAL DEFAULT 50,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS work_hours (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        work_date DATE NOT NULL,
        hours REAL DEFAULT 0,
        day_type TEXT DEFAULT 'normal',
        remark TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, work_date)
    );
    
    CREATE TABLE IF NOT EXISTS punch_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        punch_date DATE NOT NULL,
        punch_order INTEGER NOT NULL,
        punch_time TIME NOT NULL,
        status TEXT DEFAULT 'normal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    
    CREATE TABLE IF NOT EXISTS special_dates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE UNIQUE NOT NULL,
        date_type TEXT DEFAULT 'holiday',
        name TEXT
    );
    
    INSERT OR IGNORE INTO system_config (key, value) VALUES 
        ('overtime_rate', '1.5'),
        ('weekend_rate', '2.0'),
        ('holiday_rate', '3.0'),
        ('work_days_per_month', '22'),
        ('hours_per_day', '8');
    
    -- 创建默认管理员
    INSERT OR IGNORE INTO users (username, password, is_admin) 
        VALUES ('admin', 'admin123', 1);
    ''')
    conn.commit()
    conn.close()

# ===== 工具函数 =====
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def calc_salary(user_id, year, month):
    """计算薪资"""
    conn = get_db()
    c = conn.cursor()
    
    # 获取配置
    config = {k: v for k, v in c.execute("SELECT key, value FROM system_config")}
    rates = {
        'overtime': float(config.get('overtime_rate', '1.5')),
        'weekend': float(config.get('weekend_rate', '2.0')),
        'holiday': float(config.get('holiday_rate', '3.0')),
    }
    work_days_month = int(config.get('work_days_per_month', '22'))
    hours_day = float(config.get('hours_per_day', '8'))
    
    # 获取用户时薪
    user = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user[4] == 'monthly':  # salary_type
        hourly = user[5] / work_days_month / hours_day  # base_salary
    else:
        hourly = user[6]  # hourly_rate
    
    # 获取工时记录
    records = c.execute('''
        SELECT * FROM work_hours WHERE user_id = ? 
        AND strftime('%Y', work_date) = ? 
        AND strftime('%m', work_date) = ?
        ORDER BY work_date
    ''', (user_id, str(year), f'{month:02d}')).fetchall()
    
    # 统计工时
    normal_hours = overtime_hours = weekend_hours = holiday_hours = 0
    work_days = weekend_days = holiday_days = 0
    
    for r in records:
        if r[3] > 0:  # hours
            if r[4] == 'normal':  # day_type
                normal_hours += min(r[3], hours_day)
                overtime_hours += max(0, r[3] - hours_day)
                work_days += 1
            elif r[4] == 'weekend':
                weekend_hours += r[3]
                weekend_days += 1
            else:
                holiday_hours += r[3]
                holiday_days += 1
    
    # 计算工资
    base_pay = hourly * normal_hours
    overtime_pay = hourly * overtime_hours * rates['overtime']
    weekend_pay = hourly * weekend_hours * rates['weekend']
    holiday_pay = hourly * holiday_hours * rates['holiday']
    total = base_pay + overtime_pay + weekend_pay + holiday_pay
    
    conn.close()
    return {
        'hourly': hourly,
        'hours_day': hours_day,
        'rates': rates,
        'normal_hours': normal_hours,
        'overtime_hours': overtime_hours,
        'weekend_hours': weekend_hours,
        'holiday_hours': holiday_hours,
        'work_days': work_days,
        'weekend_days': weekend_days,
        'holiday_days': holiday_days,
        'base_pay': base_pay,
        'overtime_pay': overtime_pay,
        'weekend_pay': weekend_pay,
        'holiday_pay': holiday_pay,
        'total': total,
    }

# ===== KV 布局 =====
KV = '''
<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20
        canvas.before:
            Color:
                rgba: 0.12, 0.12, 0.18, 1
            Rectangle:
                pos: self.pos
                size: self.size
        
        Label:
            text: '智能计薪系统'
            font_size: 32
            size_hint_y: None
            height: 60
            color: 0.3, 0.7, 1, 1
        
        TextInput:
            id: username
            hint_text: '用户名'
            multiline: False
            size_hint_y: None
            height: 50
            font_size: 18
        
        TextInput:
            id: password
            hint_text: '密码'
            multiline: False
            password: True
            size_hint_y: None
            height: 50
            font_size: 18
        
        Button:
            text: '登录'
            size_hint_y: None
            height: 50
            background_color: 0.2, 0.6, 0.9, 1
            on_press: root.do_login()
        
        Button:
            text: '注册'
            size_hint_y: None
            height: 50
            background_color: 0.3, 0.8, 0.4, 1
            on_press: root.go_register()

<RegisterScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20
        canvas.before:
            Color:
                rgba: 0.12, 0.12, 0.18, 1
            Rectangle:
                pos: self.pos
                size: self.size
        
        Label:
            text: '注册账号'
            font_size: 28
            size_hint_y: None
            height: 50
            color: 0.3, 0.7, 1, 1
        
        TextInput:
            id: reg_username
            hint_text: '用户名'
            multiline: False
            size_hint_y: None
            height: 50
            font_size: 18
        
        TextInput:
            id: reg_email
            hint_text: '邮箱'
            multiline: False
            size_hint_y: None
            height: 50
            font_size: 18
        
        TextInput:
            id: reg_password
            hint_text: '密码'
            multiline: False
            password: True
            size_hint_y: None
            height: 50
            font_size: 18
        
        TextInput:
            id: reg_salary
            hint_text: '月薪 (默认10000)'
            multiline: False
            input_type: 'number'
            size_hint_y: None
            height: 50
            font_size: 18
        
        Button:
            text: '注册'
            size_hint_y: None
            height: 50
            background_color: 0.3, 0.8, 0.4, 1
            on_press: root.do_register()
        
        Button:
            text: '返回登录'
            size_hint_y: None
            height: 50
            background_color: 0.6, 0.6, 0.6, 1
            on_press: root.go_login()

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10
        canvas.before:
            Color:
                rgba: 0.15, 0.15, 0.22, 1
            Rectangle:
                pos: self.pos
                size: self.size
        
        # 顶部标题栏
        BoxLayout:
            size_hint_y: None
            height: 50
            spacing: 10
            padding: 5
            Label:
                text: '智能计薪系统'
                font_size: 22
                color: 0.3, 0.7, 1, 1
            Button:
                text: '退出'
                size_hint_x: None
                width: 80
                background_color: 0.9, 0.3, 0.3, 1
                on_press: root.logout()
        
        # 功能按钮区
        GridLayout:
            cols: 2
            spacing: 10
            size_hint_y: 0.25
            Button:
                text: '仪表盘'
                background_color: 0.2, 0.6, 0.9, 1
                on_press: root.show_dashboard()
            Button:
                text: '打卡'
                background_color: 0.3, 0.8, 0.4, 1
                on_press: root.show_punch()
            Button:
                text: '工时录入'
                background_color: 0.9, 0.7, 0.2, 1
                on_press: root.show_work_hours()
            Button:
                text: '工资查看'
                background_color: 0.8, 0.4, 0.7, 1
                on_press: root.show_salary()
        
        # 内容区域
        ScrollView:
            id: content_area
            size_hint_y: 0.7

<DashboardWidget>:
    orientation: 'vertical'
    padding: 15
    spacing: 10

<WorkHoursWidget>:
    orientation: 'vertical'
    padding: 15
    spacing: 10

<PunchWidget>:
    orientation: 'vertical'
    padding: 15
    spacing: 10

<SalaryWidget>:
    orientation: 'vertical'
    padding: 15
    spacing: 10
'''

# ===== 屏幕类 =====
class LoginScreen(Screen):
    def do_login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text.strip()
        if not username or not password:
            self.show_error('请输入用户名和密码')
            return
        
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password))
        ).fetchone()
        conn.close()
        
        if user:
            app = App.get_running_app()
            app.user_id = user[0]
            app.username = user[1]
            app.is_admin = bool(user[4])
            app.root.current = 'main'
            self.ids.username.text = ''
            self.ids.password.text = ''
        else:
            self.show_error('用户名或密码错误')
    
    def go_register(self):
        self.manager.current = 'register'
    
    def show_error(self, msg):
        Popup(title='提示', content=Label(text=msg),
              size_hint=(0.8, 0.3)).open()

class RegisterScreen(Screen):
    def do_register(self):
        username = self.ids.reg_username.text.strip()
        email = self.ids.reg_email.text.strip()
        password = self.ids.reg_password.text.strip()
        salary = self.ids.reg_salary.text.strip() or '10000'
        
        if not username or not password:
            self.show_error('请填写用户名和密码')
            return
        
        if len(password) < 6:
            self.show_error('密码至少6位')
            return
        
        try:
            conn = get_db()
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                self.show_error('用户名已存在')
                conn.close()
                return
            
            conn.execute('''
                INSERT INTO users (username, password, email, base_salary)
                VALUES (?, ?, ?, ?)
            ''', (username, hash_password(password), email, float(salary)))
            conn.commit()
            conn.close()
            
            self.show_success('注册成功！请登录')
            self.manager.current = 'login'
            self.clear_inputs()
        except Exception as e:
            self.show_error(f'注册失败: {e}')
    
    def go_login(self):
        self.manager.current = 'login'
    
    def clear_inputs(self):
        self.ids.reg_username.text = ''
        self.ids.reg_email.text = ''
        self.ids.reg_password.text = ''
        self.ids.reg_salary.text = ''
    
    def show_error(self, msg):
        Popup(title='错误', content=Label(text=msg),
              size_hint=(0.8, 0.3)).open()
    
    def show_success(self, msg):
        Popup(title='成功', content=Label(text=msg),
              size_hint=(0.8, 0.3)).open()

class MainScreen(Screen):
    current_widget = None
    
    def on_enter(self):
        self.show_dashboard()
    
    def show_dashboard(self):
        self.clear_content()
        self.current_widget = DashboardWidget(user_id=app.user_id, username=app.username)
        self.ids.content_area.clear_widgets()
        self.ids.content_area.add_widget(self.current_widget)
    
    def show_punch(self):
        self.clear_content()
        self.current_widget = PunchWidget(user_id=app.user_id)
        self.ids.content_area.clear_widgets()
        self.ids.content_area.add_widget(self.current_widget)
    
    def show_work_hours(self):
        self.clear_content()
        self.current_widget = WorkHoursWidget(user_id=app.user_id)
        self.ids.content_area.clear_widgets()
        self.ids.content_area.add_widget(self.current_widget)
    
    def show_salary(self):
        self.clear_content()
        self.current_widget = SalaryWidget(user_id=app.user_id)
        self.ids.content_area.clear_widgets()
        self.ids.content_area.add_widget(self.current_widget)
    
    def clear_content(self):
        self.ids.content_area.clear_widgets()
    
    def logout(self):
        app = App.get_running_app()
        app.user_id = None
        app.username = None
        self.manager.current = 'login'

class DashboardWidget(BoxLayout):
    def __init__(self, user_id, username, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.username = username
        self.orientation = 'vertical'
        self.spacing = 15
        self.build()
    
    def build(self):
        today = date.today()
        salary = calc_salary(self.user_id, today.year, today.month)
        
        # 欢迎信息
        self.add_widget(Label(
            text=f'欢迎回来, {self.username}',
            font_size=24, size_hint_y=None, height=40,
            color=0.3, 0.7, 1, 1
        ))
        
        # 今日日期
        self.add_widget(Label(
            text=f'今天是 {today.strftime("%Y年%m月%d日")}',
            font_size=16, size_hint_y=None, height=30
        ))
        
        # 本月统计卡片
        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        cards = [
            ('工作天数', f'{salary["work_days"]} 天'),
            ('工时总计', f'{salary["normal_hours"]:.1f} 小时'),
            ('加班工时', f'{salary["overtime_hours"]:.1f} 小时'),
            ('本月工资', f'¥{salary["total"]:.2f}'),
        ]
        for title, value in cards:
            card = BoxLayout(orientation='vertical', padding=10,
                           canvas.before=lambda c: setattr(c.before, 'rgba', (0.2, 0.2, 0.3, 1)))
            card.add_widget(Label(text=title, font_size=14, color=0.7, 0.7, 0.7, 1))
            card.add_widget(Label(text=value, font_size=20, color=0.3, 0.9, 0.5, 1))
            grid.add_widget(card)
        
        self.add_widget(grid)
        
        # 工资详情
        detail_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        detail_box.bind(minimum_height=detail_box.setter('height'))
        
        self.add_widget(Label(text='工资构成', font_size=18, size_hint_y=None, height=35))
        
        items = [
            ('基础工资', f'¥{salary["base_pay"]:.2f}'),
            ('加班工资', f'¥{salary["overtime_pay"]:.2f}'),
            ('周末工资', f'¥{salary["weekend_pay"]:.2f}'),
            ('节假日工资', f'¥{salary["holiday_pay"]:.2f}'),
            ('时薪', f'¥{salary["hourly"]:.2f}/小时'),
        ]
        for label_text, value_text in items:
            row = BoxLayout(size_hint_y=None, height=30)
            row.add_widget(Label(text=label_text, halign='left', size_hint_x=0.5))
            row.add_widget(Label(text=value_text, halign='right', size_hint_x=0.5))
            detail_box.add_widget(row)
        
        self.add_widget(detail_box)

class PunchWidget(BoxLayout):
    punch_times = [
        (1, '上午上班', '08:00', '09:30'),
        (2, '下午上班', '12:30', '14:00'),
        (3, '晚班上班', '17:30', '19:00'),
        (4, '上午下班', '11:30', '13:00'),
        (5, '下午下班', '17:00', '18:30'),
        (6, '晚班下班', '21:00', '23:00'),
    ]
    
    def __init__(self, user_id, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.orientation = 'vertical'
        self.spacing = 15
        self.build()
    
    def build(self):
        today = date.today()
        now = datetime.now()
        
        self.add_widget(Label(
            text=f'{today.strftime("%Y年%m月%d日")} 打卡',
            font_size=22, size_hint_y=None, height=45,
            color=0.3, 0.7, 1, 1
        ))
        
        # 今日打卡状态
        conn = get_db()
        punches = conn.execute(
            'SELECT punch_order FROM punch_records WHERE user_id = ? AND punch_date = ?',
            (self.user_id, today.isoformat())
        ).fetchall()
        punched_orders = {p[0] for p in punches}
        conn.close()
        
        grid = GridLayout(cols=2, spacing=10)
        grid.bind(minimum_height=grid.setter('height'))
        
        for order, name, start, end in self.punch_times:
            is_punched = order in punched_orders
            btn = Button(
                text=f'{name}\n{start}-{end}',
                background_color=(0.3, 0.8, 0.3, 1) if is_punched else (0.5, 0.5, 0.5, 1),
                on_press=lambda _, o=order, n=name: self.do_punch(o, n)
            )
            if is_punched:
                btn.text = f'{name}\n[已打卡]'
            grid.add_widget(btn)
        
        self.add_widget(grid)
        
        # 打卡按钮
        punch_btn = Button(
            text='签到/签退',
            size_hint_y=None,
            height=60,
            background_color=0.2, 0.6, 0.9, 1,
            on_press=self.do_punch_dialog
        )
        self.add_widget(punch_btn)
    
    def do_punch(self, order, name):
        today = date.today()
        now = datetime.now().time()
        
        conn = get_db()
        existing = conn.execute(
            'SELECT id FROM punch_records WHERE user_id = ? AND punch_date = ? AND punch_order = ?',
            (self.user_id, today.isoformat(), order)
        ).fetchone()
        
        if existing:
            conn.close()
            self.show_msg(f'{name} 已打卡')
            return
        
        conn.execute(
            'INSERT INTO punch_records (user_id, punch_date, punch_order, punch_time, status) VALUES (?, ?, ?, ?, ?)',
            (self.user_id, today.isoformat(), order, now.strftime('%H:%M:%S'), 'normal')
        )
        conn.commit()
        conn.close()
        
        self.show_msg(f'{name} 打卡成功!')
        self.build()
    
    def do_punch_dialog(self, *args):
        self.show_msg('请在上面的时间卡片点击打卡')
    
    def show_msg(self, msg):
        Popup(title='打卡提示', content=Label(text=msg),
              size_hint=(0.8, 0.3)).open()

class WorkHoursWidget(BoxLayout):
    def __init__(self, user_id, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.orientation = 'vertical'
        self.spacing = 10
        self.year = date.today().year
        self.month = date.today().month
        self.build()
    
    def build(self):
        self.clear_widgets()
        
        # 月份选择
        month_bar = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        prev_btn = Button(text='<', size_hint_x=None, width=50,
                         on_press=lambda _: self.change_month(-1))
        self.month_label = Label(text=f'{self.year}年{self.month:02d}月', font_size=20)
        next_btn = Button(text='>', size_hint_x=None, width=50,
                         on_press=lambda _: self.change_month(1))
        
        month_bar.add_widget(prev_btn)
        month_bar.add_widget(self.month_label)
        month_bar.add_widget(next_btn)
        self.add_widget(month_bar)
        
        # 日历
        calendar_grid = self.create_calendar()
        scroll = ScrollView(size_hint_y=0.6)
        scroll.add_widget(calendar_grid)
        self.add_widget(scroll)
        
        # 录入区域
        self.add_widget(Label(text='录入/修改工时', font_size=16, size_hint_y=None, height=30))
        
        input_box = GridLayout(cols=3, spacing=5, size_hint_y=None, height=120)
        
        self.date_input = TextInput(hint_text='日期 (YYYY-MM-DD)', multiline=False,
                                    size_hint_y=None, height=40)
        self.hours_input = TextInput(hint_text='工时', multiline=False,
                                     input_type='number', size_hint_y=None, height=40)
        
        self.day_type_spinner = Spinner(
            text='normal',
            values=['normal', 'weekend', 'holiday'],
            size_hint_y=None, height=40
        )
        
        save_btn = Button(text='保存', background_color=0.2, 0.7, 0.3, 1,
                         on_press=self.save_record)
        input_box.add_widget(self.date_input)
        input_box.add_widget(self.hours_input)
        input_box.add_widget(self.day_type_spinner)
        input_box.add_widget(save_btn)
        
        self.add_widget(input_box)
    
    def create_calendar(self):
        grid = GridLayout(cols=7, spacing=2)
        grid.bind(minimum_height=grid.setter('height'))
        
        # 表头
        for day in ['日', '一', '二', '三', '四', '五', '六']:
            grid.add_widget(Label(text=day, size_hint_y=None, height=30,
                                 color=0.3, 0.7, 1, 1))
        
        # 获取数据
        conn = get_db()
        records = conn.execute('''
            SELECT work_date, hours, day_type FROM work_hours
            WHERE user_id = ? AND strftime('%Y', work_date) = ? AND strftime('%m', work_date) = ?
        ''', (self.user_id, str(self.year), f'{self.month:02d}')).fetchall()
        record_dict = {r[0]: r for r in records}
        conn.close()
        
        first_day, days = calendar.monthrange(self.year, self.month)
        
        # 空白
        for _ in range(first_day):
            grid.add_widget(Label(text=''))
        
        today = date.today()
        
        # 日期
        for d in range(1, days + 1):
            dt = f'{self.year}-{self.month:02d}-{d:02d}'
            record = record_dict.get(dt)
            
            if record:
                hours, day_type = record[1], record[2]
                if day_type == 'weekend':
                    color = (0.9, 0.7, 0.2, 1)
                elif day_type == 'holiday':
                    color = (0.9, 0.4, 0.4, 1)
                else:
                    color = (0.2, 0.7, 0.3, 1)
                text = f'{d}\n{hours:.1f}h'
            else:
                color = (0.3, 0.3, 0.4, 1)
                text = str(d)
            
            day_label = Label(text=text, color=color)
            grid.add_widget(day_label)
        
        return grid
    
    def change_month(self, delta):
        self.month += delta
        if self.month > 12:
            self.month = 1
            self.year += 1
        elif self.month < 1:
            self.month = 12
            self.year -= 1
        self.build()
    
    def save_record(self, *args):
        work_date = self.date_input.text.strip()
        hours = self.hours_input.text.strip()
        day_type = self.day_type_spinner.text
        
        if not work_date or not hours:
            self.show_msg('请填写日期和工时')
            return
        
        try:
            hours = float(hours)
            conn = get_db()
            
            existing = conn.execute(
                'SELECT id FROM work_hours WHERE user_id = ? AND work_date = ?',
                (self.user_id, work_date)
            ).fetchone()
            
            if existing:
                conn.execute(
                    'UPDATE work_hours SET hours = ?, day_type = ? WHERE user_id = ? AND work_date = ?',
                    (hours, day_type, self.user_id, work_date)
                )
            else:
                conn.execute(
                    'INSERT INTO work_hours (user_id, work_date, hours, day_type) VALUES (?, ?, ?, ?)',
                    (self.user_id, work_date, hours, day_type)
                )
            
            conn.commit()
            conn.close()
            
            self.show_msg('保存成功!')
            self.date_input.text = ''
            self.hours_input.text = ''
            self.build()
        except Exception as e:
            self.show_msg(f'保存失败: {e}')
    
    def show_msg(self, msg):
        Popup(title='提示', content=Label(text=msg),
              size_hint=(0.8, 0.3)).open()

class SalaryWidget(BoxLayout):
    def __init__(self, user_id, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.orientation = 'vertical'
        self.spacing = 10
        self.year = date.today().year
        self.month = date.today().month
        self.build()
    
    def build(self):
        self.clear_widgets()
        
        # 月份选择
        month_bar = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        prev_btn = Button(text='<', size_hint_x=None, width=50,
                         on_press=lambda _: self.change_month(-1))
        self.month_label = Label(text=f'{self.year}年{self.month:02d}月', font_size=20)
        next_btn = Button(text='>', size_hint_x=None, width=50,
                         on_press=lambda _: self.change_month(1))
        
        month_bar.add_widget(prev_btn)
        month_bar.add_widget(self.month_label)
        month_bar.add_widget(next_btn)
        self.add_widget(month_bar)
        
        # 工资数据
        salary = calc_salary(self.user_id, self.year, self.month)
        
        # 总工资卡片
        total_card = BoxLayout(orientation='vertical', padding=20,
                              canvas.before=lambda c: setattr(c.before, 'rgba', (0.2, 0.6, 0.9, 0.3)))
        total_card.add_widget(Label(text='本月工资', font_size=18))
        total_card.add_widget(Label(text=f'¥{salary["total"]:.2f}', font_size=36,
                                   color=0.3, 0.9, 0.5, 1))
        self.add_widget(total_card)
        
        # 明细
        detail_grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        detail_grid.bind(minimum_height=detail_grid.setter('height'))
        
        items = [
            ('基础工资', f'¥{salary["base_pay"]:.2f}'),
            ('加班工资', f'¥{salary["overtime_pay"]:.2f}'),
            ('周末工资', f'¥{salary["weekend_pay"]:.2f}'),
            ('节假日工资', f'¥{salary["holiday_pay"]:.2f}'),
            ('工作天数', f'{salary["work_days"]} 天'),
            ('加班工时', f'{salary["overtime_hours"]:.1f} 小时'),
            ('周末天数', f'{salary["weekend_days"]} 天'),
            ('节假日天数', f'{salary["holiday_days"]} 天'),
            ('时薪', f'¥{salary["hourly"]:.2f}'),
            ('日工时', f'{salary["hours_day"]:.0f} 小时'),
        ]
        
        for label_text, value_text in items:
            card = BoxLayout(orientation='vertical', padding=10,
                           canvas.before=lambda c: setattr(c.before, 'rgba', (0.2, 0.2, 0.3, 1)))
            card.add_widget(Label(text=label_text, font_size=14, color=0.7, 0.7, 0.7, 1))
            card.add_widget(Label(text=value_text, font_size=18, color=0.9, 0.9, 0.9, 1))
            detail_grid.add_widget(card)
        
        self.add_widget(detail_grid)
    
    def change_month(self, delta):
        self.month += delta
        if self.month > 12:
            self.month = 1
            self.year += 1
        elif self.month < 1:
            self.month = 12
            self.year -= 1
        self.build()

# ===== App =====
class SalaryApp(App):
    user_id = None
    username = None
    is_admin = False
    
    def build(self):
        init_db()
        
        Builder.load_string(KV)
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(MainScreen(name='main'))
        
        return sm

if __name__ in ('__android__', '__main__'):
    app = SalaryApp()
    app.run()
