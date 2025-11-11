from flask import Flask, render_template, request, session, redirect, url_for
import random
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'demo_casino_secret_key_2024'

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            session_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            game_type TEXT,
            bet_amount INTEGER,
            win_amount INTEGER,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES users (session_id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.before_request
def init_session():
    init_db()
    
    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()
        
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO users (session_id, balance) VALUES (?, ?)',
            (session['user_id'], 1000)
        )
        conn.commit()
        conn.close()

def get_user_balance():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT balance FROM users WHERE session_id = ?',
        (session['user_id'],)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 1000

def update_user_balance(new_balance):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET balance = ? WHERE session_id = ?',
        (new_balance, session['user_id'])
    )
    conn.commit()
    conn.close()

def add_game_history(game_type, bet_amount, win_amount, result):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO game_history 
           (session_id, game_type, bet_amount, win_amount, result) 
           VALUES (?, ?, ?, ?, ?)''',
        (session['user_id'], game_type, bet_amount, win_amount, result)
    )
    conn.commit()
    conn.close()

def get_game_history(limit=5):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT game_type, bet_amount, win_amount, result, created_at 
           FROM game_history 
           WHERE session_id = ? 
           ORDER BY created_at DESC 
           LIMIT ?''',
        (session['user_id'], limit)
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

class BlackjackGame:
    @staticmethod
    def new_deck():
        """Создает новую колоду карт"""
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
        """Вычисляет стоимость руки"""
        value = 0
        aces = 0
        
        for card in hand:
            card_value = card[:-1]  # Убираем масть
            if card_value in ['J', 'Q', 'K']:
                value += 10
            elif card_value == 'A':
                aces += 1
                value += 11
            else:
                value += int(card_value)
        
        # Корректировка тузов
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
            
        return value

    @staticmethod
    def deal_initial_cards(deck):
        """Раздает начальные карты"""
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        return player_hand, dealer_hand, deck

    @staticmethod
    def hit(hand, deck):
        """Добавляет карту в руку"""
        hand.append(deck.pop())
        return hand, deck

    @staticmethod
    def dealer_play(dealer_hand, deck):
        """Логика дилера"""
        while BlackjackGame.calculate_hand_value(dealer_hand) < 17:
            dealer_hand, deck = BlackjackGame.hit(dealer_hand, deck)
        return dealer_hand, deck

    @staticmethod
    def determine_winner(player_value, dealer_value):
        """Определяет победителя"""
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

@app.route('/')
def index():
    balance = get_user_balance()
    history = get_game_history()
    return render_template('index.html', balance=balance, history=history)

