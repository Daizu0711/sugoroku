import streamlit as st
import random
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components

# ページ設定
st.set_page_config(page_title="年間収益勝ち組ゲーム", layout="wide")

# セッション状態の初期化
if 'game_started' not in st.session_state:
    st.session_state.game_started = False
    st.session_state.current_player = 0
    st.session_state.turn = 1
    st.session_state.players = []
    st.session_state.board = []
    st.session_state.num_players = 4
    st.session_state.dice_rolled = False
    st.session_state.investment_pending = False
    st.session_state.investment_amount = 0
    st.session_state.investment_type = ""
    st.session_state.investment_position = 0
    st.session_state.candlestick_data = []
    st.session_state.current_candle = 0
    st.session_state.sell_decision_made = False
    st.session_state.investment_asset_value = 0

# マスの種類と効果
MASS_TYPES = {
    'nothing': {'name': '何もなし', 'color': '#FFFFFF', 'emoji': '⚪', 'weight': 20},
    'profit': {'name': '利益マス', 'color': '#90EE90', 'emoji': '💰', 'weight': 15},
    'loss': {'name': '損失マス', 'color': '#FFB6C1', 'emoji': '💸', 'weight': 15},
    'debt': {'name': '借金マス', 'color': '#FFD700', 'emoji': '💳', 'weight': 10},
    'investment': {'name': '投資マス', 'color': '#87CEEB', 'emoji': '🏢', 'weight': 10},
    'bonus': {'name': 'ボーナスタイム', 'color': '#FF69B4', 'emoji': '🎉', 'weight': 2}
}

# プレイヤーの色と絵文字
PLAYER_COLORS = ['🔴', '🔵', '🟢', '🟡']

# 利益イベント
PROFIT_EVENTS = [
    {'reason': '広告収益が好調！', 'amount': (500, 2000)},
    {'reason': '新商品が大ヒット！', 'amount': (1000, 3000)},
    {'reason': 'サービス契約成立！', 'amount': (800, 2500)},
    {'reason': 'リピーター増加！', 'amount': (600, 1800)},
    {'reason': '大口契約獲得！', 'amount': (1500, 4000)},
]

# 損失イベント
LOSS_EVENTS = [
    {'reason': '広告費の支出', 'amount': (300, 1500)},
    {'reason': '接待・飲み会費', 'amount': (200, 1000)},
    {'reason': '設備のメンテナンス費用', 'amount': (400, 1800)},
    {'reason': '人件費の増加', 'amount': (500, 2000)},
    {'reason': 'クレーム対応費用', 'amount': (300, 1200)},
]

# プレイヤークラス
class Player:
    def __init__(self, name, number):
        self.name = name
        self.number = number
        self.position = 0
        self.cash = 5000
        self.assets = {'建物・土地': 0, '在庫・商品': 0}
        self.liabilities = {'借金': 0}
        self.revenue = 0
        self.expenses = 0
        self.cf_operations = 0
        self.cf_investment = 0
        self.cf_financing = 0
        self.history = []
    
    def get_total_assets(self):
        return self.cash + sum(self.assets.values())
    
    def get_equity(self):
        return self.get_total_assets() - self.liabilities['借金']
    
    def get_profit(self):
        return self.revenue - self.expenses
    
    def add_transaction(self, transaction_type, amount, reason):
        self.history.append({
            'turn': st.session_state.turn,
            'type': transaction_type,
            'amount': amount,
            'reason': reason,
            'cash_after': self.cash
        })

# ボードの生成
def generate_board():
    board = []
    mass_list = []
    
    for mass_type, info in MASS_TYPES.items():
        mass_list.extend([mass_type] * info['weight'])
    
    random.shuffle(mass_list)
    
    # 72マス生成
    for i in range(72):
        if i < len(mass_list):
            board.append(mass_list[i])
        else:
            board.append('nothing')
    
    # 投資マスを5マス確実に配置
    investment_positions = random.sample(range(72), 5)
    for pos in investment_positions:
        board[pos] = 'investment'
    
    # ボーナスタイムを2マス確実に配置
    bonus_positions = random.sample([i for i in range(72) if board[i] != 'investment'], 2)
    for pos in bonus_positions:
        board[pos] = 'bonus'
    
    return board

