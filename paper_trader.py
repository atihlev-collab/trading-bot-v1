from config import START_BALANCE
from datetime import datetime
from market_data import get_price


class PaperTrader:

    def __init__(self):

        self.start_balance = START_BALANCE

        self.balance = self.start_balance

        self.positions = {}

        self.closed_trades = []

        self.realized_pnl = 0.0

        self.open_pnl = 0.0

        self.total_trades = 0

        self.wins = 0

        self.losses = 0

        self.max_open_positions = 2

        self.risk_percent = 2.0

        self.daily_loss = 0.0

        self.max_daily_loss = 5.0

    # ==========================================
    # POSITION CHECK
    # ==========================================

    def has_position(self, symbol):

        return symbol in self.positions

    # ==========================================
    # FREE SLOTS
    # ==========================================

    def free_slots(self):

        return self.max_open_positions - len(self.positions)

    # ==========================================
    # EQUITY
    # ==========================================

    def equity(self):

        return self.balance + self.open_pnl

    # ==========================================
    # POSITION SIZE
    # ==========================================

    def calculate_position_size(

        self,

        entry,

        stop,

    ):

        risk_amount = (
            self.balance *
            self.risk_percent /
            100
        )

        stop_distance = abs(
            entry - stop
        )

        if stop_distance <= 0:
            return 0

        quantity = (
            risk_amount /
            stop_distance
        )

        value = quantity * entry

        if value > self.balance:
            value = self.balance
            quantity = value / entry

        

        return round(quantity, 6)

    # ==========================================
    # OPEN POSITION
    # ==========================================

    def try_open_position(

        self,

        symbol,

        signal,

    ):

        if self.has_position(symbol):
            print("[FAIL] already has position")
            return False

        if len(self.positions) >= self.max_open_positions:
            print("[FAIL] max positions")
            return False

        entry = signal["close"]

        atr = signal["atr"]

        print(f"[DEBUG] entry={entry} atr={atr}")

        stop = entry - atr * 2

        take = entry + atr * 5

        quantity = self.calculate_position_size(

            entry,

            stop,

        )

        print(f"[DEBUG] quantity={quantity}")

        if quantity <= 0:
            print("[FAIL] quantity <= 0")
            return False

        value = quantity * entry

        ср, 29.07 в 15:33
Това какво значи

Python
ad50706e-2641-408f-80bc-c2afb1ed3a1e.py
Python
26dc97c5-a88c-434f-ae1f-d3e8351efdce.py
Python
карам подред да не забравя някой-
395d22e2-2a4c-459b-80db-88863cc45c3d.py
Python
d5623238-4d27-435c-a006-fe196b381a3d.py
Python
3cef5bf6-643a-4370-8d45-d187df045a33.py
Python
9514b634-5365-4eec-9a3d-441dc6b1828f.py
Python
3d47bc87-45ac-4c87-a8fc-1e2248220b42.py
Python
c06d0e7e-4294-41a9-b8a9-1b7f7d00215a.py
Python
c5edb416-25a6-4aa8-8112-5f0796f80554.py
Python
3c763209-47f7-4f10-995f-479ede1796ce.py
Python
587d6f25-04fa-40a4-8301-c486d8f65ac8.py
Python
в червено свети
4c701f1c-b8d4-43d6-a919-e173ca1e20e9.py
Python
afa7a0b1-5e12-4617-9a28-879af8724148.py
Python
e10ff154-7f07-4c6e-83b4-6474d5779063.py
Python
вчера 10:43
Абеее майна нали каза този блок да го заменя с друг, ти май пак не знаеш къде се намираш
Пак обърка нещо май-
А
Pasted text(20260806-082456).txt
Документ
Pasted text(20260806-083338).txt
Документ
Не става така-

Ето защо не отваря сделки.

Имаш:

BUY_SCORE = 75
WATCH_SCORE = 70
IGNORE_SCORE = 60

А логът показва:

BTCUSDT WATCH 61
ETHUSDT WATCH 61

Тоест ботът не е счупен. Той прави точно това, което си му казал:

75+ → BUY ❌
70–74 → WATCH ❌
60–69 → WATCH ← тук са твоите сигнали
под 60 → WAIT
Има два начина:
Вариант 1 (за тест)

