from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import time
from datetime import datetime, timedelta
from threading import Lock
import pytz

app = Flask(__name__)
app.secret_key = 'schooltech-secret-key-2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'equipment')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAIN_DB = os.path.join(BASE_DIR, 'schooltech.db')
db_lock = Lock()

PRE_CREATED_ACCOUNTS = {
    'GOPTAR': {
        'password': 'goptar1',
        'first_name': 'ЕВГЕНИЙ',
        'last_name': 'ГОПТАРЬ', 
        'middle_name': 'АНДРЕЕВИЧ',
        'school_number': '2098',
        'class': 'УЧИТЕЛЬ',
        'email': 'goptar@yandex.ru',
        'role': 'teacher'
    }
}

def safe_input(text):
    if not text or not isinstance(text, str):
        return ''
    dangerous = [';', '--', '/*', '*/', 'xp_']
    for d in dangerous:
        text = text.replace(d, '')
    if len(text) > 1000:
        text = text[:1000]
    return text.strip()

def get_moscow_time():
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)

def format_moscow_time(dt=None):
    if dt is None:
        dt = get_moscow_time()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_datetime_display(dt_string):
    if not dt_string:
        return ""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        moscow_tz = pytz.timezone('Europe/Moscow')
        dt_moscow = dt.astimezone(moscow_tz)
        now = datetime.now(moscow_tz)
        if dt_moscow.date() == now.date():
            return dt_moscow.strftime('%H:%M')
        elif dt_moscow.date() == now.date() - timedelta(days=1):
            return f"Вчера {dt_moscow.strftime('%H:%M')}"
        else:
            return dt_moscow.strftime('%d.%m.%Y %H:%M')
    except:
        return str(dt_string)[:16]

def format_date_display(date_string):
    if not date_string:
        return ""
    try:
        if isinstance(date_string, str):
            dt = datetime.fromisoformat(date_string)
        else:
            dt = date_string
        return dt.strftime('%d.%m.%Y')
    except:
        return str(date_string)

def get_db_connection():
    for attempt in range(5):
        try:
            with db_lock:
                conn = sqlite3.connect(MAIN_DB, timeout=30.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                return conn
        except sqlite3.OperationalError:
            if attempt < 4:
                time.sleep(0.1)
                continue
            raise
    raise sqlite3.OperationalError("Не удалось подключиться к базе")

def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  first_name TEXT NOT NULL,
                  last_name TEXT NOT NULL,
                  middle_name TEXT,
                  school_number TEXT NOT NULL,
                  class TEXT NOT NULL,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL DEFAULT 'student',
                  is_active BOOLEAN DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  description TEXT,
                  category TEXT NOT NULL,
                  school_number TEXT NOT NULL,
                  available INTEGER DEFAULT 1,
                  image_filename TEXT,
                  created_by INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_id INTEGER NOT NULL,
                  equipment_id INTEGER NOT NULL,
                  status TEXT DEFAULT 'pending',
                  due_date TEXT,
                  request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  approved_by INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id INTEGER NOT NULL,
                  receiver_id INTEGER NOT NULL,
                  message TEXT NOT NULL,
                  is_read BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    for username, account_data in PRE_CREATED_ACCOUNTS.items():
        c.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        if c.fetchone()[0] == 0:
            c.execute('''INSERT INTO users 
                        (first_name, last_name, middle_name, school_number, class, username, email, password, role)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (account_data['first_name'], account_data['last_name'], account_data['middle_name'],
                      account_data['school_number'], account_data['class'], username,
                      account_data['email'], account_data['password'], account_data['role']))
    
    conn.commit()
    conn.close()

def log_action(user_id, action):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO logs (user_id, action, created_at) VALUES (?, ?, ?)''',
                 (user_id, action, format_moscow_time()))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_by_id(user_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return format_user_data(dict(user))
        return None
    except:
        return None

def get_user_by_username(username):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username.upper(),))
        user = c.fetchone()
        conn.close()
        if user:
            return format_user_data(dict(user))
        return None
    except:
        return None

