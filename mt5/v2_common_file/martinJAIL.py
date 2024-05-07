import time
from datetime import datetime, timedelta

import MetaTrader5 as mt

from mt5.v2_common_file.common_file import pool_data_from_mt5, calculate_levels

# import matplotlib.pyplot as plt

mt.initialize()

login = 48456843
password = 'ov6WZ%Rc'
# login = 48449505
# password = 'w8FH9@FK'
server = 'HFMarketsGlobal-Demo'
path = 'C:/Program Files/MetaTrader 5/terminal64.exe'

mt.login(login, password, server)


# latest_deal_info
class Latest_Deal_Info:
    def __init__(self, ticket_number, primary_qty):
        self.ticket_number = ticket_number
        self.primary_qty = primary_qty

    def update(self, ticket_number, primary_qty):
        self.ticket_number = ticket_number
        self.primary_qty = primary_qty


# static variables
ticker = 'XAUUSD'
primary_qty = 0.0
buy_now_order_type = mt.ORDER_TYPE_BUY
sell_now_order_type = mt.ORDER_TYPE_SELL
buy_limit_order_type = mt.ORDER_TYPE_BUY_LIMIT
sell_limit_order_type = mt.ORDER_TYPE_SELL_LIMIT
time_frame = mt.TIMEFRAME_M1
window_count = 100
number_of_lines_per_side = 5
noise_factor = 0.1
# max_risk = 3
plot_it = False
trade_it = True

position_types_buy = "Scalping Buy"
position_types_sell = "Scalping Sell"

latest_deal_info = Latest_Deal_Info(None, primary_qty)
fast_ma = 5
slow_ma = 21


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


def check_decision_point(support_levels, resistance_levels, ohlc):
    # if EMA cross , fast > slow -> sell , slow > fast -> buy
    # decision point at resistance / support
    # if a position exist , do not make another trade
    # if is_previous_trade_win is a loss, double trade quantity
    # if a buy and a sell order exist , do not make another trade
    if len(support_levels) <= 1 or len(resistance_levels) <= 1:
        return

    # trade execution price
    latest_support_level = support_levels[0]
    latest_resistance_level = resistance_levels[0]

    # difference between resistance and support level
    # level_difference = latest_resistance_level - latest_support_level

    # no trade if the opportunity is too small
    # if level_difference < 1:
    #     return

    # risk and reward ratio 1 : 1
    buy_sl = round(latest_support_level - 1, 2)
    buy_tp = round(latest_support_level + 1, 2)
    sell_sl = round(latest_resistance_level + 1, 2)
    sell_tp = round(latest_resistance_level - 1, 2)

    # tp[17] is the 17th index element in mt.positions_get() , which is the "comment"
    has_sell = any(tp[17] == position_types_sell for tp in mt.positions_get())
    has_buy = any(tp[17] == position_types_buy for tp in mt.positions_get())

    has_buy_pending, has_sell_pending = house_keep_open_order()

    check_previous_trade_win()

    if has_buy or has_sell:
        return

    if not has_buy_pending and ohlc[-1:]['fast'].iloc[0] < ohlc[-1:]['slow'].iloc[0]:
        # If long condition hit , create buy order
        create_order(ticker, latest_deal_info.primary_qty, buy_limit_order_type, latest_support_level, buy_sl,
                     buy_tp)
        print("Buy orders placed")
        print("BUY IN " + str(latest_support_level))
        print("TP " + str(buy_tp))
        print("SL " + str(buy_sl))

    if not has_sell_pending and ohlc[-1:]['fast'].iloc[0] >= ohlc[-1:]['slow'].iloc[0]:
        create_order(ticker, latest_deal_info.primary_qty, sell_limit_order_type, latest_resistance_level, sell_sl,
                     sell_tp)
        print("Sell orders placed")
        print("Sell Out " + str(latest_resistance_level))
        print("TP " + str(sell_tp))
        print("SL " + str(sell_sl))


def check_previous_trade_win():
    today = datetime.now()
    deals = mt.history_deals_get(today - timedelta(days=1), today + timedelta(days=1))

    # Print the last deal history
    if deals is not None and len(deals) > 0:
        last_deal = None
    for deal in reversed(deals):
        if deal.reason == 4 or deal.reason == 5:
            last_deal = deal
            break

    if last_deal is not None:
        if last_deal.profit > 0:
            primary_qty = 0.05
        else:
            primary_qty = (last_deal.volume * 2.00) + 0.01

        latest_deal_info.update(last_deal.order, primary_qty)


def house_keep_open_order():
    orders = mt.orders_get()

    has_buy_pending = any(order.comment == position_types_buy for order in orders)
    has_sell_pending = any(order.comment == position_types_sell for order in orders)
    return has_buy_pending, has_sell_pending


while True:
    try:
        buy_price = mt.symbol_info_tick(ticker).ask
        sell_price = mt.symbol_info_tick(ticker).bid

        ohlc, current_close = pool_data_from_mt5(ticker, time_frame, window_count, fast_ma, slow_ma)

        # run plot graph
        support_levels, resistance_levels = calculate_levels(ohlc, number_of_lines_per_side, buy_price, sell_price,
                                                             plot_it)

        # check for breakouts
        if trade_it:
            check_decision_point(support_levels, resistance_levels, ohlc)
    except Exception as e:
        print(f"An error occurred")
        continue
