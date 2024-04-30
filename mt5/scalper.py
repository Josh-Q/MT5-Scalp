import time

import MetaTrader5 as mt
import mplfinance as mpf
# import matplotlib.pyplot as plt
import pandas as pd

mt.initialize()

login = 48456843
password = 'ov6WZ%Rc'
# login = 48449505
# password = 'w8FH9@FK'
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
plot_graph = False
# risk threshold for TP / SL
risk_threshold = 0.8

position_types_buy = "Scalping Buy"
position_types_sell = "Scalping Sell"


def filter_levels(df, number_of_lines_per_side):
    filtered_levels = []
    df.sort_index(ascending=False, inplace=True)
    # used to prevent too many resistance / support lines too close to each other
    noise_value = 1

    for index, row in df.iterrows():
        if len(filtered_levels) > number_of_lines_per_side - 1:
            break
        # support levels
        if row.color == 'g':
            # if have filtered_levels, run logic to check if we should add this row to the filtered_levels
            if filtered_levels:
                # if current row level is not too close to the previous support level and is less than current sell price , add it
                if row.level < filtered_levels[-1][1] - noise_value and row.level < sell_price:
                    filtered_levels.append((row.time, row.level, row.color))
            else:
                # if do not have any filtered_levels, add the new resistance level to the list
                filtered_levels.append((row.time, row.level, row.color))
        # resistance level
        elif row.color == 'r':
            # if have filtered_levels, run logic to check if we should add this row to the filtered_levels
            if filtered_levels:
                # if current row level is not too close to the previous resistance level and is greater than current buy price , add it
                if row.level > filtered_levels[-1][1] + noise_value and row.level > buy_price:
                    filtered_levels.append((row.time, row.level, row.color))
            else:
                # if do not have any filtered_levels, add the new resistance level to the list
                filtered_levels.append((row.time, row.level, row.color))

    filtered_df = pd.DataFrame(filtered_levels, columns=['time', 'level', 'color'])

    return filtered_df


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


def plot_graph(ohlc, support_levels, resistance_levels):
    levels = pd.concat([support_levels, resistance_levels])
    mpf.plot(ohlc, hlines=dict(hlines=levels.level.to_list(), colors=levels.color.to_list(), linestyle='-.'),
             type='candle')


def calculate_levels(ohlc, number_of_lines_per_side):
    # using the fractol method to determine the support and resistance lines (find min/max value in a sliding window of +2 / -2 records away from selected row)
    support_levels = ohlc['low'].rolling(window=5, center=True, min_periods=1).min()
    resistance_levels = ohlc['high'].rolling(window=5, center=True, min_periods=1).max()

    # add color to support and resistance levels
    support_levels = pd.DataFrame({'time': support_levels.index, 'level': support_levels, 'color': 'g'})
    resistance_levels = pd.DataFrame({'time': resistance_levels.index, 'level': resistance_levels, 'color': 'r'})

    # filtering
    support_levels = filter_levels(support_levels, number_of_lines_per_side)
    resistance_levels = filter_levels(resistance_levels, number_of_lines_per_side)

    if plot_graph:
        plot_graph(ohlc, support_levels, resistance_levels)

    return support_levels, resistance_levels


def pool_data_from_mt5(ticker, timeframe, window_count):
    # connect to MT5 for data
    ohlc = pd.DataFrame(mt.copy_rates_from_pos(ticker,  # symbol
                                               timeframe,  # timeframe
                                               0,  # start_pos
                                               window_count))  # count

    ohlc['time'] = pd.to_datetime(ohlc['time'], unit='s')
    ohlc.set_index('time', inplace=True)
    current_close = list(ohlc[-1:]['close'])[0]
    return ohlc, current_close


def check_scalp(support_levels, resistance_levels):
    noise = 0

    # trade execution price
    adjusted_support_level = support_levels.level[0] + noise
    adjusted_resistance_level = resistance_levels.level[0] - noise

    # risk and reward amount (scalp opportunity)
    risk_reward_amount = (adjusted_resistance_level - adjusted_support_level) * risk_threshold

    # no trade if the opportunity is too small
    if risk_reward_amount < 1:
        return

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
    # for order in orders:
    #     time_difference = int(current_time + time_offset) - order.time_setup
    #     time_difference_minutes = time_difference / 60
    #     if time_difference_minutes > 1:
    #         mt.order_close(order['ticket'], 0)  # Close the order


while True:
    try:
        buy_price = mt.symbol_info_tick(ticker).ask
        sell_price = mt.symbol_info_tick(ticker).bid

        ohlc, current_close = pool_data_from_mt5(ticker, time_frame, window_count)

        # run plot graph
        support_levels, resistance_levels = calculate_levels(ohlc, number_of_lines_per_side)

        # check for breakouts
        check_scalp(support_levels, resistance_levels)
    except Exception as e:
        print(f"An error occurred")
        continue
