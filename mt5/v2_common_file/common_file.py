import MetaTrader5 as mt
import mplfinance as mpf
import pandas as pd


def filter_levels(df, number_of_lines_per_side, buy_price, sell_price):
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


def plot_graph(ohlc, support_levels, resistance_levels):
    levels = pd.concat([support_levels, resistance_levels])
    mpf.plot(ohlc, hlines=dict(hlines=levels.level.to_list(), colors=levels.color.to_list(), linestyle='-.'),
             type='candle')


def calculate_levels(ohlc, number_of_lines_per_side, buy_price, sell_price, plot_it):
    # using the fractol method to determine the support and resistance lines (find min/max value in a sliding window of +2 / -2 records away from selected row)
    support_levels = ohlc['low'].rolling(window=5, center=True, min_periods=1).min()
    resistance_levels = ohlc['high'].rolling(window=5, center=True, min_periods=1).max()

    # add color to support and resistance levels
    support_levels = pd.DataFrame({'time': support_levels.index, 'level': support_levels, 'color': 'g'})
    resistance_levels = pd.DataFrame({'time': resistance_levels.index, 'level': resistance_levels, 'color': 'r'})

    # filtering
    support_levels = filter_levels(support_levels, number_of_lines_per_side, buy_price, sell_price)
    resistance_levels = filter_levels(resistance_levels, number_of_lines_per_side, buy_price, sell_price)

    if plot_it:
        plot_graph(ohlc, support_levels, resistance_levels)

    return support_levels, resistance_levels


def close_order(ticker, qty, order_type, price):
    request = {
        "action": mt.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": qty,
        "type": order_type,
        "position": mt.positions_get()[0]._asdict()['ticket'],
        "price": price,
        "comment": "Close position",
        "type_time": mt.ORDER_TIME_GTC,
        "type_filling": mt.ORDER_FILLING_IOC,
    }
    # send a trading request
    mt.order_send(request)


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
