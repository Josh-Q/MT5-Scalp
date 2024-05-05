import MetaTrader5 as mt
import mplfinance as mpf
import numpy as np
import pandas as pd


def filter_levels(df, number_of_lines_per_side, buy_price, sell_price):  #
    # support_levels = df[df['color'] == 'g']
    # resistance_levels = df[df['color'] == 'r']
    support_levels = []
    resistance_levels = []

    df = df.reset_index(drop=True)
    for i in range(2, df.shape[0] - 2):
        level = df['level'][i]
        if sell_price > level:
            if far_from_level(level, support_levels):
                support_levels.append(level)
        elif buy_price < level:
            if far_from_level(level, resistance_levels):
                resistance_levels.append(level)

    # Get only the top X number of entries and sort them
    top_x_support_levels = sorted(support_levels, reverse=True)[:number_of_lines_per_side]
    top_x_resistance_levels = sorted(resistance_levels, reverse=False)[:number_of_lines_per_side]

    return top_x_support_levels, top_x_resistance_levels


def far_from_level(new_level, other_levels):
    # used to prevent too many resistance / support lines too close to each other
    noise_value = 1
    return np.sum([abs(new_level - x) < noise_value for x in other_levels]) == 0


def calculate_levels(ohlc, number_of_lines_per_side, buy_price, sell_price, plot_it):
    # using the fractol method to determine the support and resistance lines (find min/max value in a sliding window of +2 / -2 records away from selected row)
    support_levels = ohlc['low'].rolling(window=5, center=True, min_periods=5).min()
    resistance_levels = ohlc['high'].rolling(window=5, center=True, min_periods=5).max()

    # drop rows with NaN values
    support_levels.dropna(inplace=True)
    resistance_levels.dropna(inplace=True)

    combined_levels = pd.concat([
        pd.DataFrame({'time': support_levels.index, 'level': support_levels.values, 'color': 'g'}),
        pd.DataFrame({'time': resistance_levels.index, 'level': resistance_levels.values, 'color': 'r'})
    ]).sort_values(by='time', ascending=False)

    # filtering
    support_levels, resistance_levels = filter_levels(combined_levels, number_of_lines_per_side, buy_price, sell_price)

    if plot_it:
        plot_graph(ohlc, support_levels, resistance_levels)

    return support_levels, resistance_levels


def plot_graph(ohlc, support_levels, resistance_levels):
    support_df = pd.DataFrame({'level': support_levels, 'color': 'green'})
    resistance_df = pd.DataFrame({'level': resistance_levels, 'color': 'red'})

    # Concatenate support and resistance levels
    levels = pd.concat([support_df, resistance_df])
    mpf.plot(ohlc, hlines=dict(hlines=levels.level.to_list(), colors=levels.color.to_list(), linestyle='-.'),
             type='candle')


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


def pool_data_from_mt5(ticker, timeframe, window_count, fast_ma=None, slow_ma=None):
    # connect to MT5 for data
    ohlc = pd.DataFrame(mt.copy_rates_from_pos(ticker,  # symbol
                                               timeframe,  # timeframe
                                               0,  # start_pos
                                               window_count))  # count

    ohlc['time'] = pd.to_datetime(ohlc['time'], unit='s')
    ohlc.set_index('time', inplace=True)
    current_close = list(ohlc[-1:]['close'])[0]
    if fast_ma and slow_ma:
        ohlc['fast'] = ohlc['close'].ewm(span=slow_ma, adjust=False).mean()
        ohlc['slow'] = ohlc['close'].ewm(span=fast_ma, adjust=False).mean()

    return ohlc, current_close
