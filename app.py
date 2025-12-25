from flask import Flask, render_template, request, session, redirect, url_for, flash
import random
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'casino_secret_key_2025'
# Флаг для отслеживания инициализации БД
db_initialized = False

# Инициализация базы данных
def init_db():
    global db_initialized
    if db_initialized:
        return
        
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    
    # Проверяем существование таблиц через SELECT
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_table_exists = cursor.fetchone()
    
    if not users_table_exists:
        # Создаем таблицы только если они не существуют
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                bet_amount INTEGER,
                win_amount INTEGER,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("Таблицы базы данных созданы")
    
    conn.commit()
    conn.close()
    db_initialized = True

# Хеширование пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Проверка пароля
def verify_password(password, password_hash):
    return hash_password(password) == password_hash

# Получение пользователя по ID через SELECT
def get_user_by_id(user_id):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, password_hash, balance FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password_hash': result[3],
            'balance': result[4]
        }
    return None

# Получение пользователя по имени через SELECT
def get_user_by_username(username):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, password_hash, balance FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password_hash': result[3],
            'balance': result[4]
        }
    return None

# Проверка существования пользователя по email через SELECT
def get_user_by_email(email):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2]
        }
    return None

# Проверка существования пользователя через SELECT (универсальная функция)
def check_user_exists(username=None, email=None):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    
    if username and email:
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
    elif username:
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    elif email:
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    else:
        conn.close()
        return False
    
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Создание сессии
def create_session(user_id):
    session_id = secrets.token_urlsafe(32)
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO user_sessions (session_id, user_id, expires_at) VALUES (?, ?, datetime("now", "+7 days"))',
        (session_id, user_id)
    )
    conn.commit()
    conn.close()
    return session_id

# Проверка сессии через SELECT
def verify_session(session_id):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT user_id FROM user_sessions WHERE session_id = ? AND expires_at > datetime("now")',
        (session_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Удаление сессии
def delete_session(session_id):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_sessions WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

# Получение баланса пользователя через SELECT
def get_user_balance(user_id):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 1000

# Обновление баланса
def update_user_balance(user_id, new_balance):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
    conn.commit()
    conn.close()

# Добавление в историю игр
def add_game_history(user_id, game_type, bet_amount, win_amount, result):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO game_history 
           (user_id, game_type, bet_amount, win_amount, result) 
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, game_type, bet_amount, win_amount, result)
    )
    conn.commit()
    conn.close()