def get_all_users():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = [format_user_data(dict(row)) for row in c.fetchall()]
        conn.close()
        return users
    except:
        return []

def format_user_data(user_dict):
    user_dict['avatar'] = f"{user_dict['last_name'][0]}{user_dict['first_name'][0]}" if user_dict.get('last_name') and user_dict.get('first_name') else '??'
    user_dict['role_display'] = 'УЧИТЕЛЬ' if user_dict.get('role') == 'teacher' else 'УЧЕНИК'
    return user_dict

def get_equipment_by_school(school_number):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT * FROM equipment WHERE school_number = ? ORDER BY name''', (school_number,))
        equipment = [dict(row) for row in c.fetchall()]
        conn.close()
        for item in equipment:
            item['image_path'] = f"uploads/equipment/{item['image_filename']}" if item.get('image_filename') else "images/placeholder.jpg"
            creator = get_user_by_id(item['created_by']) if item.get('created_by') else None
            item['creator_name'] = f"{creator['first_name']} {creator['last_name']}" if creator else 'Система'
        return equipment
    except:
        return []

def get_student_requests(student_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT r.*, e.name as equipment_name, e.description as equipment_description
                     FROM requests r
                     JOIN equipment e ON r.equipment_id = e.id
                     WHERE r.student_id = ?
                     ORDER BY r.request_date DESC''', (student_id,))
        requests = [dict(row) for row in c.fetchall()]
        conn.close()
        return requests
    except:
        return []

def get_requests_for_teacher(school_number):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT r.*, 
                     e.name as equipment_name, 
                     e.available as equipment_available,
                     u.first_name, u.last_name, u.middle_name, u.class as student_class
                     FROM requests r
                     JOIN equipment e ON r.equipment_id = e.id
                     JOIN users u ON r.student_id = u.id
                     WHERE e.school_number = ? AND r.status != 'returned'
                     ORDER BY r.request_date DESC''', (school_number,))
        requests = []
        for row in c.fetchall():
            req = dict(row)
            student_name_parts = [req['last_name'], req['first_name']]
            if req['middle_name']:
                student_name_parts.append(req['middle_name'])
            req['student_name'] = " ".join(student_name_parts)
            if req.get('request_date'):
                req['request_date'] = format_datetime_display(req['request_date'])
            if req.get('due_date'):
                req['due_date'] = format_date_display(req['due_date'])
            requests.append(req)
        conn.close()
        return requests
    except Exception as e:
        print(f"Ошибка при получении заявок учителя: {e}")
        return []

def get_unread_notifications_count(user_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_user_notifications(user_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC''', (user_id,))
        notifications = [dict(row) for row in c.fetchall()]
        conn.close()
        return notifications
    except:
        return []

def create_notification(user_id, message):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)''', 
                 (user_id, safe_input(message), format_moscow_time()))
        conn.commit()
        conn.close()
    except:
        pass

def get_chat_users(current_user_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT id, username, first_name, last_name, middle_name, role
                     FROM users 
                     WHERE id != ?
                     ORDER BY last_name, first_name''', (current_user_id,))
        users = []
        for row in c.fetchall():
            user = dict(row)
            user['avatar'] = f"{user['last_name'][0]}{user['first_name'][0]}"
            users.append(user)
        conn.close()
        return users
    except:
        return []

