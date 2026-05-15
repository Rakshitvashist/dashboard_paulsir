import pandas as pd
import json
import os

def process_trading_data():
    # 1. Load 111.csv (Trade Executions)
    trades_file = '111.csv'
    if not os.path.exists(trades_file):
        print(f"Error: {trades_file} not found")
        return

    df_trades = pd.read_csv(trades_file, header=None)
    df_trades.columns = [
        'TradeID', 'Qty', 'Price', 'Unknown3', 'Symbol', 'Side', 
        'Date', 'Time', 'ExecPrice', 'Exchange', 'Account', 'Account2', 'Symbol2'
    ]
    df_trades['Account'] = df_trades['Account'].astype(str).str.strip()
    df_trades['Value'] = df_trades['Price'] * df_trades['Qty']

    # 2. Load PHILLIP_Open_Position_XOF9000_20260514.csv (Positions)
    positions_file = 'PHILLIP_Open_Position_XOF9000_20260514.csv'
    if not os.path.exists(positions_file):
        print(f"Error: {positions_file} not found")
        df_positions = pd.DataFrame()
    else:
        df_positions = pd.read_csv(positions_file)

    # Clean Client_No in positions
    if not df_positions.empty:
        df_positions['Client_No'] = df_positions['Client_No'].astype(str).str.strip()
        df_positions['Unrealised_pl_value'] = pd.to_numeric(df_positions['Unrealised_pl_value'], errors='coerce').fillna(0)
        df_positions['Traded_Qty'] = pd.to_numeric(df_positions['Traded_Qty'], errors='coerce').fillna(0)
        df_positions['Traded_Price'] = pd.to_numeric(df_positions['Traded_Price'], errors='coerce').fillna(0)
        df_positions['Settlement_Price'] = pd.to_numeric(df_positions['Settlement_Price'], errors='coerce').fillna(0)

    # 3. Aggregate Data by Account
    all_accounts = set(df_trades['Account'].unique())
    if not df_positions.empty:
        all_accounts.update(df_positions['Client_No'].unique())
        
    traders_list = []

    for acc in all_accounts:
        acc_trades = df_trades[df_trades['Account'] == acc]
        acc_positions = df_positions[df_positions['Client_No'] == acc] if not df_positions.empty else pd.DataFrame()
        
        # Metrics from trades
        buy_trades = acc_trades[acc_trades['Side'] == 'B']
        sell_trades = acc_trades[acc_trades['Side'] == 'S']
        
        total_buy_qty = int(buy_trades['Qty'].sum())
        total_sell_qty = int(sell_trades['Qty'].sum())
        
        # Buy Value & Sell Value
        buy_value = float(buy_trades['Value'].sum())
        sell_value = float(sell_trades['Value'].sum())
        
        avg_buy = float(buy_trades['Price'].mean()) if total_buy_qty > 0 else 0.0
        avg_sell = float(sell_trades['Price'].mean()) if total_sell_qty > 0 else 0.0
        
        # Gross P&L (Sum of MTM)
        gross_pl = float(acc_positions['Unrealised_pl_value'].sum()) if not acc_positions.empty else 0.0
        
        # Net position
        if not acc_trades.empty:
            net_position = total_buy_qty - total_sell_qty
        elif not acc_positions.empty:
            pos_buys = acc_positions[acc_positions['Buy_Sell'] == 'B']['Traded_Qty'].sum()
            pos_sells = acc_positions[acc_positions['Buy_Sell'] == 'S']['Traded_Qty'].sum()
            net_position = int(pos_buys - pos_sells)
        else:
            net_position = 0
            
        num_trades = len(acc_trades)
        volatility = float(acc_trades['Price'].std()) if num_trades > 1 else 0.0
        
        symbols = set()
        if not acc_trades.empty: symbols.update(acc_trades['Symbol'].unique())
        if not acc_positions.empty: symbols.update(acc_positions['Com_cd'].unique())
        
        # Trade History
        trades_history = []
        for _, row in acc_trades.iterrows():
            trades_history.append({
                'Time': str(row['Time']),
                'Symbol': str(row['Symbol']),
                'Side': str(row['Side']),
                'Qty': int(row['Qty']),
                'Price': float(row['Price']),
                'Value': float(row['Value']),
                'Exchange': str(row['Exchange'])
            })
        
        # Current Positions Detail
        current_positions = []
        if not acc_positions.empty:
            for _, row in acc_positions.iterrows():
                current_positions.append({
                    'Symbol': str(row['Com_cd']),
                    'Month': str(row['Contract_Month']),
                    'Side': str(row['Buy_Sell']),
                    'Qty': int(row['Traded_Qty']),
                    'AvgPrice': float(row['Traded_Price']),
                    'ClosingPrice': float(row['Settlement_Price']),
                    'MTM': float(row['Unrealised_pl_value'])
                })
            
        traders_list.append({
            'account': str(acc),
            'is_master': True if str(acc) == 'XOF9000' else False,
            'total_buy_qty': total_buy_qty,
            'buy_value': buy_value,
            'avg_buy': avg_buy,
            'total_sell_qty': total_sell_qty,
            'sell_value': sell_value,
            'avg_sell': avg_sell,
            'net_position': net_position,
            'gross_pl': gross_pl,
            'num_trades': num_trades,
            'volatility': volatility,
            'symbols': sorted(list(symbols)),
            'trades': trades_history,
            'positions': current_positions
        })

    traders_list.sort(key=lambda x: (x['is_master'], x['total_buy_qty'] + x['total_sell_qty']), reverse=True)

    with open('trader_data.json', 'w') as f:
        json.dump(traders_list, f, indent=2)
        
    print(f"Successfully processed {len(traders_list)} accounts and saved to trader_data.json")

if __name__ == "__main__":
    process_trading_data()