# Получение истории игр через SELECT
def get_game_history(user_id, limit=5):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT game_type, bet_amount, win_amount, result, created_at 
           FROM game_history 
           WHERE user_id = ? 
           ORDER BY created_at DESC 
           LIMIT ?''',
        (user_id, limit)
    )
    history = cursor.fetchall()
    conn.close()
    
    return [{
        'game': row[0],
        'bet': row[1],
        'win': row[2],
        'result': row[3],
        'timestamp': row[4][11:19] if row[4] else '00:00:00'
    } for row in history]

# Middleware для проверки аутентификации
@app.before_request
def check_auth():
    # Инициализируем базу данных один раз
    init_db()
    
    # Исключаем статические файлы и страницы аутентификации
    if request.endpoint in ['static', 'login', 'register', 'auth_login', 'auth_register']:
        return
    
    user_id = session.get('user_id')
    session_id = session.get('session_id')
    
    if user_id and session_id:
        # Проверяем валидность сессии через SELECT
        valid_user_id = verify_session(session_id)
        if valid_user_id and valid_user_id == user_id:
            # Обновляем время последнего входа
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = datetime("now") WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            return
    
    # Если не авторизован, перенаправляем на страницу входа
    return redirect(url_for('login'))

class BlackjackGame:
    @staticmethod
    def new_deck():
        suits = ['♠', '♥', '♦', '♣']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = []
        for suit in suits:
            for value in values:
                deck.append(f"{value}{suit}")
        random.shuffle(deck)
        return deck

    @staticmethod
    def calculate_hand_value(hand):
        value = 0
        aces = 0
        
        for card in hand:
            card_value = card[:-1]
            if card_value in ['J', 'Q', 'K']:
                value += 10
            elif card_value == 'A':
                aces += 1
                value += 11
            else:
                value += int(card_value)
        
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
            
        return value

    @staticmethod
    def deal_initial_cards(deck):
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        return player_hand, dealer_hand, deck

    @staticmethod
    def hit(hand, deck):
        hand.append(deck.pop())
        return hand, deck

    @staticmethod
    def dealer_play(dealer_hand, deck):
        while BlackjackGame.calculate_hand_value(dealer_hand) < 17:
            dealer_hand, deck = BlackjackGame.hit(dealer_hand, deck)
        return dealer_hand, deck

    @staticmethod
    def determine_winner(player_value, dealer_value):
        if player_value > 21:
            return "dealer"
        elif dealer_value > 21:
            return "player"
        elif player_value > dealer_value:
            return "player"
        elif dealer_value > player_value:
            return "dealer"
        else:
            return "push"

# Страницы аутентификации
@app.route('/login')
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register')
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/auth/login', methods=['POST'])
def auth_login():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('login'))
        
        # Используем SELECT для поиска пользователя
        user = get_user_by_username(username)
        if user and verify_password(password, user['password_hash']):
            session_id = create_session(user['id'])
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['session_id'] = session_id
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Ошибка при входе: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/auth/register', methods=['POST'])
def auth_register():
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Валидация
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 4:
            flash('Пароль должен содержать минимум 4 символа', 'error')
            return redirect(url_for('register'))
        
        # Используем SELECT для проверки существования пользователя
        if check_user_exists(username=username, email=email):
            flash('Пользователь с таким именем или email уже существует', 'error')
            return redirect(url_for('register'))
        
        # Создаем нового пользователя
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, hash_password(password))
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Получаем данные пользователя через SELECT для подтверждения
        new_user = get_user_by_id(user_id)
        if new_user:
            session_id = create_session(user_id)
            session['user_id'] = user_id
            session['username'] = new_user['username']
            session['session_id'] = session_id
            
            flash('Регистрация успешна! Добро пожаловать!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Ошибка при создании пользователя', 'error')
            return redirect(url_for('register'))
        
    except sqlite3.IntegrityError as e:
        flash('Ошибка: пользователь с такими данными уже существует', 'error')
        return redirect(url_for('register'))
    except Exception as e:
        flash(f'Ошибка при регистрации: {str(e)}', 'error')
        return redirect(url_for('register'))

@app.route('/logout')
def logout():
    session_id = session.get('session_id')
    if session_id:
        delete_session(session_id)
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Основные маршруты
@app.route('/')
def index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    balance = get_user_balance(user_id)
    history = get_game_history(user_id)
    return render_template('index.html', 
                         balance=balance, 
                         history=history,
                         username=session.get('username'))

@app.route('/slots', methods=['GET', 'POST'])
def slots_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    balance = get_user_balance(user_id)
    message = ""
    reels = ['?', '?', '?']
    
    if request.method == 'POST':
        bet = int(request.form.get('bet', 10))
        
        if bet > balance:
            message = "❌ Недостаточно средств!"
        else:
            symbols = ['🍒', '🍋', '🍊', '⭐', '🔔', '💎']
            reels = [random.choice(symbols) for _ in range(3)]
            
            if reels[0] == reels[1] == reels[2]:
                multiplier = 10 if reels[0] == '💎' else 5
                win = bet * multiplier
            elif reels[0] == reels[1] or reels[1] == reels[2]:
                win = bet * 2
            else:
                win = 0
            
            new_balance = balance - bet + win
            update_user_balance(user_id, new_balance)
            add_game_history(user_id, 'slots', bet, win, str(reels))
            
            if win > 0:
                message = f"🎉 Поздравляем! Вы выиграли {win} копейка!"
            else:
                message = "😔 Повезет в следующий раз!"
            
            balance = new_balance
    
    return render_template('slots.html', 
                         balance=balance, 
                         reels=reels, 
                         message=message)

@app.route('/blackjack', methods=['GET', 'POST'])
def blackjack_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    balance = get_user_balance(user_id)
    message = ""
    
    if 'blackjack_deck' not in session or request.form.get('action') == 'new_game':
        session['blackjack_deck'] = BlackjackGame.new_deck()
        session['player_hand'] = []
        session['dealer_hand'] = []
        session['game_state'] = 'betting'
        session['blackjack_bet'] = 0
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'place_bet':
            bet = int(request.form.get('bet', 10))
            
            if bet > balance:
                message = "❌ Недостаточно средств!"
            else:
                player_hand, dealer_hand, deck = BlackjackGame.deal_initial_cards(session['blackjack_deck'])
                session['player_hand'] = player_hand
                session['dealer_hand'] = dealer_hand
                session['blackjack_deck'] = deck
                session['blackjack_bet'] = bet
                session['game_state'] = 'player_turn'
                
                new_balance = balance - bet
                update_user_balance(user_id, new_balance)
                balance = new_balance
                
                player_value = BlackjackGame.calculate_hand_value(player_hand)
                if player_value == 21:
                    session['game_state'] = 'dealer_turn'
                    session['dealer_hand'], session['blackjack_deck'] = BlackjackGame.dealer_play(
                        session['dealer_hand'], session['blackjack_deck']
                    )
                    dealer_value = BlackjackGame.calculate_hand_value(session['dealer_hand'])
                    
                    if dealer_value == 21:
                        new_balance = balance + bet
                        update_user_balance(user_id, new_balance)
                        message = "🤝 Оба имеют блэкджек! Ничья!"
                        session['game_state'] = 'game_over'
                        add_game_history(user_id, 'blackjack', bet, 0, 'push')
                    else:
                        win_amount = int(bet * 2.5)
                        new_balance = balance + win_amount
                        update_user_balance(user_id, new_balance)
                        message = f"🎉 Блэкджек! Вы выиграли {win_amount} копейка!"
                        session['game_state'] = 'game_over'
                        add_game_history(user_id, 'blackjack', bet, win_amount - bet, 'blackjack')
                    balance = new_balance
        
        elif action == 'hit':
            session['player_hand'], session['blackjack_deck'] = BlackjackGame.hit(
                session['player_hand'], session['blackjack_deck']
            )
            
            player_value = BlackjackGame.calculate_hand_value(session['player_hand'])
            if player_value > 21:
                message = "💥 Перебор! Дилер выиграл!"
                session['game_state'] = 'game_over'
                add_game_history(user_id, 'blackjack', session['blackjack_bet'], 0, 'bust')
        
        elif action == 'stand':
            session['game_state'] = 'dealer_turn'
            session['dealer_hand'], session['blackjack_deck'] = BlackjackGame.dealer_play(
                session['dealer_hand'], session['blackjack_deck']
            )
            
            player_value = BlackjackGame.calculate_hand_value(session['player_hand'])
            dealer_value = BlackjackGame.calculate_hand_value(session['dealer_hand'])
            
            winner = BlackjackGame.determine_winner(player_value, dealer_value)
            
            if winner == "player":
                win_amount = session['blackjack_bet'] * 2
                new_balance = balance + win_amount
                update_user_balance(user_id, new_balance)
                message = f"🎉 Вы выиграли {win_amount} копейка!"
                add_game_history(user_id, 'blackjack', session['blackjack_bet'], session['blackjack_bet'], 'win')
                balance = new_balance
            elif winner == "dealer":
                message = "😞 Дилер выиграл!"
                add_game_history(user_id, 'blackjack', session['blackjack_bet'], 0, 'lose')
            else:
                new_balance = balance + session['blackjack_bet']
                update_user_balance(user_id, new_balance)
                message = "🤝 Ничья! Ставка возвращена"
                add_game_history(user_id, 'blackjack', session['blackjack_bet'], 0, 'push')
                balance = new_balance
            
            session['game_state'] = 'game_over'
    
    player_hand = session.get('player_hand', [])
    dealer_hand = session.get('dealer_hand', [])
    game_state = session.get('game_state', 'betting')
    
    player_value = BlackjackGame.calculate_hand_value(player_hand) if player_hand else 0
    dealer_value = BlackjackGame.calculate_hand_value(dealer_hand) if dealer_hand else 0
    
    show_dealer_value = game_state in ['dealer_turn', 'game_over']
    dealer_display_hand = dealer_hand.copy()
    if not show_dealer_value and len(dealer_display_hand) > 1:
        dealer_display_hand[1] = '??'
    
    return render_template('blackjack.html',
                         balance=balance,
                         player_hand=player_hand,
                         dealer_hand=dealer_display_hand,
                         player_value=player_value,
                         dealer_value=dealer_value if show_dealer_value else '?',
                         message=message,
                         game_state=game_state,
                         current_bet=session.get('blackjack_bet', 0))

@app.route('/coinflip', methods=['GET', 'POST'])
def coinflip_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    balance = get_user_balance(user_id)
    message = ""
    result = None
    stats = {'wins': 0, 'total': 0}
    
    if request.method == 'POST':
        bet = int(request.form.get('bet', 10))
        choice = request.form.get('choice', 'heads')
        
        if bet > balance:
            message = "❌ Недостаточно средств!"
        else:
            # Подбрасываем монетку (50/50 шанс)
            coin_result = random.choice(['heads', 'tails'])
            result = coin_result
            
            if choice == coin_result:
                win = bet * 2
                new_balance = balance - bet + win
                message = f"🎉 Вы угадали! Выигрыш {win} копейка!"
                result_type = 'win'
            else:
                win = 0
                new_balance = balance - bet
                message = f"😔 Не угадали. Выпал {'орел' if coin_result == 'heads' else 'решка'}"
                result_type = 'lose'
            
            update_user_balance(user_id, new_balance)
            add_game_history(user_id, 'coinflip', bet, win, result_type)
            balance = new_balance
    
    # Получаем статистику
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT 
            COUNT(CASE WHEN result = 'win' THEN 1 END) as wins,
            COUNT(*) as total
           FROM game_history 
           WHERE user_id = ? AND game_type = 'coinflip' ''',
        (user_id,)
    )
    stats_result = cursor.fetchone()
    conn.close()
    
    if stats_result:
        stats['wins'] = stats_result[0]
        stats['total'] = stats_result[1]
    
    return render_template('coinflip.html',
                         balance=balance,
                         message=message,
                         result=result,
                         stats=stats)