def get_chat_messages(user1_id, user2_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT cm.*, u.first_name, u.last_name, u.username
                     FROM chat_messages cm
                     JOIN users u ON cm.sender_id = u.id
                     WHERE (cm.sender_id = ? AND cm.receiver_id = ?)
                        OR (cm.sender_id = ? AND cm.receiver_id = ?)
                     ORDER BY cm.created_at ASC
                     LIMIT 100''',
                 (user1_id, user2_id, user2_id, user1_id))
        messages = []
        for row in c.fetchall():
            msg = dict(row)
            msg['is_me'] = msg['sender_id'] == user1_id
            msg['created_at_formatted'] = format_datetime_display(msg['created_at'])
            messages.append(msg)
        c.execute('''UPDATE chat_messages 
                     SET is_read = 1 
                     WHERE receiver_id = ? AND sender_id = ? AND is_read = 0''',
                 (user1_id, user2_id))
        conn.commit()
        conn.close()
        return messages
    except:
        return []

def get_unread_chat_count(user_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT COUNT(*) as unread_count
                     FROM chat_messages
                     WHERE receiver_id = ? AND is_read = 0''',
                 (user_id,))
        count = c.fetchone()['unread_count']
        conn.close()
        return count
    except:
        return 0

@app.before_request
def basic_security():
    if request.method == 'POST':
        protected_paths = ['/chat/send', '/add_equipment', '/request_equipment', 
                          '/update_request_status', '/admin/', '/update_profile']
        for path in protected_paths:
            if request.path.startswith(path):
                if 'user_id' not in session:
                    if request.is_json:
                        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
                    return redirect(url_for('login'))
                break
    return None

@app.route('/')
def home():
    if 'user_id' in session:
        user_data = get_user_by_id(session['user_id'])
        if user_data:
            unread_count = get_unread_notifications_count(session['user_id'])
            return render_template('home.html', user=user_data, unread_count=unread_count)
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = {field: safe_input(request.form.get(field, '').strip().upper()) 
                    for field in ['first_name', 'last_name', 'middle_name', 'school_number', 'class', 'username']}
            data['email'] = safe_input(request.form.get('email', '').strip().lower())
            data['password'] = request.form.get('password', '')
            
            required_fields = ['first_name', 'last_name', 'school_number', 'class', 'username', 'email', 'password']
            if not all(data[field] for field in required_fields):
                return render_template('register.html', error='Заполните все обязательные поля')
            
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users WHERE username = ? OR email = ?", 
                     (data['username'].upper(), data['email']))
            if c.fetchone()[0] > 0:
                conn.close()
                return render_template('register.html', error='Логин или email уже заняты')
            
            c.execute('''INSERT INTO users 
                        (first_name, last_name, middle_name, school_number, class, username, email, password, role)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'student')''',
                     (data['first_name'], data['last_name'], data['middle_name'],
                      data['school_number'], data['class'], data['username'].upper(),
                      data['email'], data['password']))
            conn.commit()
            user_id = c.lastrowid
            conn.close()
            
            log_action(user_id, 'REGISTER')
            session['user_id'] = user_id
            return redirect(url_for('home'))
            
        except Exception as e:
            return render_template('register.html', error='Ошибка при регистрации')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        try:
            username = safe_input(request.form.get('username', '').strip().upper())
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('login.html', error='Заполните все поля')
            
            user = get_user_by_username(username)
            
            if user and user['password'] == password:
                session['user_id'] = user['id']
                log_action(user['id'], 'LOGIN')
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error='Неверный логин или пароль')
                
        except:
            return render_template('login.html', error='Ошибка входа')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], 'LOGOUT')
        session.clear()
    return redirect(url_for('register'))

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return redirect(url_for('register'))
    
    unread_count = get_unread_notifications_count(session['user_id'])
    return render_template('account.html', user=user_data, unread_count=unread_count)

@app.route('/rentals')
def rentals():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return redirect(url_for('register'))
    
    equipment = get_equipment_by_school(user_data['school_number'])
    student_requests = []
    
    if user_data['role'] == 'student':
        student_requests = get_student_requests(session['user_id'])
    
    unread_count = get_unread_notifications_count(session['user_id'])
    return render_template('rentals.html', user=user_data, equipment=equipment, 
                         student_requests=student_requests, unread_count=unread_count)

