import time

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
buy_now_order_type = mt.ORDER_TYPE_BUY
sell_now_order_type = mt.ORDER_TYPE_SELL
buy_limit_order_type = mt.ORDER_TYPE_BUY_LIMIT
sell_limit_order_type = mt.ORDER_TYPE_SELL_LIMIT
time_frame = mt.TIMEFRAME_M1
window_count = 20
number_of_lines_per_side = 1
noise_factor = 0.1
plot_it = False
trade_it = True

position_types_buy = "Scalping Buy"
position_types_sell = "Scalping Sell"


def create_order(ticker, qty, order_type, price, sl, tp):
    if order_type == mt.ORDER_TYPE_BUY or order_type == mt.ORDER_TYPE_BUY_LIMIT:
        comment = position_types_buy
    elif order_type == mt.ORDER_TYPE_SELL or order_type == mt.ORDER_TYPE_SELL_LIMIT:
        comment = position_types_sell

    time_offset = 3 * 60 * 60
    request_life_time = 1 * 120
    expiry_time = int(time.time() + time_offset + request_life_time)
    request = {
        "action": mt.TRADE_ACTION_PENDING,
        "symbol": ticker,
        "volume": qty,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "comment": comment,
        "type_time": mt.ORDER_TIME_SPECIFIED,
        "expiration": expiry_time,
    }
    mt.order_send(request)


def check_scalp(support_levels, resistance_levels):
    if support_levels.empty or resistance_levels.empty:
        return

    # difference between resistance and support level
    level_difference = resistance_levels.level.iloc[0] - support_levels.level.iloc[0]

    # no trade if the opportunity is too small
    if level_difference < 1:
        return

    # noise_factor multipler
    noise = level_difference * noise_factor
    # trade execution price
    adjusted_support_level = support_levels.level.iloc[0] + noise
    adjusted_resistance_level = resistance_levels.level.iloc[0] - noise

    # risk and reward amount (scalp opportunity)
    risk_reward_amount = (adjusted_resistance_level - adjusted_support_level)

    # risk and reward ratio 1 : 1
    buy_sl = round(adjusted_support_level - risk_reward_amount, 2)
    sell_sl = round(adjusted_resistance_level + risk_reward_amount, 2)

    # tp[17] is the 17th index element in mt.positions_get() , which is the "comment"
    has_sell = any(tp[17] == position_types_sell for tp in mt.positions_get())
    has_buy = any(tp[17] == position_types_buy for tp in mt.positions_get())

    # adjusted_support_level = 2400.00
    # buy_sl = 2200.00
    # adjusted_resistance_level = 2400
    # sell_sl = 2400.00
    has_buy_pending, has_sell_pending = house_keep_open_order()

    if not has_buy and not has_buy_pending:
        # If long condition hit , create buy order
        create_order(ticker, primary_qty, buy_limit_order_type, adjusted_support_level, buy_sl,
                     adjusted_resistance_level)
        print("Buy orders placed")
        print("BUY IN " + str(adjusted_support_level))
        print("TP " + str(adjusted_resistance_level))
        print("SL " + str(buy_sl))

    if not has_sell and not has_sell_pending:
        create_order(ticker, primary_qty, sell_limit_order_type, adjusted_resistance_level, sell_sl,
                     adjusted_support_level)
        print("Sell orders placed")
        print("Sell Out " + str(adjusted_resistance_level))
        print("TP " + str(adjusted_support_level))
        print("SL " + str(sell_sl))


def house_keep_open_order():
    orders = mt.orders_get()

    has_buy_pending = any(order.comment == position_types_buy for order in orders)
    has_sell_pending = any(order.comment == position_types_sell for order in orders)
    return has_buy_pending, has_sell_pending


while True:
    try:
        buy_price = mt.symbol_info_tick(ticker).ask
        sell_price = mt.symbol_info_tick(ticker).bid

        ohlc, current_close = pool_data_from_mt5(ticker, time_frame, window_count)

        # run plot graph
        support_levels, resistance_levels = calculate_levels(ohlc, number_of_lines_per_side, buy_price, sell_price,
                                                             plot_it)

        # check for breakouts
        if trade_it:
            check_scalp(support_levels, resistance_levels)
    except Exception as e:
        print(f"An error occurred")
        continue