Промени само:

BUY_SCORE = 60
WATCH_SCORE = 55
IGNORE_SCORE = 50

Ако веднага започне да отваря позиции, значи всичко останало работи.

Вариант 2 (това препоръчвам)

Оставяме BUY_SCORE = 75, но правим стратегията по-силна, за да дава повече точки при качествени сигнали.

Така няма да купува всяка монета, а само когато условията са наистина добри.

Моето предложение

Не пипай праговете.

Аз ще пренапиша точкуването така, че:

силен тренд = повече точки;
потвърждение от 1h и 4h = повече точки;
MACD + RSI + Volume да носят по-голяма тежест.

Така добрите монети ще стигат 80–95 точки, а слабите ще остават около 40–60.

Това е по-доброто решение за бот, който искаш да използваш дългосрочно.

Сега вече се вижда ясно.

Има два различни проблема:

1. Сделките се опитват да се отворят

Вижда се:

[TRY OPEN] BTCUSDT
[TRY OPEN] ETHUSDT
[TRY OPEN] ADAUSDT
...

Тоест main.py и strategy.py работят.

2. Но try_open_position() връща:
[OPEN RESULT] False

Това означава, че PaperTrader отказва сделката.

Има още един важен лог

На третата снимка се вижда:

POSITIONS: {
    ...
    'quantity': 12.428536,
    'value': 50.00000032799,
    ...
}

А балансът ти е 50 USDT.

Тоест стойността на позицията е:

50.00000032799

а проверката в try_open_position() е:

if value > self.balance + 0.01:
    return False

или балансът вече е почти 0 след първата сделка.

Но има нещо още по-важно.

Виждам:

[TRY OPEN] BTCUSDT
...
[TRY OPEN] ETHUSDT
...
[TRY OPEN] ADAUSDT

Не виждам нито един

[OPEN OK]

след тях.

Това означава, че try_open_position() връща False още преди да стигне до:

print(f"[OPEN OK] ...")
Сега ми трябва само едно.

Покажи ми цялата функция try_open_position() от текущия paper_trader.py.

Не стара версия, а тази, която е качена в GitHub в момента.

Убеден съм, че проблемът е вътре в тази функция и след като я видя, ще кажа точно кой return False се изпълнява.

from config import START_BALANCE
from datetime import datetime
from market_data import get_price