@app.route('/school')
def school_page():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return redirect(url_for('register'))
    
    equipment = get_equipment_by_school(user_data['school_number'])
    unread_count = get_unread_notifications_count(session['user_id'])
    return render_template('school.html', user=user_data, equipment=equipment, unread_count=unread_count)

@app.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return redirect(url_for('register'))
    
    chat_users = get_chat_users(session['user_id'])
    unread_count = get_unread_notifications_count(session['user_id'])
    
    return render_template('chat.html', 
                         user=user_data, 
                         chat_users=chat_users,
                         unread_count=unread_count)

@app.route('/chat/messages/<int:receiver_id>')
def get_chat_messages_route(receiver_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    try:
        messages = get_chat_messages(session['user_id'], receiver_id)
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat/send', methods=['POST'])
def send_chat_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    receiver_id = request.form.get('receiver_id')
    message = request.form.get('message', '').strip()
    
    if not receiver_id:
        return jsonify({'success': False, 'error': 'Получатель не указан'})
    
    if not message:
        return jsonify({'success': False, 'error': 'Сообщение не может быть пустым'})
    
    message = safe_input(message)
    
    if len(message) > 1000:
        return jsonify({'success': False, 'error': 'Сообщение слишком длинное'})
    
    receiver = get_user_by_id(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'error': 'Получатель не найден'})
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        current_time = format_moscow_time()
        
        c.execute('''INSERT INTO chat_messages (sender_id, receiver_id, message, created_at)
                     VALUES (?, ?, ?, ?)''',
                 (session['user_id'], receiver_id, message, current_time))
        
        sender = get_user_by_id(session['user_id'])
        if sender:
            create_notification(receiver_id, 
                              f'Новое сообщение от {sender["first_name"]} {sender["last_name"]}')
        
        conn.commit()
        message_id = c.lastrowid
        conn.close()
        
        log_action(session['user_id'], f'SEND_CHAT_MESSAGE to {receiver_id}')
        
        return jsonify({
            'success': True, 
            'message_id': message_id,
            'created_at': current_time,
            'created_at_formatted': format_datetime_display(current_time)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat/unread_count')
def get_unread_chat_count_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    try:
        count = get_unread_chat_count(session['user_id'])
        return jsonify({'success': True, 'unread_count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_equipment', methods=['POST'])
def add_equipment():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    name = safe_input(request.form.get('name', '').strip())
    description = safe_input(request.form.get('description', '').strip())
    category = safe_input(request.form.get('category', 'technology'))
    available = int(request.form.get('available', 1))
    
    if not name:
        return jsonify({'success': False, 'error': 'Введите название'})
    
    image_filename = None
    if 'equipment_image' in request.files:
        file = request.files['equipment_image']
        if file and file.filename:
            from werkzeug.utils import secure_filename
            import uuid
            filename = secure_filename(file.filename)
            image_filename = f"{uuid.uuid4().hex}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO equipment 
                    (name, description, category, school_number, available, image_filename, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (name.upper(), description, category, user_data['school_number'], available, image_filename, session['user_id']))
        conn.commit()
        conn.close()
        
        log_action(session['user_id'], 'ADD_EQUIPMENT')
        return jsonify({'success': True})
    except:
        return jsonify({'success': False, 'error': 'Ошибка базы'})

@app.route('/request_equipment', methods=['POST'])
def request_equipment():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return jsonify({'success': False, 'error': 'Пользователь не найден'})
    
    if user_data['role'] != 'student':
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    equipment_id = request.form.get('equipment_id')
    
    if not equipment_id:
        return jsonify({'success': False, 'error': 'Оборудование не выбрано'})
    
    try:
        equipment_id = int(equipment_id)
    except:
        return jsonify({'success': False, 'error': 'Неверный ID оборудования'})
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,))
        equipment = c.fetchone()
        
        if not equipment:
            return jsonify({'success': False, 'error': 'Оборудование не найдено'})
        
        equipment_dict = dict(equipment)
        
        if equipment_dict.get('available', 0) <= 0:
            return jsonify({'success': False, 'error': 'Оборудование недоступно'})
        
        c.execute("UPDATE equipment SET available = available - 1 WHERE id = ?", (equipment_id,))
        c.execute('''INSERT INTO requests (student_id, equipment_id, status) VALUES (?, ?, 'pending')''', 
                 (session['user_id'], equipment_id))
        
        conn.commit()
        conn.close()
        
        log_action(session['user_id'], 'REQUEST_EQUIPMENT')
        return jsonify({'success': True})
        
    except:
        return jsonify({'success': False, 'error': 'Ошибка базы'})

@app.route('/update_request_status', methods=['POST'])
def update_request_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    request_id = request.form.get('request_id')
    status = request.form.get('status')
    due_date = request.form.get('due_date', '')
    
    if not request_id or status not in ['approved', 'rejected', 'returned']:
        return jsonify({'success': False, 'error': 'Некорректные данные'})
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        request_data = c.fetchone()
        if not request_data:
            conn.close()
            return jsonify({'success': False, 'error': 'Заявка не найдена'})
        
        request_dict = dict(request_data)
        
        if status == 'approved':
            if not due_date:
                conn.close()
                return jsonify({'success': False, 'error': 'Укажите дату возврата'})
            
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                conn.close()
                return jsonify({'success': False, 'error': 'Неверный формат даты. Используйте ГГГГ-ММ-ДД'})
            
            c.execute("SELECT available FROM equipment WHERE id = ?", (request_dict['equipment_id'],))
            equipment = c.fetchone()
            if not equipment or dict(equipment)['available'] <= 0:
                conn.close()
                return jsonify({'success': False, 'error': 'Оборудование больше недоступно'})
            
            c.execute('''UPDATE requests 
                        SET status = ?, due_date = ?, approved_by = ?
                        WHERE id = ?''',
                     (status, due_date, session['user_id'], request_id))
            
            create_notification(request_dict['student_id'], 
                              f'Заявка на оборудование одобрена! Дата возврата: {due_date}')
            
        elif status == 'returned':
            c.execute('''UPDATE requests SET status = ? WHERE id = ?''', 
                     (status, request_id))
            
            c.execute('''UPDATE equipment 
                        SET available = available + 1 
                        WHERE id = ?''', 
                     (request_dict['equipment_id'],))
            
            create_notification(request_dict['student_id'],
                              'Оборудование возвращено и готово к новым заявкам')
            
        else:
            c.execute('''UPDATE requests SET status = ? WHERE id = ?''', 
                     (status, request_id))
            
            c.execute('''UPDATE equipment 
                        SET available = available + 1 
                        WHERE id = ?''', 
                     (request_dict['equipment_id'],))
            
            create_notification(request_dict['student_id'],
                              'Ваша заявка на оборудование отклонена')
        
        conn.commit()
        conn.close()
        
        log_action(session['user_id'], f'UPDATE_REQUEST {request_id} to {status}')
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(e)}'})

