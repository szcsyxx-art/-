from flask import Blueprint, request, render_template, session, redirect, flash
from WkSqlite3 import WkSqlite3
import os

fr = Blueprint('friend', __name__)


# 确保能正确找到数据库文件
def get_db_path():
    """获取数据库文件的绝对路径"""
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(current_dir, 'database.db')

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

def get_user_id(db, username):
    """获取用户id"""
    cursor = db.conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def get_username(db, userid):
    """获取用户名"""
    cursor = db.conn.execute(
        "SELECT username FROM users WHERE id = ?",
        (userid,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def get_friends(db, username):
    """查看当前用户的好友"""
    cursor = db.conn.execute(
        "SELECT friends_id FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def get_friend_request(db, username):
    """查看当前用户的好友请求信息"""
    cursor = db.conn.execute(
        "SELECT friend_request FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def update_friends(db, friends_id, username):
    """更新数据库中的好友列表"""
    friends_id_str = ",".join(friends_id)

    db.conn.execute(
        "UPDATE users SET friends_id = ? WHERE username = ?",
        (friends_id_str, username)
    )
    db.conn.commit()

def update_friend_request(db, friend_request, username):
    """更新数据库中的好友列表请求"""
    friend_request_str = ",".join(friend_request)

    db.conn.execute(
        "UPDATE users SET friend_request = ? WHERE username = ?",
        (friend_request_str, username)
    )
    db.conn.commit()

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

def search_user(db, text):
    """在数据库中搜索用户"""
    result = []
    cursor = db.conn.execute(
        "SELECT username FROM users"
    )
    if text:
        for i in cursor:
            if text in i[0]:
                result.append(i[0])
    else:
        return 'NoInput'
    if not result:
        return None
    return result

@fr.route('/friend_list')
def friend_list():
    if request.method == 'GET':
        username = session.get('current_user')
        if not username:
            flash('请先登录！', 'error')
            return redirect('/login')
            
        db = init_db()
        userid = get_user_id(db, username)
        friends = get_friends(db, username)
        friend_list = []
        del_friend = request.args.get('del')

        # 处理好友列表显示
        if friends:
            friends = friends.split(',')
            for friend_id in friends:
                if friend_id:  # 确保不是空字符串
                    friend_name = get_username(db, friend_id)
                    if friend_name:  # 确保用户存在
                        friend_list.append((find_user_profile_picture(friend_id), friend_name))
        else:
            friends = []
        
        # 处理删除好友请求
        if del_friend:
            print(f"要删除的好友: {del_friend}")
            
            # 获取要删除的好友ID（确保是字符串）
            del_friend_id = str(get_user_id(db, del_friend))
            print(f"要删除的好友ID: {del_friend_id}")
            
            if friends and del_friend_id in friends:
                # 创建新列表而不是修改原列表
                new_friends = [f for f in friends if f != del_friend_id]
                
                # 更新当前用户的好友列表
                update_friends(db, new_friends, username)
                
                # 也删除对方好友列表中的自己
                friend_friends = get_friends(db, del_friend)
                if friend_friends:
                    friend_friends = friend_friends.split(',')
                    new_friend_friends = [f for f in friend_friends if f != str(userid)]
                    update_friends(db, new_friend_friends, del_friend)
                
                flash('✅ 成功删除好友', 'success')
                return redirect('/friend_list')
            else:
                flash('❌ 未找到该好友', 'error')

        # 处理好友请求消息
        friend_request = get_friend_request(db, username)
        friend_request_list = []
        if friend_request:
            friend_request = friend_request.split(',')
            for i in friend_request:
                friend_request_list.append((find_user_profile_picture(i), get_username(db, i)))
        else:
            friend_request = []

        accept_friend = request.args.get('accept')
        if accept_friend:
            accept_id = get_user_id(db, accept_friend)
            if str(accept_id) in friend_request:
                
                a = 0
                for i in friend_request:
                    if str(i) == str(accept_id):
                        friend_request.pop(a)
                        break
                    a += 1
                update_friend_request(db, friend_request, username)

                if not friends:
                    friends = []
                if not str(accept_id) in friends:
                    friends.append(str(accept_id))
                    update_friends(db, friends, username)
                    accept_friend_friends = get_friends(db, accept_friend)
                    if accept_friend_friends:
                        accept_friend_friends = accept_friend_friends.split(',')
                    else:
                        accept_friend_friends = []
                    accept_friend_friends.append(str(userid))
                    update_friends(db, accept_friend_friends, accept_friend)
                flash(f'✅已和{accept_friend}成为好友!', 'success')
                return redirect('/friend_list')
            else:
                flash(f'❌对方没有向你发送好友请求!', 'danger')
        
        decline_friend = request.args.get('decline')
        if decline_friend:
            decline_id = get_user_id(db, decline_friend)
            a = 0
            for i in friend_request:
                if str(i) == str(decline_id):
                    friend_request.pop(a)
                    break
                a += 1
            update_friend_request(db, friend_request, username)
            flash(f'✅已拒绝{decline_friend}的好友申请', 'success')
            return redirect('/friend_list')
        
        return render_template(
            'friend_list.html',
            friend_list=friend_list if friend_list else None,
            friend_request_list=friend_request_list
        )


@fr.route('/addfriend', methods=['GET', 'POST'])
def addfriend():
    if request.method == 'GET':
        return render_template('addfriend.html', user_list='get')
    
    elif request.method == 'POST':
        db = init_db()
        search = request.form.get('search', '').strip()
        
        if not search:
            return render_template('addfriend.html', user_list=None)
        
        user_list = search_user(db, search)
        
        if user_list == 'NoInput':
            return render_template('addfriend.html', user_list=None)
        elif not user_list:
            return render_template('addfriend.html', user_list=None)
        
        return render_template('addfriend.html', user_list=user_list)

# 添加处理好友请求的路由
@fr.route('/add_friend_action', methods=['POST'])
def add_friend_action():
    if 'current_user' not in session:
        flash('请先登录！', 'error')
        return redirect('/login')
    
    friend_username = request.form.get('friend_username')
    current_user = session['current_user']
    
    db = init_db()

    userid = get_user_id(db, current_user)
    
    # 检查好友是否存在
    friend_id = get_user_id(db, friend_username)
    if not friend_id:
        flash('❌用户不存在', 'error')
        return redirect('/addfriend')
    
    # 检查是否已经是好友
    current_friends = get_friends(db, current_user)
    if current_friends:
        friends_list = current_friends.split(',')
        if str(friend_id) in friends_list:
            flash('❌已经是好友了', 'warning')
            return redirect('/addfriend')
    
    friend_friend_request = get_friend_request(db, friend_username)
    if friend_friend_request:
            friend_friend_request = friend_friend_request.split(',')
    else:
        friend_friend_request = []

    if str(userid) in friend_friend_request:
        flash(f'❌已经给Ta发送请求啦, 不要重复发送哦')
        return redirect('/addfriend')
    friend_friend_request.append(str(userid))
    update_friend_request(db, friend_friend_request, friend_username)
    
    flash(f'✅ 已发送好友请求给 {friend_username}', 'success')
    return redirect('/addfriend')