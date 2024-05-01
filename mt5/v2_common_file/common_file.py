import MetaTrader5 as mt
import mplfinance as mpf
import pandas as pd


def filter_levels(df, number_of_lines_per_side, buy_price, sell_price):
    # used to prevent too many resistance / support lines too close to each other
    noise_value = 0.5

    filtered_levels = []

    max_resistance = 0
    resistance_count = 0
    min_support = 0
    support_count = 0

    for index, row in df.iterrows():
        if resistance_count == number_of_lines_per_side and support_count == number_of_lines_per_side:
            break

        level = row.level

        if level > buy_price and resistance_count < number_of_lines_per_side:
            if max_resistance == 0 or level - max_resistance > noise_value:
                filtered_levels.append(row)
                max_resistance = level
                resistance_count += 1
        elif level < sell_price and support_count < number_of_lines_per_side:
            if min_support == 0 or min_support - level > noise_value:
                filtered_levels.append(row)
                min_support = level
                support_count += 1

    filtered_df = pd.DataFrame(filtered_levels, columns=['time', 'level', 'color'])

    # Split the filtered levels into support and resistance levels
    support_levels = filtered_df[filtered_df['color'] == 'g']
    resistance_levels = filtered_df[filtered_df['color'] == 'r']

    return support_levels, resistance_levels


def calculate_levels(ohlc, number_of_lines_per_side, buy_price, sell_price, plot_it):
    # using the fractol method to determine the support and resistance lines (find min/max value in a sliding window of +2 / -2 records away from selected row)
    support_levels = ohlc['low'].rolling(window=5, center=True, min_periods=5).min()
    resistance_levels = ohlc['high'].rolling(window=5, center=True, min_periods=5).max()

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
