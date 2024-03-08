from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = "femboysarecute"

messages = []
sessions = {}

# Heartbeat timeout (in seconds)
HEARTBEAT_TIMEOUT = 10

def update_user_list():
    users = [sessions[x]['username'] for x in sessions]
    socketio.emit('update_user_list', {'users': users}, broadcast=True)

def remove_inactive_sessions():
    now = datetime.now()
    for addr, session in list(sessions.items()):
        if now - session['last_active'] > timedelta(seconds=HEARTBEAT_TIMEOUT):
            sessions.pop(addr)
    update_user_list()

@app.route('/')
def index():
    session = sessions.get(request.remote_addr)
    users = [sessions[x]['username'] for x in sessions]
    if not session or 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', messages=messages, username=session['username'], users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    session = sessions.get(request.remote_addr, {})
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        password = request.form['password']
        if password == 'pookie':
            session['username'] = request.form['username']
            session['last_active'] = datetime.now()
            sessions[request.remote_addr] = session
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    sessions.pop(request.remote_addr, None)
    update_user_list()
    return redirect(url_for('login'))

@app.route('/protected', methods=['GET', 'POST'])
def protected():
    session = sessions.get(request.remote_addr)
    if not session or 'username' not in session:
        return redirect(url_for('login'))
    return render_template('protected.html')

@socketio.on('send_message')
def send(data):
    session = sessions.get(request.remote_addr)
    if not session or 'username' not in session:
        return
    session['last_active'] = datetime.now()
    username = session['username']
    message = data['message']
    messages.append({'username': username, 'message': message})
    emit('new_message', {'username': username, 'message': message}, broadcast=True)
    update_user_list() 

@socketio.on('heartbeat')
def handle_heartbeat():
    session = sessions.get(request.remote_addr)
    if session:
        session['last_active'] = datetime.now()
        remove_inactive_sessions()

@socketio.on('connect')
def on_connect():
    session = sessions.get(request.remote_addr, {})
    if 'username' in session:
        emit('load_messages', messages)
    update_user_list()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=32000, debug=True)