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
buy_order_type = mt.ORDER_TYPE_BUY
sell_order_type = mt.ORDER_TYPE_SELL
time_frame = mt.TIMEFRAME_M10
window_count = 100
number_of_lines_per_side = 3

position_types_primary_buy = "Break Pri Buy"
position_types_primary_sell = "Break Pri Sell"
position_types_secondary_buy = "Break Sec Buy"
position_types_secondary_sell = "Break Sec Sell"


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

    # plot_graph(ohlc, support_levels, resistance_levels)

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
