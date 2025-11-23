from flask import Flask

def create_app():
    app = Flask(__name__)

    from .views import account
    from .views import chat
    from .views import about
    app.register_blueprint(account.ac)
    app.register_blueprint(about.ab)
    app.register_blueprint(chat.Chat)

    return app
