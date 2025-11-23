import os, sys, random
from flask import Flask, render_template, redirect, request
from waitress import serve

# 添加项目路径到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, 'app')
sys.path.insert(0, app_dir)

from app.views.account import ac
from app.views.about import ab
from app.views.friend import fr

app = Flask(__name__)
# 配置Session密钥
app.secret_key = '你的超级安全密钥_可以随便改_但要够长bruh233333'
app.register_blueprint(ac)
app.register_blueprint(ab)
app.register_blueprint(fr)

@app.route('/')
def goto_home():
    return redirect('/home')

@app.route('/home')
def index():
    # 一次性读取所有回声洞内容
    with open('echohole.txt', 'r', encoding='utf-8') as f:
        all_echocaves = [line.strip() for line in f if line.strip()]
    
    # 随机选择一条用于初始显示
    initial_echocave = random.choice(all_echocaves) if all_echocaves else "暂无内容"
    
    return render_template('index.html', 
                         echocave=initial_echocave,
                         all_echocaves=all_echocaves)


if __name__ == '__main__':
    print('-' * 50)
    print('网站启动中...')
    print('数据库路径:', os.path.join(os.getcwd(), 'database.db'))
    print('项目路径:', os.getcwd())
    print('服务地址: http://127.0.0.1:5000')
    print('-' * 50)

    # 确保数据库文件存在
    if not os.path.exists('database.db'):
        print('📦 初始化数据库中...')
        from app.views.account import init_db
        init_db()

    try:
        serve(app, host='0.0.0.0', port=5000, threads=16)
        #app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print('启动失败:', str(e))
