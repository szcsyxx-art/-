from flask import Blueprint, render_template, request, redirect, jsonify, session, flash, url_for
from WkSqlite3 import WkSqlite3
import bcrypt
import os
import sys
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

logging.getLogger('WkSqlite3').setLevel(logging.WARNING)

# 确保能正确找到数据库文件
def get_db_path():
    """获取数据库文件的绝对路径"""
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(current_dir, 'database.db')

ac = Blueprint('account', __name__)  # 蓝图对象

# 上传配置
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_user_avatar(file, user_id):
    """处理用户头像：验证、转换、保存"""
    try:
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        if file_size > MAX_FILE_SIZE:
            return False, f"文件太大！请选择小于5MB的图片（当前：{file_size//1024}KB）"
        
        # 尝试使用Pillow处理图片
        try:
            from PIL import Image
            import io
            
            # 读取文件数据
            file_data = file.read()
            
            # 用Pillow打开图片
            image = Image.open(io.BytesIO(file_data))
            
            # 验证图片完整性
            image.verify()
            
            # 重新打开（因为verify()会关闭图片）
            image = Image.open(io.BytesIO(file_data))
            
            # 转换格式和调整大小
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整大小（保持比例）
            width, height = image.size
            if width > 800 or height > 800:
                image.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            # 保存为标准JPEG
            output_path = os.path.join(UPLOAD_FOLDER, f"{user_id}.jpg")
            image.save(output_path, 'JPEG', quality=85, optimize=True)
            
            return True, f"{user_id}.jpg"
            
        except ImportError:
            # 如果没有安装Pillow，使用原始方法
            print("Pillow未安装，使用原始文件保存方法")
            file_extension = secure_filename(file.filename).rsplit('.', 1)[1].lower()
            new_filename = f"{user_id}.{file_extension}"
            file_path = os.path.join(UPLOAD_FOLDER, new_filename)
            file.save(file_path)
            return True, new_filename
            
    except Exception as e:
        return False, f"图片处理失败: {str(e)}"