# すごろくボードの表示
def display_board():
    st.subheader("🎲 すごろくボード")
    
    # プレイヤーの位置を取得
    player_positions = {}
    for player in st.session_state.players:
        if player.position not in player_positions:
            player_positions[player.position] = []
        player_positions[player.position].append(player.number)
    
    # HTMLコンポーネントとして表示
    board_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {
        margin: 0;
        padding: 10px;
        font-family: sans-serif;
    }
    .board-container {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 5px;
        max-width: 100%;
    }
    .board-cell {
        aspect-ratio: 1;
        border: 3px solid #333;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: bold;
        padding: 3px;
        position: relative;
        box-sizing: border-box;
    }
    .cell-number {
        position: absolute;
        top: 2px;
        left: 3px;
        font-size: 9px;
        color: #666;
        font-weight: bold;
    }
    .cell-emoji {
        font-size: 20px;
        margin: 2px 0;
    }
    .cell-players {
        font-size: 14px;
        margin-top: 2px;
    }
    .current-player-cell {
        box-shadow: 0 0 15px 5px #FFD700;
        animation: pulse 1.5s infinite;
        border: 3px solid #FFA500;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 15px 5px #FFD700; }
        50% { box-shadow: 0 0 25px 8px #FFA500; }
    }
    .legend {
        margin-top: 15px;
        padding: 15px;
        background-color: #f0f0f0;
        border-radius: 10px;
    }
    .legend-item {
        display: inline-block;
        margin-right: 15px;
        font-size: 14px;
    }
    </style>
    </head>
    <body>
    <div class="board-container">
    """
    
    # 蛇行パターンで表示（上段左→右、下段右→左、を繰り返す）
    rows = 6
    cols = 12
    for row in range(rows):
        for col in range(cols):
            if row % 2 == 0:  # 偶数行は左から右
                pos = row * cols + col
            else:  # 奇数行は右から左
                pos = row * cols + (cols - 1 - col)
            
            if pos < 72:
                mass_type = st.session_state.board[pos]
                mass_info = MASS_TYPES[mass_type]
                
                # プレイヤーがいるか確認
                players_here = player_positions.get(pos, [])
                player_markers = ''.join([PLAYER_COLORS[p] for p in players_here])
                
                # 現在のプレイヤーがいるセルをハイライト
                current_class = ''
                if len(st.session_state.players) > st.session_state.current_player:
                    if st.session_state.players[st.session_state.current_player].position == pos:
                        current_class = 'current-player-cell'
                
                board_html += f"""
                <div class="board-cell {current_class}" style="background-color: {mass_info['color']};">
                    <span class="cell-number">{pos}</span>
                    <span class="cell-emoji">{mass_info['emoji']}</span>
                    <span class="cell-players">{player_markers}</span>
                </div>
                """
    
    board_html += """
    </div>
    <div class="legend">
        <strong>📋 凡例：</strong><br><br>
    """
    
    for mass_type, info in MASS_TYPES.items():
        board_html += f'<span class="legend-item"><span style="font-size: 18px;">{info["emoji"]}</span> {info["name"]}</span>'
    
    board_html += "<br><br><strong>プレイヤー：</strong><br><br>"
    
    for i, player in enumerate(st.session_state.players):
        board_html += f'<span class="legend-item"><span style="font-size: 18px;">{PLAYER_COLORS[i]}</span> {player.name}</span>'
    
    board_html += """
    </div>
    </body>
    </html>
    """
    
    # HTMLコンポーネントとして表示
    components.html(board_html, height=650, scrolling=False)

# サイコロを振る
def roll_dice():
    return random.randint(1, 6)

# ボトルフリップ
def bottle_flip():
    return random.choice([True, False])

# マスの効果を適用
def apply_mass_effect(player, mass_type):
    messages = []
    
    if mass_type == 'nothing':
        messages.append('何も起こりませんでした。')
    
    elif mass_type == 'profit':
        event = random.choice(PROFIT_EVENTS)
        amount = random.randint(event['amount'][0], event['amount'][1])
        player.cash += amount
        player.revenue += amount
        player.cf_operations += amount
        player.add_transaction('収益', amount, event['reason'])
        messages.append(f"💰 {event['reason']} +{amount:,}円")
    
    elif mass_type == 'loss':
        event = random.choice(LOSS_EVENTS)
        amount = random.randint(event['amount'][0], event['amount'][1])
        player.cash -= amount
        player.expenses += amount
        player.cf_operations -= amount
        player.add_transaction('費用', -amount, event['reason'])
        messages.append(f"💸 {event['reason']} -{amount:,}円")
    
    elif mass_type == 'debt':
        amount = random.randint(1000, 5000)
        player.cash += amount
        player.liabilities['借金'] += amount
        player.cf_financing += amount
        player.add_transaction('借入', amount, '運転資金の借入')
        messages.append(f"💳 借金をしました +{amount:,}円（負債増加）")
    
    elif mass_type == 'investment':
        investment_type = random.choice(['建物・土地', '在庫・商品'])
        amount = random.randint(1000, 3000)
        st.session_state.investment_amount = amount
        st.session_state.investment_type = investment_type
        st.session_state.investment_position = player.position
        st.session_state.investment_pending = True
        messages.append(f"🏢 {investment_type}に投資しますか？ 投資額: {amount:,}円")
    
    elif mass_type == 'bonus':
        messages.append("🎉 ボーナスタイム！ボトルフリップチャレンジ！")
    
    return messages

# ボーナスタイム実行
def execute_bonus_time(player):
    dice = roll_dice()
    st.write(f"🎲 サイコロの目: {dice}")
    
    success_count = 0
    results = []
    
    for i in range(dice):
        if bottle_flip():
            success_count += 1
            results.append("✅ 成功")
        else:
            results.append("❌ 失敗")
    
    st.write(f"ボトルフリップ結果: {' | '.join(results)}")
    
    bonus = success_count * 500
    if bonus > 0:
        player.cash += bonus
        player.revenue += bonus
        player.cf_operations += bonus
        player.add_transaction('ボーナス', bonus, 'ボトルフリップ成功')
        st.success(f"🎊 ボーナス獲得: +{bonus:,}円")
    else:
        st.info("残念！ボーナスなし")

# ローソク足チャートデータの生成
def generate_candlestick_data():
    # 50本のローソク足を生成
    data = []
    base_price = random.uniform(100, 500)
    
    for i in range(50):
        # ランダムな価格変動をシミュレート
        open_price = base_price if i == 0 else data[-1]['close']
        change = random.uniform(-0.1, 0.1)  # -10% 〜 +10% の変動
        close_price = open_price * (1 + change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.05))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.05))
        
        data.append({
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'color': 'green' if close_price >= open_price else 'red'
        })
        
        base_price = close_price
    
    return data

# 財務諸表の表示
def display_financial_statement(player):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 貸借対照表（B/S）")
        
        # 資産の部
        st.write("**【資産の部】**")
        st.write(f"現金: {player.cash:,}円")
        for asset, value in player.assets.items():
            st.write(f"{asset}: {value:,}円")
        total_assets = player.get_total_assets()
        st.write(f"**資産合計: {total_assets:,}円**")
        
        st.write("")
        
        # 負債・純資産の部
        st.write("**【負債・純資産の部】**")
        st.write(f"借金: {player.liabilities['借金']:,}円")
        equity = player.get_equity()
        st.write(f"**純資産: {equity:,}円**")
        st.write(f"**負債・純資産合計: {total_assets:,}円**")
    
    with col2:
        st.subheader("💵 損益計算書（P/L）")
        st.write(f"収益: {player.revenue:,}円")
        st.write(f"費用: {player.expenses:,}円")
        st.write("─" * 30)
        profit = player.get_profit()
        if profit >= 0:
            st.write(f"**利益: {profit:,}円** ✨")
        else:
            st.write(f"**損失: {profit:,}円** 😰")
        
        st.write("")
        
        st.subheader("💰 キャッシュフロー計算書（C/F）")
        st.write(f"営業CF: {player.cf_operations:,}円")
        st.write(f"投資CF: {player.cf_investment:,}円")
        st.write(f"財務CF: {player.cf_financing:,}円")

# ゲーム開始画面
def game_start_screen():
    st.title("🎮 年間収益勝ち組ゲーム")
    st.subheader("会社経営すごろくゲーム")
    
    st.write("---")
    st.write("### ゲームルール")
    st.write("- 初期資金: 5,000円")
    st.write("- 12ターン経営を行い、最も純資産が多いプレイヤーが勝利！")
    st.write("- サイコロを振ってマスを進み、止まったマスの指示に従います")
    st.write("- ボーナスタイムではボトルフリップに挑戦！")
    st.write("")
    
    num_players = st.number_input("プレイヤー数", min_value=2, max_value=4, value=4)
    
    st.write("### プレイヤー名入力")
    player_names = []
    cols = st.columns(num_players)
    for i in range(num_players):
        with cols[i]:
            name = st.text_input(f"プレイヤー{i+1}", value=f"プレイヤー{i+1}", key=f"player_{i}")
            player_names.append(name)
    
    if st.button("🚀 ゲームスタート", type="primary", use_container_width=True):
        st.session_state.num_players = num_players
        st.session_state.players = [Player(name, i) for i, name in enumerate(player_names)]
        st.session_state.board = generate_board()
        st.session_state.game_started = True
        st.session_state.current_player = 0
        st.session_state.turn = 1
        st.session_state.bonus_mode = False
        st.session_state.dice_rolled = False
        st.session_state.investment_pending = False
        st.session_state.investment_amount = 0
        st.session_state.investment_type = ""
        st.session_state.investment_position = 0
        st.session_state.candlestick_data = []
        st.session_state.current_candle = 0
        st.session_state.sell_decision_made = False
        st.session_state.investment_asset_value = 0
        st.rerun()

# メインゲーム画面
def main_game_screen():
    st.title("🎮 年間収益勝ち組ゲーム")
    
    # ターン表示
    progress = st.session_state.turn / 12
    st.progress(progress, text=f"ターン {st.session_state.turn}/12")
    
    # すごろくボードの表示
    display_board()
    
    st.write("---")
    
    # 現在のプレイヤー
    current_player = st.session_state.players[st.session_state.current_player]
    
    st.header(f"🎯 {PLAYER_COLORS[current_player.number]} {current_player.name} のターン")
    
    # プレイヤーの状態表示
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("現在位置", f"{current_player.position}マス目")
    with col2:
        st.metric("現金", f"{current_player.cash:,}円")
    with col3:
        st.metric("純資産", f"{current_player.get_equity():,}円")
    with col4:
        st.metric("利益", f"{current_player.get_profit():,}円")
    
    st.write("---")
    
    # サイコロを振るボタン（まだ振っていない場合のみ表示）
    if not st.session_state.dice_rolled:
        if st.button("🎲 サイコロを振る", type="primary", use_container_width=True):
            dice = roll_dice()
            st.session_state.last_dice = dice
            
            # 位置を更新
            old_position = current_player.position
            current_player.position = (current_player.position + dice) % 72
            
            st.success(f"🎲 サイコロの目: {dice}")
            st.info(f"📍 {old_position}マス目 → {current_player.position}マス目に移動しました")
            
            # マスの効果を適用
            mass_type = st.session_state.board[current_player.position]
            mass_name = MASS_TYPES[mass_type]['name']
            
            st.write(f"### 📋 {mass_name}")
            
            if mass_type == 'bonus':
                st.session_state.bonus_mode = True
            else:
                messages = apply_mass_effect(current_player, mass_type)
                for msg in messages:
                    st.write(msg)
                st.session_state.bonus_mode = False
            
            st.session_state.dice_rolled = True
            st.rerun()
    
    # サイコロを振った後の表示
    if st.session_state.dice_rolled:
        st.success(f"✅ サイコロの目: {st.session_state.last_dice}")
        
        mass_type = st.session_state.board[current_player.position]
        mass_name = MASS_TYPES[mass_type]['name']
        st.info(f"📍 現在のマス: {mass_name}")
    
    # ボーナスモード
    if st.session_state.get('bonus_mode', False):
        st.write("### 🎉 ボーナスタイム！")
        st.write("ボトルフリップに挑戦しましょう！")
        
        if st.button("🍾 ボトルフリップ開始", type="primary"):
            execute_bonus_time(current_player)
            st.session_state.bonus_mode = False
    
    # 投資決定モード
    if st.session_state.get('investment_pending', False):
        st.write("### 🏢 投資オプション")
        st.write(f"投資タイプ: {st.session_state.investment_type}")
        st.write(f"投資額: {st.session_state.investment_amount:,}円")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 購入する", type="primary"):
                current_player = st.session_state.players[st.session_state.current_player]
                if current_player.cash >= st.session_state.investment_amount:
                    current_player.cash -= st.session_state.investment_amount
                    current_player.assets[st.session_state.investment_type] += st.session_state.investment_amount
                    current_player.cf_investment -= st.session_state.investment_amount
                    current_player.add_transaction('投資', -st.session_state.investment_amount, f'{st.session_state.investment_type}の取得')
                    st.success(f"🏢 {st.session_state.investment_type}に投資しました -{st.session_state.investment_amount:,}円（資産増加）")
                    
                    # ローソク足チャートの生成
                    st.session_state.candlestick_data = generate_candlestick_data()
                    st.session_state.current_candle = 0
                    st.session_state.sell_decision_made = False
                    st.session_state.investment_asset_value = st.session_state.investment_amount
                else:
                    st.error(f"❌ 資金不足で投資できませんでした（必要額: {st.session_state.investment_amount:,}円）")
                
                st.session_state.investment_pending = False
                st.rerun()
        
        with col2:
            if st.button("❌ 購入しない"):
                st.info("投資を見送りました")
                st.session_state.investment_pending = False
                st.rerun()
    
    # ローソク足売却モード
    if st.session_state.get('candlestick_data', []) and not st.session_state.get('sell_decision_made', False):
        st.write("### 📈 投資資産の売却")
        st.write("ローソク足チャートが表示されています。50本のローソク足のいずれかで資産を売却してください。")
        
        # ローソク足チャートの表示
        if st.session_state.candlestick_data:
            # 現在のローソク足までのデータのみ表示
            visible_data = st.session_state.candlestick_data[:st.session_state.current_candle + 1]
            
            fig = go.Figure(data=go.Candlestick(
                x=list(range(len(visible_data))),
                open=[candle['open'] for candle in visible_data],
                high=[candle['high'] for candle in visible_data],
                low=[candle['low'] for candle in visible_data],
                close=[candle['close'] for candle in visible_data]
            ))
            
            fig.update_layout(
                title="投資資産価値チャート",
                xaxis_title="ローソク足番号",
                yaxis_title="価格",
                width=800,
                height=400,
                xaxis_rangeslider_visible=False
            )
            
            st.plotly_chart(fig)
            
            # 現在の価値を表示
            current_price = visible_data[-1]['close']
            initial_price = st.session_state.candlestick_data[0]['close']
            current_value = st.session_state.investment_asset_value * (current_price / initial_price)
            profit_loss = current_value - st.session_state.investment_asset_value
            
            st.write(f"**現在のローソク足:** {st.session_state.current_candle + 1}/50")
            st.write(f"**投資額:** {st.session_state.investment_asset_value:,}円")
            st.write(f"**現在の価値:** {int(current_value):,}円")
            if profit_loss >= 0:
                st.write(f"**損益:** +{int(profit_loss):,}円 📈")
            else:
                st.write(f"**損益:** {int(profit_loss):,}円 📉")
            
            # 売却ポイントの選択
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⏭️ 次へ"):
                    if st.session_state.current_candle < len(st.session_state.candlestick_data) - 1:
                        st.session_state.current_candle += 1
                        st.rerun()
                    else:
                        st.warning("すでに最後のローソク足です")
            
            with col2:
                if st.button("💰 ここで売却", type="primary"):
                    # 売却処理
                    current_player = st.session_state.players[st.session_state.current_player]
                    sell_price = st.session_state.candlestick_data[st.session_state.current_candle]['close']
                    sell_value = st.session_state.investment_asset_value * (sell_price / st.session_state.candlestick_data[0]['close'])
                    
                    current_player.cash += int(sell_value)
                    current_player.assets[st.session_state.investment_type] -= st.session_state.investment_asset_value
                    if current_player.assets[st.session_state.investment_type] < 0:
                        current_player.assets[st.session_state.investment_type] = 0
                    
                    current_player.cf_investment += int(sell_value)
                    
                    profit_or_loss = int(sell_value) - st.session_state.investment_asset_value
                    if profit_or_loss >= 0:
                        current_player.add_transaction('売却益', int(sell_value), f'{st.session_state.investment_type}の売却 (利益: +{profit_or_loss:,}円)')
                    else:
                        current_player.add_transaction('売却損', int(sell_value), f'{st.session_state.investment_type}の売却 (損失: {profit_or_loss:,}円)')
                    
                    st.success(f"🏢 {st.session_state.investment_type}を売却しました +{int(sell_value):,}円")
                    
                    # 状態をリセット
                    st.session_state.candlestick_data = []
                    st.session_state.current_candle = 0
                    st.session_state.sell_decision_made = True
                    st.session_state.investment_asset_value = 0
                    
                    st.rerun()
            
            with col3:
                if st.button("🔚 最後まで見る"):
                    st.session_state.current_candle = len(st.session_state.candlestick_data) - 1
                    st.rerun()
    
    # 財務諸表表示
    if st.session_state.dice_rolled and not st.session_state.get('investment_pending', False) and not st.session_state.get('candlestick_data', []):
        st.write("---")
        display_financial_statement(current_player)
    
    # ターン終了ボタン（サイコロを振った後のみ表示）
    if st.session_state.dice_rolled and not st.session_state.get('bonus_mode', False) and not st.session_state.get('investment_pending', False) and not st.session_state.get('candlestick_data', []):
        st.write("---")
        if st.button("✅ ターン終了 - 次のプレイヤーへ", use_container_width=True, type="primary"):
            # 次のプレイヤーへ
            st.session_state.current_player = (st.session_state.current_player + 1) % st.session_state.num_players
            
            # 全プレイヤーが終わったらターン進行
            if st.session_state.current_player == 0:
                st.session_state.turn += 1
            
            st.session_state.last_dice = None
            st.session_state.dice_rolled = False
            
            # ゲーム終了判定
            if st.session_state.turn > 12:
                st.session_state.game_finished = True
            
            st.rerun()
    
    # サイドバーに全プレイヤーの状況表示
    with st.sidebar:
        st.header("👥 プレイヤー状況")
        for i, player in enumerate(st.session_state.players):
            is_current = i == st.session_state.current_player
            with st.expander(f"{PLAYER_COLORS[i]} {player.name} {'🎯 (現在)' if is_current else ''}", expanded=is_current):
                st.write(f"位置: {player.position}マス目")
                st.write(f"現金: {player.cash:,}円")
                st.write(f"純資産: {player.get_equity():,}円")
                st.write(f"利益: {player.get_profit():,}円")

# ゲーム終了画面
def game_end_screen():
    st.title("🏆 ゲーム終了！")
    st.balloons()
    
    # 順位を計算
    rankings = sorted(st.session_state.players, key=lambda p: p.get_equity(), reverse=True)
    
    st.subheader("最終順位")
    
    medals = ["🥇", "🥈", "🥉", "4️⃣"]
    
    for i, player in enumerate(rankings):
        medal = medals[i] if i < len(medals) else f"{i+1}位"
        with st.expander(f"{medal} {PLAYER_COLORS[player.number]} {player.name} - 純資産 {player.get_equity():,}円", expanded=(i==0)):
            display_financial_statement(player)
            
            if player.history:
                st.write("### 📜 取引履歴")
                df = pd.DataFrame(player.history)
                st.dataframe(df, use_container_width=True)
    
    st.write("---")
    
    if st.button("🔄 新しいゲームを始める", type="primary", use_container_width=True):
        # セッションステートをリセット
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# メイン処理
def main():
    if not st.session_state.game_started:
        game_start_screen()
    elif st.session_state.get('game_finished', False):
        game_end_screen()
    else:
        main_game_screen()

if __name__ == "__main__":
    main()
