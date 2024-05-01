import MetaTrader5 as mt

from mt5.v2_common_file.common_file import pool_data_from_mt5, calculate_levels

# import matplotlib.pyplot as plt

mt.initialize()

# login = 48456843
# password = 'ov6WZ%Rc'
login = 48449505
password = 'w8FH9@FK'
server = 'HFMarketsGlobal-Demo'
path = 'C:/Program Files/MetaTrader 5/terminal64.exe'

mt.login(login, password, server)

# static variables
ticker = 'XAUUSD'
primary_qty = 0.05
secondary_qty = 0.03
buy_order_type = mt.ORDER_TYPE_BUY
sell_order_type = mt.ORDER_TYPE_SELL
time_frame = mt.TIMEFRAME_M10
window_count = 100
number_of_lines_per_side = 3

position_types_primary_buy = "Break Pri Buy"
position_types_primary_sell = "Break Pri Sell"
position_types_secondary_buy = "Break Sec Buy"
position_types_secondary_sell = "Break Sec Sell"


def create_order(ticker, qty, order_type, price, sl, tp):
    if order_type == mt.ORDER_TYPE_BUY:
        if primary_qty == qty:
            comment = position_types_primary_buy
        else:
            comment = position_types_secondary_buy
    elif order_type == mt.ORDER_TYPE_SELL:
        if primary_qty == qty:
            comment = position_types_primary_sell
        else:
            comment = position_types_secondary_sell

    request = {
        "action": mt.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": qty,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "comment": comment,
        "type_time": mt.ORDER_TIME_GTC,
        # "type_filling": mt.ORDER_FILLING_IOC,
    }
    # send a trading request
    mt.order_send(request)


def check_breakout(support_levels, resistance_levels):
    # trade execution conditions
    long_condition = buy_price > resistance_levels.level[0]
    short_condition = sell_price < support_levels.level[0]
    buy_sl = 2 * buy_price - resistance_levels.level[1]
    sell_sl = 2 * sell_price - support_levels.level[1]
    # tp[17] is the 17th index element in mt.positions_get() , which is the "comment"
    has_sell = any(tp[17] == position_types_primary_sell for tp in mt.positions_get())
    has_buy = any(tp[17] == position_types_primary_buy for tp in mt.positions_get())

    if long_condition and not has_buy:
        # If long condition hit , create buy order
        create_order(ticker, primary_qty, buy_order_type, buy_price, buy_sl, resistance_levels.level[1])
        create_order(ticker, secondary_qty, buy_order_type, buy_price, buy_sl, resistance_levels.level[2])
        # create_order(ticker, secondary_qty, buy_order_type, buy_price, buy_sl, resistance_levels.level[3])
        print("Buy orders placed")
    elif short_condition and not has_sell:
        create_order(ticker, primary_qty, sell_order_type, sell_price, sell_sl, support_levels.level[1])
        create_order(ticker, secondary_qty, sell_order_type, sell_price, sell_sl, support_levels.level[2])
        # create_order(ticker, secondary_qty, sell_order_type, sell_price, sell_sl, support_levels.level[3])
        print("Sell orders placed")


while True:
    try:
        buy_price = mt.symbol_info_tick(ticker).ask
        sell_price = mt.symbol_info_tick(ticker).bid
        ohlc, current_close = pool_data_from_mt5(ticker, time_frame, window_count)

        # run plot graph
        support_levels, resistance_levels = calculate_levels(ohlc, number_of_lines_per_side)

        # check for breakouts
        check_breakout(support_levels, resistance_levels)
    except Exception as e:
        print(f"An error occurred")
        continue