class PaperTrader:

    def __init__(self):

        self.start_balance = START_BALANCE

        self.balance = self.start_balance

        self.positions = {}

        self.closed_trades = []

        self.realized_pnl = 0.0

        self.open_pnl = 0.0

        self.total_trades = 0

        self.wins = 0

        self.losses = 0

        self.max_open_positions = 2

        self.risk_percent = 2.0

        self.daily_loss = 0.0

        self.max_daily_loss = 5.0

    # ==========================================
    # POSITION CHECK
    # ==========================================

    def has_position(self, symbol):

        return symbol in self.positions

    # ==========================================
    # FREE SLOTS
    # ==========================================

    def free_slots(self):

        return self.max_open_positions - len(self.positions)

    # ==========================================
    # EQUITY
    # ==========================================

    def equity(self):

        return self.balance + self.open_pnl

    # ==========================================
    # POSITION SIZE
    # ==========================================

    def calculate_position_size(

        self,

        entry,

        stop,

    ):

        risk_amount = (
            self.balance *
            self.risk_percent /
            100
        )

        stop_distance = abs(
            entry - stop
        )

        if stop_distance <= 0:
            return 0

        quantity = (
            risk_amount /
            stop_distance
        )

        value = quantity * entry

        if value > self.balance:
            value = self.balance
            quantity = value / entry

        

        return round(quantity, 6)

    # ==========================================
    # OPEN POSITION
    # ==========================================

    def try_open_position(

        self,

        symbol,

        signal,

    ):

        if self.has_position(symbol):
            return False

        if len(self.positions) >= self.max_open_positions:
            return False

        entry = signal["close"]

        atr = signal["atr"]

        stop = entry - atr * 2

        take = entry + atr * 5

        quantity = self.calculate_position_size(

            entry,

            stop,

        )

        if quantity <= 0:
            return False

        value = quantity * entry

        if value > self.balance + 0.01:
            print(
                f"[SKIP] {symbol} "
                f"value={value:.8f} "
                f"balance={self.balance:.8f}"
            )
            return False

        self.balance -= value

        print(
            f"[OPEN OK] {symbol} "
            f"qty={quantity} "
            f"value={value:.2f}"
        )

        self.positions[symbol] = {

            "entry": entry,

            "quantity": quantity,

            "value": value,

            "stop": stop,

            "take": take,

            "highest": entry,

            "break_even": False,

            "partial_taken": False,

            "opened": datetime.utcnow(),

        }

        self.total_trades += 1

        print(

            f"[OPEN] {symbol} "

            f"Entry={entry:.4f} "

            f"SL={stop:.4f} "

            f"TP={take:.4f}"

        )

        return True

    # ==========================================
    # UPDATE POSITION
    # ==========================================

    def update_position(
        self,
        symbol,
        price,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        # Update highest price

        if price > pos["highest"]:
            pos["highest"] = price

        # --------------------------
        # Break Even
        # --------------------------

        if (
            not pos["break_even"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.30
        ):

            pos["stop"] = pos["entry"]

            pos["break_even"] = True

            print(
                f"[BE] {symbol}"
            )

        # --------------------------
        # Trailing Stop
        # --------------------------

        trail = pos["highest"] * 0.985

        if trail > pos["stop"]:

            pos["stop"] = trail

        # --------------------------
        # Partial TP
        # --------------------------

        if (
            not pos["partial_taken"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.60
        ):

            qty = pos["quantity"] / 2

            pnl = (
                (price - pos["entry"])
                * qty
            )

            self.balance += qty * price

            self.realized_pnl += pnl

            pos["quantity"] -= qty

            pos["partial_taken"] = True

            print(
                f"[PARTIAL] {symbol} "
                f"PnL={pnl:.2f}"
            )

        # --------------------------
        # Stop Loss
        # --------------------------

        if price <= pos["stop"]:

            return self.close_position(
                symbol,
                price,
                "STOP",
            )

        # --------------------------
        # Take Profit
        # --------------------------

        if price >= pos["take"]:

            return self.close_position(
                symbol,
                price,
                "TARGET",
            )

        # --------------------------
        # Open P/L
        # --------------------------

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            current_price = get_price(sym)

            self.open_pnl += (
                (current_price - p["entry"])
                * p["quantity"]
            )

        return None

    # ==========================================
    # CLOSE POSITION
    # ==========================================

    def close_position(
        self,
        symbol,
        price,
        reason,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)

        value = price * pos["quantity"]

        pnl = (
            price - pos["entry"]
        ) * pos["quantity"]

        self.balance += value

        self.realized_pnl += pnl

        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1

        # Recalculate Open P/L

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            current_price = get_price(sym)

            self.open_pnl += (
                (current_price - p["entry"])
                * p["quantity"]
            )

        trade = {

            "symbol": symbol,

            "reason": reason,

            "entry": pos["entry"],

            "exit": price,

            "quantity": pos["quantity"],

            "pnl": pnl,

        }

        self.closed_trades.append(trade)

        return trade

    # ==========================================
    # WIN RATE
    # ==========================================

    def win_rate(self):

        closed = self.wins + self.losses

        if closed == 0:
            return 0.0

        return round(
            self.wins / closed * 100,
            1,
        )

    # ==========================================
    # PROFIT FACTOR
    # ==========================================

    def profit_factor(self):

        profits = sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] > 0
        )

        losses = abs(sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] < 0
        ))

        if losses == 0:

            if profits > 0:
                return 999.0

            return 0.0

        return round(
            profits / losses,
            2,
        )

    # ==========================================
    # STATS
    # ==========================================

    def stats(self):

        return {

            "balance": round(
                self.balance,
                2,
            ),

            "equity": round(
                self.equity(),
                2,
            ),

            "realized": round(
                self.realized_pnl,
                2,
            ),

            "open_pnl": round(
                self.open_pnl,
                2,
            ),

            "positions": len(
                self.positions
            ),

            "trades": self.total_trades,

            "wins": self.wins,

            "losses": self.losses,

            "win_rate": self.win_rate(),

            "profit_factor": self.profit_factor(),

        }   
            