@app.route('/slots', methods=['GET', 'POST'])
def slots_page():
    balance = get_user_balance()
    message = ""
    reels = ['?', '?', '?']
    
    if request.method == 'POST':
        bet = int(request.form.get('bet', 10))
        
        if bet > balance:
            message = "❌ Недостаточно средств!"
        else:
            symbols = ['🍒', '🍋', '🍊', '⭐', '🔔', '💎']
            reels = [random.choice(symbols) for _ in range(3)]
            
            # Вычисление выигрыша
            if reels[0] == reels[1] == reels[2]:
                multiplier = 10 if reels[0] == '💎' else 5
                win = bet * multiplier
            elif reels[0] == reels[1] or reels[1] == reels[2]:
                win = bet * 2
            else:
                win = 0
            
            # Обновляем баланс
            new_balance = balance - bet + win
            update_user_balance(new_balance)
            
            # Сохраняем в историю
            add_game_history('slots', bet, win, str(reels))
            
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
    balance = get_user_balance()
    message = ""
    
    # Инициализация состояния игры
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
                # Раздаем карты
                player_hand, dealer_hand, deck = BlackjackGame.deal_initial_cards(session['blackjack_deck'])
                session['player_hand'] = player_hand
                session['dealer_hand'] = dealer_hand
                session['blackjack_deck'] = deck
                session['blackjack_bet'] = bet
                session['game_state'] = 'player_turn'
                
                # Списываем ставку
                new_balance = balance - bet
                update_user_balance(new_balance)
                balance = new_balance
                
                # Проверяем блэкджек
                player_value = BlackjackGame.calculate_hand_value(player_hand)
                if player_value == 21:
                    session['game_state'] = 'dealer_turn'
                    # Дилер открывает карты
                    session['dealer_hand'], session['blackjack_deck'] = BlackjackGame.dealer_play(
                        session['dealer_hand'], session['blackjack_deck']
                    )
                    dealer_value = BlackjackGame.calculate_hand_value(session['dealer_hand'])
                    
                    if dealer_value == 21:
                        # Ничья
                        new_balance = balance + bet
                        update_user_balance(new_balance)
                        message = "🤝 Оба имеют блэкджек! Ничья!"
                        session['game_state'] = 'game_over'
                        add_game_history('blackjack', bet, 0, 'push')
                    else:
                        # Игрок выиграл блэкджек
                        win_amount = int(bet * 2.5)  # Блэкджек платит 3:2
                        new_balance = balance + win_amount
                        update_user_balance(new_balance)
                        message = f"🎉 Блэкджек! Вы выиграли {win_amount} копейка!"
                        session['game_state'] = 'game_over'
                        add_game_history('blackjack', bet, win_amount - bet, 'blackjack')
                    balance = new_balance
        
        elif action == 'hit':
            # Игрок берет карту
            session['player_hand'], session['blackjack_deck'] = BlackjackGame.hit(
                session['player_hand'], session['blackjack_deck']
            )
            
            player_value = BlackjackGame.calculate_hand_value(session['player_hand'])
            if player_value > 21:
                # Перебор
                message = "💥 Перебор! Дилер выиграл!"
                session['game_state'] = 'game_over'
                add_game_history('blackjack', session['blackjack_bet'], 0, 'bust')
        
        elif action == 'stand':
            # Ход дилера
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
                update_user_balance(new_balance)
                message = f"🎉 Вы выиграли {win_amount} копейка!"
                add_game_history('blackjack', session['blackjack_bet'], session['blackjack_bet'], 'win')
                balance = new_balance
            elif winner == "dealer":
                message = "😞 Дилер выиграл!"
                add_game_history('blackjack', session['blackjack_bet'], 0, 'lose')
            else:  # push
                new_balance = balance + session['blackjack_bet']
                update_user_balance(new_balance)
                message = "🤝 Ничья! Ставка возвращена"
                add_game_history('blackjack', session['blackjack_bet'], 0, 'push')
                balance = new_balance
            
            session['game_state'] = 'game_over'
    
    # Подготавливаем данные для отображения
    player_hand = session.get('player_hand', [])
    dealer_hand = session.get('dealer_hand', [])
    game_state = session.get('game_state', 'betting')
    
    # Вычисляем значения рук
    player_value = BlackjackGame.calculate_hand_value(player_hand) if player_hand else 0
    dealer_value = BlackjackGame.calculate_hand_value(dealer_hand) if dealer_hand else 0
    
    # Для дилера скрываем вторую карту до конца игры
    show_dealer_value = game_state in ['dealer_turn', 'game_over']
    dealer_display_hand = dealer_hand.copy()
    if not show_dealer_value and len(dealer_display_hand) > 1:
        dealer_display_hand[1] = '??'  # Скрытая карта
    
    return render_template('blackjack.html',
                         balance=balance,
                         player_hand=player_hand,
                         dealer_hand=dealer_display_hand,
                         player_value=player_value,
                         dealer_value=dealer_value if show_dealer_value else '?',
                         message=message,
                         game_state=game_state,
                         current_bet=session.get('blackjack_bet', 0))

@app.route('/reset_balance')
def reset_balance():
    update_user_balance(1000)
    
    # Очищаем историю игр для этого пользователя
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM game_history WHERE session_id = ?',
        (session['user_id'],)
    )
    conn.commit()
    conn.close()
    
    # Сбрасываем состояние блэкджека
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
    
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5006)