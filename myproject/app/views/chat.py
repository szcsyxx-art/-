from flask import Blueprint

Chat = Blueprint('chat list',__name__,)           #蓝图对象

@Chat.route('/chatlist')
def chatlist():
    return '聊天列表'