Намерих проблема.

Самият paper_trader.py изглежда нормално. Проблемът не е в него.

Причината е, че try_open_position() връща False от някой от първите проверки, но ти нямаш никакъв лог коя точно.

Замени началото на try_open_position() с това:

def try_open_position(self, symbol, signal):

    if self.has_position(symbol):
        print("[FAIL] already has position")
        return False

    if len(self.positions) >= self.max_open_positions:
        print("[FAIL] max positions")
        return False

    entry = signal["close"]
    atr = signal["atr"]

    print(f"[DEBUG] entry={entry} atr={atr}")

    stop = entry - atr * 2
    take = entry + atr * 5

    quantity = self.calculate_position_size(entry, stop)

    print(f"[DEBUG] quantity={quantity}")

    if quantity <= 0:
        print("[FAIL] quantity <= 0")
        return False

    value = quantity * entry

    print(f"[DEBUG] value={value} balance={self.balance}")

        if value > self.balance + 0.01:
            print("[FAIL] value > balance")
            
            return False

        self.balance -= value

        print(f"[OPEN OK] {symbol}")

        print(
            f"[OPEN OK] {symbol} "
            f"qty={quantity} "
            f"value={value:.2f}"
        )

        self.positions[symbol] = {

            "entry": entry,

            "quantity": quantity,

            "value": value,

            "stop": stop,

            "take": take,

            "highest": entry,

            "break_even": False,

            "partial_taken": False,

            "opened": datetime.utcnow(),

        }

        self.total_trades += 1

        print(

            f"[OPEN] {symbol} "

            f"Entry={entry:.4f} "

            f"SL={stop:.4f} "

            f"TP={take:.4f}"

        )

        return True

    # ==========================================
    # UPDATE POSITION
    # ==========================================

    def update_position(
        self,
        symbol,
        price,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        # Update highest price

        if price > pos["highest"]:
            pos["highest"] = price

        # --------------------------
        # Break Even
        # --------------------------

        if (
            not pos["break_even"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.30
        ):

            pos["stop"] = pos["entry"]

            pos["break_even"] = True

            print(
                f"[BE] {symbol}"
            )

        # --------------------------
        # Trailing Stop
        # --------------------------

        trail = pos["highest"] * 0.985

        if trail > pos["stop"]:

            pos["stop"] = trail

        # --------------------------
        # Partial TP
        # --------------------------

        if (
            not pos["partial_taken"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.60
        ):

            qty = pos["quantity"] / 2

            pnl = (
                (price - pos["entry"])
                * qty
            )

            self.balance += qty * price

            self.realized_pnl += pnl

            pos["quantity"] -= qty

            pos["partial_taken"] = True

            print(
                f"[PARTIAL] {symbol} "
                f"PnL={pnl:.2f}"
            )

        # --------------------------
        # Stop Loss
        # --------------------------

        if price <= pos["stop"]:

            return self.close_position(
                symbol,
                price,
                "STOP",
            )

        # --------------------------
        # Take Profit
        # --------------------------

        if price >= pos["take"]:

            return self.close_position(
                symbol,
                price,
                "TARGET",
            )

        # --------------------------
        # Open P/L
        # --------------------------

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            current_price = get_price(sym)

            self.open_pnl += (
                (current_price - p["entry"])
                * p["quantity"]
            )

        return None

    # ==========================================
    # CLOSE POSITION
    # ==========================================

    def close_position(
        self,
        symbol,
        price,
        reason,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)

        value = price * pos["quantity"]

        pnl = (
            price - pos["entry"]
        ) * pos["quantity"]

        self.balance += value

        self.realized_pnl += pnl

        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1

        # Recalculate Open P/L

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            current_price = get_price(sym)

            self.open_pnl += (
                (current_price - p["entry"])
                * p["quantity"]
            )

        trade = {

            "symbol": symbol,

            "reason": reason,

            "entry": pos["entry"],

            "exit": price,

            "quantity": pos["quantity"],

            "pnl": pnl,

        }

        self.closed_trades.append(trade)

        return trade

    # ==========================================
    # WIN RATE
    # ==========================================

    def win_rate(self):

        closed = self.wins + self.losses

        if closed == 0:
            return 0.0

        return round(
            self.wins / closed * 100,
            1,
        )

    # ==========================================
    # PROFIT FACTOR
    # ==========================================

    def profit_factor(self):

        profits = sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] > 0
        )

        losses = abs(sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] < 0
        ))

        if losses == 0:

            if profits > 0:
                return 999.0

            return 0.0

        return round(
            profits / losses,
            2,
        )

    # ==========================================
    # STATS
    # ==========================================

    def stats(self):

        return {

            "balance": round(
                self.balance,
                2,
            ),

            "equity": round(
                self.equity(),
                2,
            ),

            "realized": round(
                self.realized_pnl,
                2,
            ),

            "open_pnl": round(
                self.open_pnl,
                2,
            ),

            "positions": len(
                self.positions
            ),

            "trades": self.total_trades,

            "wins": self.wins,

            "losses": self.losses,

            "win_rate": self.win_rate(),

            "profit_factor": self.profit_factor(),

        }   


                # ==========================================
    # UPDATE POSITION
    # ==========================================

    def update_position(
        self,
        symbol,
        price,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        if price > pos["highest"]:
            pos["highest"] = price

        # Break Even

        if (
            not pos["break_even"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.30
        ):

            pos["stop"] = pos["entry"]
            pos["break_even"] = True

            print(f"[BE] {symbol}")

        # Trailing Stop

        trail = pos["highest"] * 0.985

        if trail > pos["stop"]:
            pos["stop"] = trail

        # Partial Take Profit

        if (
            not pos["partial_taken"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.60
        ):

            qty = pos["quantity"] / 2

            pnl = (
                (price - pos["entry"])
                * qty
            )

            self.balance += qty * price
            self.realized_pnl += pnl

            pos["quantity"] -= qty
            pos["partial_taken"] = True

            print(f"[PARTIAL] {symbol} PnL={pnl:.2f}")

        # Stop

        if price <= pos["stop"]:

            return self.close_position(
                symbol,
                price,
                "STOP",
            )

        # Target

        if price >= pos["take"]:

            return self.close_position(
                symbol,
                price,
                "TARGET",
            )

        # Open P/L

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            current_price = get_price(sym)

            self.open_pnl += (
                (current_price - p["entry"])
                * p["quantity"]
            )

        return None

    # ==========================================
    # CLOSE POSITION
    # ==========================================

    def close_position(
        self,
        symbol,
        price,
        reason,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)

        value = price * pos["quantity"]

        pnl = (
            price - pos["entry"]
        ) * pos["quantity"]

        self.balance += value
        self.realized_pnl += pnl

        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            current_price = get_price(sym)

            self.open_pnl += (
                (current_price - p["entry"])
                * p["quantity"]
            )

        trade = {
            "symbol": symbol,
            "reason": reason,
            "entry": pos["entry"],
            "exit": price,
            "quantity": pos["quantity"],
            "pnl": pnl,
        }

        self.closed_trades.append(trade)

        return trade

    # ==========================================
    # WIN RATE
    # ==========================================

    def win_rate(self):

        closed = self.wins + self.losses

        if closed == 0:
            return 0.0

        return round(
            self.wins / closed * 100,
            1,
        )

    # ==========================================
    # PROFIT FACTOR
    # ==========================================

    def profit_factor(self):

        profits = sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] > 0
        )

        losses = abs(sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] < 0
        ))

        if losses == 0:

            if profits > 0:
                return 999.0

            return 0.0

        return round(
            profits / losses,
            2,
        )

    # ==========================================
    # STATS
    # ==========================================

    def stats(self):

        return {

            "balance": round(self.balance, 2),

            "equity": round(
                self.equity(),
                2,
            ),

            "realized": round(
                self.realized_pnl,
                2,
            ),

            "open_pnl": round(
                self.open_pnl,
                2,
            ),

            "positions": len(self.positions),

            "trades": self.total_trades,

            "wins": self.wins,

            "losses": self.losses,

            "win_rate": self.win_rate(),

            "profit_factor": self.profit_factor(),

        }
