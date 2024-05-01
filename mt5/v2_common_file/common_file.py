import MetaTrader5 as mt
import mplfinance as mpf
import pandas as pd


def filter_levels(df, number_of_lines_per_side, buy_price, sell_price):
    # used to prevent too many resistance / support lines too close to each other
    noise_value = 0.5

    # Update 'color' column where level is less than sell_price
    df.loc[df['level'] < sell_price, 'color'] = 'g'

    # Update 'color' column where level is greater than buy_price
    df.loc[df['level'] > buy_price, 'color'] = 'r'

    support_levels = df[df['color'] == 'g']
    resistance_levels = df[df['color'] == 'r']

    # Calculate the difference between consecutive values in the 'level' column for support levels
    support_levels_diff = abs(support_levels['level'].diff())

    # Calculate the difference between consecutive values in the 'level' column for resistance levels
    resistance_levels_diff = abs(resistance_levels['level'].diff())

    # Find rows where the difference is greater than or equal to 1 or is NaN
    support_mask = (support_levels_diff >= noise_value) | (support_levels_diff.isnull())
    resistance_mask = (resistance_levels_diff >= noise_value) | (resistance_levels_diff.isnull())

    # Filter the DataFrames based on the mask
    support_levels_filtered = support_levels[support_mask]
    resistance_levels_filtered = resistance_levels[resistance_mask]

    # Get only the top X number of entries and sort them
    top_x_support_levels = support_levels_filtered.head(number_of_lines_per_side).sort_values(by='level',
                                                                                              ascending=False)
    top_x_resistance_levels = resistance_levels_filtered.head(number_of_lines_per_side).sort_values(by='level',
                                                                                                    ascending=True)

    return top_x_support_levels, top_x_resistance_levels


def calculate_levels(ohlc, number_of_lines_per_side, buy_price, sell_price, plot_it):
    # using the fractol method to determine the support and resistance lines (find min/max value in a sliding window of +2 / -2 records away from selected row)
    support_levels = ohlc['low'].rolling(window=5, center=True, min_periods=1).min()
    resistance_levels = ohlc['high'].rolling(window=5, center=True, min_periods=1).max()

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
    levels = pd.concat([support_levels, resistance_levels])
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