# 初始化数据库（确保表存在）
def init_db():
    """初始化数据库"""
    db_path = get_db_path()
    db = WkSqlite3(db_path)  # 传入完整路径
    db.set_table('users')
    # 创建用户表（如果不存在）
    db.conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pwd_hash TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    ''')
    db.conn.commit()
    return db

def get_image_files(folder_path):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    image_files = []
    
    for filename in os.listdir(folder_path):
        # 检查文件扩展名
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            image_files.append(filename)
    
    return image_files

# 用户名检查方法
def check_username_exists(db, username):
    """检查用户名是否存在"""
    cursor = db.conn.execute(
        "SELECT id FROM users WHERE username = ?", 
        (username,)
    )
    return cursor.fetchone() is not None

def get_user_password_hash(db, username):
    """获取用户的密码哈希"""
    cursor = db.conn.execute(
        "SELECT pwd_hash FROM users WHERE username = ?", 
        (username,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def get_user_id(db, username):
    """获取用户id"""
    cursor = db.conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def find_user_profile_picture(user_id):
    """查找用户的头像文件"""
    upload_folder = 'static/uploads'
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    # 确保上传目录存在
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder, exist_ok=True)
    
    # 查找用户头像
    for ext in image_extensions:
        filename = f"{user_id}{ext}"
        file_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(file_path):
            return f"/static/uploads/{filename}"

    # 直接返回默认头像路径
    return '/static/uploads/default.png'

@ac.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        username = request.form.get('username')
        pwd = request.form.get('pwd')
        
        # 重要：检查空值
        if not all([username, pwd]):
            return render_template('login.html', error="❌ 请填写用户名和密码！")
        
        # 初始化数据库
        db = init_db()
        
        try:
            # 检查用户是否存在
            if not check_username_exists(db, username):
                return render_template('login.html', error="❌ 用户名不存在！")
            
            # 获取存储的密码哈希
            stored_hash = get_user_password_hash(db, username)
            if not stored_hash:
                return render_template('login.html', error="❌ 用户数据异常！")
            
            # 验证密码
            if bcrypt.checkpw(pwd.encode(), stored_hash.encode()):
                print(f'✅ 登录成功：用户名：{username}')
                userid = get_user_id(db, username)
                
                # 查找用户头像
                profile_picture_path = find_user_profile_picture(userid)
                if not profile_picture_path:
                    profile_picture_path = '/static/uploads/default.png'

                session['current_user'] = username
                session['user_id'] = userid
                session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                session['login_count'] = session.get('login_count', 0) + 1
                session['profile_picture_path'] = profile_picture_path

                return redirect('/home')
            else:
                print(f'❌ 登录失败：用户名：{username}，密码错误')
                return render_template('login.html', error="❌ 密码错误！")

        except Exception as e:
            return render_template('login.html', error=f"❌ 登录失败: {str(e)}")

@ac.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    # 获取表单数据
    reg_username = request.form.get('username')
    reg_pwd = request.form.get('pwd')
    reg_confirm_pwd = request.form.get('confirm_pwd')

    # 重要：检查空值
    if not all([reg_username, reg_pwd, reg_confirm_pwd]):
        return render_template(
            'register.html',
            error="❌ 请填写所有必填字段！"
        )

    # 检查密码一致性
    if reg_pwd != reg_confirm_pwd:
        return render_template(
            'register.html',
            error="❌ 两次密码输入不一致！"
        )

    # 初始化数据库
    db = init_db()
        
    try:
        # 检查用户名是否已存在
        if check_username_exists(db, reg_username):
            return render_template(
                'register.html', 
                error=f"❌ 用户名 '{reg_username}' 已被注册！"
            )

        # 生成密码哈希
        pwd_hash = bcrypt.hashpw(reg_pwd.encode(), bcrypt.gensalt())

        # 插入新用户
        db.insert_row(
            username=reg_username, 
            pwd_hash=pwd_hash.decode()  # 转成字符串存储
        )

        print(f'有人执行了注册操作：用户名：{reg_username}')
        return render_template('welcome.html', userinfo=f'✅ 注册成功！欢迎 {reg_username}')

    except Exception as e:
        # 捕获其他可能的错误（如数据库唯一约束冲突）
        if "UNIQUE constraint failed" in str(e):
            return render_template(
                'register.html', 
                error=f"❌ 用户名 '{reg_username}' 已被注册！"
            )
        return render_template(
            'register.html', 
            error=f"❌ 注册失败: {str(e)}"
        )

# 实时用户名检查API
@ac.route('/api/check_username', methods=['POST'])
def api_check_username():
    """API接口：检查用户名是否可用"""
    data = request.get_json()
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'available': False, 'message': '用户名不能为空'})

    if len(username) < 3 or len(username) > 20:
        return jsonify({'available': False, 'message': '用户名长度必须在3-20个字符之间'})

    db = init_db()
    if check_username_exists(db, username):
        return jsonify({'available': False, 'message': '❌ 用户名已被注册'})
    return jsonify({'available': True, 'message': '✅ 用户名可用'})

# 退出登录路由
@ac.route('/logout')
def logout():
    session.pop('current_user', None)
    session.pop('user_id', None)
    session.pop('login_time', None)
    session.pop('login_count', None)
    session.pop('profile_picture_path', None)
    return redirect('/home')

# 个人资料页
@ac.route('/profile')
def profile():
    username = session.get('current_user')
    user_id = session.get('user_id')
    profile_picture_path = session.get('profile_picture_path')
    
    if not username:
        return redirect('/login?error=请先登录')
    
    return render_template(
        'profile.html',
        username=username,
        userid=user_id,
        profile_picture_path=profile_picture_path
    )

@ac.route('/upload_image', methods=['POST'])
def upload_image():
    """处理头像上传"""
    # 检查用户是否登录
    if 'current_user' not in session:
        flash('请先登录！')
        return redirect(url_for('account.login'))
    
    # 检查文件是否存在
    if 'image' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('account.profile'))
    
    file = request.files['image']
    
    # 检查是否选择了文件
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('account.profile'))
    
    # 检查文件类型
    if file and allowed_file(file.filename):
        user_id = session.get('user_id')
        
        # 使用新的图片处理函数
        success, result = process_user_avatar(file, user_id)
        
        if success:
            session['profile_picture_path'] = f"/static/uploads/{result}"
            flash('✅ 头像上传成功！', 'success')
        else:
            flash(f'❌ {result}', 'warning')
        
        return redirect(url_for('account.profile'))
    
    else:
        flash('不支持的文件格式!请上传图片文件(PNG, JPG, JPEG, GIF)')
        return redirect(url_for('account.profile'))
    
@ac.route('/change_username', methods=['GET', 'POST'])
def change_username():
    if request.method == 'GET':
        return redirect(url_for('account.profile'))
    db = init_db()
    username = session.get('current_user')
    user_id = get_user_id(db, username)
    new_username = request.form.get('new_username')

    if not new_username:
        flash('❌ 用户名不能为空', 'warning')
    elif len(new_username) < 3 or len(new_username) > 20:
        flash('❌ 用户名长度必须在3-20个字符之间', 'warning')
    elif new_username == username:
        flash('emm...你好像没有改用户名啊😅', 'info')
    elif check_username_exists(db, new_username):
        flash('❌ 用户名已被注册', 'warning')
    else:
        flash('修改成功!', 'success')
    
    print(new_username)
    try:
        # 执行更新操作
        db.conn.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user_id))
        # 提交事务，确保更改保存到数据库 [citation:2]
        db.conn.commit()
        session['current_user'] = new_username
        print("更新成功！")
    except Exception as e:
        print(f"更新失败: {e}")

    return redirect(url_for('account.profile'))