@app.route('/teacher_requests')
def teacher_requests():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    requests = get_requests_for_teacher(user_data['school_number'])
    return jsonify({'success': True, 'requests': requests})

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return "Доступ запрещен", 403
    
    users = get_all_users()
    student_count = len([u for u in users if u['role'] == 'student'])
    teacher_count = len([u for u in users if u['role'] == 'teacher'])
    
    logs = []
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT l.action, l.created_at, u.username, u.first_name, u.last_name 
                     FROM logs l 
                     LEFT JOIN users u ON l.user_id = u.id
                     ORDER BY l.created_at DESC LIMIT 50''')
        logs = [dict(row) for row in c.fetchall()]
        conn.close()
    except:
        pass
    
    unread_count = get_unread_notifications_count(session['user_id'])
    
    return render_template('admin_panel.html', 
                         user=user_data,
                         student_count=student_count,
                         teacher_count=teacher_count,
                         logs=logs,
                         unread_count=unread_count)

@app.route('/admin/send_notification', methods=['POST'])
def admin_send_notification():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    message = safe_input(request.form.get('message', '').strip())
    notification_type = request.form.get('type', 'all')
    
    if not message:
        return jsonify({'success': False, 'error': 'Введите сообщение'})
    
    users = get_all_users()
    
    if notification_type == 'students':
        target_users = [u for u in users if u['role'] == 'student']
    elif notification_type == 'teachers':
        target_users = [u for u in users if u['role'] == 'teacher']
    else:
        target_users = users
    
    sent_count = 0
    for user in target_users:
        create_notification(user['id'], message)
        sent_count += 1
    
    log_action(session['user_id'], 'SEND_NOTIFICATION')
    
    return jsonify({
        'success': True, 
        'sent_count': sent_count
    })

@app.route('/admin/clear_logs', methods=['POST'])
def admin_clear_logs():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM logs")
        conn.commit()
        conn.close()
        
        log_action(session['user_id'], 'CLEAR_LOGS')
        return jsonify({'success': True})
    except:
        return jsonify({'success': False, 'error': 'Ошибка очистки'})

@app.route('/admin/databases')
def view_databases():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data or user_data['role'] != 'teacher':
        return "Доступ запрещен", 403
    
    users = get_all_users()
    
    equipment = []
    requests = []
    logs = []
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM equipment")
        equipment = [dict(row) for row in c.fetchall()]
        
        c.execute('''SELECT r.*, u.username as student_username, e.name as equipment_name 
                     FROM requests r 
                     LEFT JOIN users u ON r.student_id = u.id 
                     LEFT JOIN equipment e ON r.equipment_id = e.id''')
        requests = [dict(row) for row in c.fetchall()]
        
        c.execute('''SELECT l.action, l.created_at, u.username 
                     FROM logs l 
                     LEFT JOIN users u ON l.user_id = u.id
                     ORDER BY l.created_at DESC LIMIT 100''')
        logs = [dict(row) for row in c.fetchall()]
        conn.close()
    except:
        pass
    
    unread_count = get_unread_notifications_count(session['user_id'])
    
    return render_template('databases.html', 
                         user=user_data,
                         users=users,
                         equipment=equipment,
                         requests=requests,
                         logs=logs,
                         unread_count=unread_count)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return 'Не авторизован', 401
    
    first_name = safe_input(request.form.get('first_name', '').strip().upper())
    last_name = safe_input(request.form.get('last_name', '').strip().upper())
    middle_name = safe_input(request.form.get('middle_name', '').strip().upper())
    email = safe_input(request.form.get('email', '').strip().lower())
    
    if not all([first_name, last_name, email]):
        return 'Заполните все обязательные поля', 400
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''UPDATE users 
                    SET first_name = ?, last_name = ?, middle_name = ?, email = ?
                    WHERE id = ?''',
                 (first_name, last_name, middle_name, email, session['user_id']))
        conn.commit()
        conn.close()
        
        log_action(session['user_id'], 'UPDATE_PROFILE')
        return 'Профиль обновлен'
    except:
        return 'Ошибка обновления', 500

@app.route('/get_notifications')
def get_notifications_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    notifications = get_user_notifications(session['user_id'])
    return jsonify({'success': True, 'notifications': notifications})

@app.route('/mark_notification_read', methods=['POST'])
def mark_notification_read_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    notification_id = request.json.get('notification_id')
    if notification_id:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
            conn.commit()
            conn.close()
        except:
            pass
    
    return jsonify({'success': True})

@app.route('/mark_all_notifications_read', methods=['POST'])
def mark_all_notifications_read_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False, 'error': 'Ошибка'})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    if not os.path.exists(MAIN_DB):
        init_database()
    app.run(host='0.0.0.0', port=5000)