@app.route('/dice', methods=['GET', 'POST'])
def dice_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    balance = get_user_balance(user_id)
    message = ""
    player_dice = [1, 1]
    dealer_dice = [1, 1]
    player_score = 2
    dealer_score = 2
    rolled = False
    
    if request.method == 'POST':
        bet = int(request.form.get('bet', 10))
        
        if bet > balance:
            message = "❌ Недостаточно средств!"
        else:
            rolled = True
            # Бросаем кости
            player_dice = [random.randint(1, 6) for _ in range(2)]
            dealer_dice = [random.randint(1, 6) for _ in range(2)]
            
            player_score = sum(player_dice)
            dealer_score = sum(dealer_dice)
            
            # Проверяем дубль у игрока
            player_double = player_dice[0] == player_dice[1]
            
            if player_score > dealer_score:
                if player_double:
                    win = bet * 3
                    multiplier = "x3 (дубль!)"
                else:
                    win = bet * 2
                    multiplier = "x2"
                
                new_balance = balance - bet + win
                message = f"🎉 Вы выиграли {win} копейка! ({multiplier})"
                result_type = 'win'
                add_game_history(user_id, 'dice', bet, win, f'win_{multiplier}')
                
            elif player_score < dealer_score:
                win = 0
                new_balance = balance - bet
                message = f"😔 Дилер выиграл! ({dealer_score} vs {player_score})"
                result_type = 'lose'
                add_game_history(user_id, 'dice', bet, 0, 'lose')

            else:
                # Ничья
                new_balance = balance  # Возвращаем ставку
                message = "🤝 Ничья! Ставка возвращена"
                result_type = 'push'
                add_game_history(user_id, 'dice', bet, 0, 'push')
            
            update_user_balance(user_id, new_balance)
            balance = new_balance
    
    return render_template('dice.html',
                         balance=balance,
                         message=message,
                         player_dice=player_dice,
                         dealer_dice=dealer_dice,
                         player_score=player_score,
                         dealer_score=dealer_score,
                         rolled=rolled)

@app.route('/reset_balance')
def reset_balance():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    update_user_balance(user_id, 1000)
    
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM game_history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    if 'blackjack_deck' in session:
        del session['blackjack_deck']
    if 'player_hand' in session:
        del session['player_hand']
    if 'dealer_hand' in session:
        del session['dealer_hand']
    if 'game_state' in session:
        del session['game_state']
    if 'blackjack_bet' in session:
        del session['blackjack_bet']
    
    flash('Баланс сброшен до 1000 копейка', 'success')
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5005)
