import pandas as pd
import json
import os
import sys
import time

def process_trading_data():
    # 1. Load 111.csv (Trade Executions)
    trades_file = '111.csv'
    if not os.path.exists(trades_file):
        print(f"Error: {trades_file} not found")
        return

    try:
        df_trades = pd.read_csv(trades_file, header=None)
    except Exception as e:
        print(f"Error reading trades file: {e}")
        return

    df_trades.columns = [
        'TradeID', 'Qty', 'Price', 'Unknown3', 'Symbol', 'Side', 
        'Date', 'Time', 'ExecPrice', 'Exchange', 'Account', 'Account2', 'Symbol2'
    ]
    
    def clean_acc(acc):
        acc = str(acc).strip()
        if 'XOF' in acc:
            return acc[acc.find('XOF'):]
        return acc

    df_trades['Account'] = df_trades['Account'].apply(clean_acc)
    df_trades['Value'] = df_trades['Price'] * df_trades['Qty']

    # 2. Load PHILLIP_Open_Position_XOF9000_20260514.csv (Positions)
    positions_file = 'PHILLIP_Open_Position_XOF9000_20260514.csv'
    if not os.path.exists(positions_file):
        print(f"Warning: {positions_file} not found")
        df_positions = pd.DataFrame()
    else:
        try:
            df_positions = pd.read_csv(positions_file)
        except Exception as e:
            print(f"Error reading positions file: {e}")
            df_positions = pd.DataFrame()

    # Clean Client_No in positions
    if not df_positions.empty:
        df_positions['Client_No'] = df_positions['Client_No'].apply(clean_acc)
        df_positions['Unrealised_pl_value'] = pd.to_numeric(df_positions['Unrealised_pl_value'], errors='coerce').fillna(0)
        df_positions['Traded_Qty'] = pd.to_numeric(df_positions['Traded_Qty'], errors='coerce').fillna(0)
        df_positions['Traded_Price'] = pd.to_numeric(df_positions['Traded_Price'], errors='coerce').fillna(0)
        df_positions['Settlement_Price'] = pd.to_numeric(df_positions['Settlement_Price'], errors='coerce').fillna(0)

    # 3. Aggregate Data by Account
    all_accounts = set(df_trades['Account'].unique())
    if not df_positions.empty:
        all_accounts.update(df_positions['Client_No'].unique())
        
    # Group by account for fast O(1) group lookup instead of O(N) scanning
    trades_groups = {name: group for name, group in df_trades.groupby('Account')}
    
    try:
        df_clients = pd.read_excel('CLNT_MST.xlsx')
        client_map = dict(zip(df_clients['Account'].astype(str).str.strip(), df_clients['Name'].astype(str).str.strip()))
    except Exception as e:
        print(f"Error reading client master file: {e}")
        client_map = {}
    
    positions_groups = {}
    if not df_positions.empty:
        positions_groups = {name: group for name, group in df_positions.groupby('Client_No')}
        
    traders_list = []

    for acc in all_accounts:
        if str(acc) != 'XOF9000' and (not client_map or acc not in client_map):
            continue
            
        acc_name = client_map.get(acc, "")
        acc_trades = trades_groups.get(acc, pd.DataFrame())
        acc_positions = positions_groups.get(acc, pd.DataFrame())
        
        # Metrics from trades
        if not acc_trades.empty:
            buy_trades = acc_trades[acc_trades['Side'] == 'B']
            sell_trades = acc_trades[acc_trades['Side'] == 'S']
            
            total_buy_qty = int(buy_trades['Qty'].sum())
            total_sell_qty = int(sell_trades['Qty'].sum())
            
            # Buy Value & Sell Value
            buy_value = float(buy_trades['Value'].sum())
            sell_value = float(sell_trades['Value'].sum())
            
            avg_buy = float(buy_trades['Price'].mean()) if total_buy_qty > 0 else 0.0
            avg_sell = float(sell_trades['Price'].mean()) if total_sell_qty > 0 else 0.0
            
            num_trades = len(acc_trades)
            volatility = float(acc_trades['Price'].std()) if num_trades > 1 else 0.0
        else:
            total_buy_qty = 0
            total_sell_qty = 0
            buy_value = 0.0
            sell_value = 0.0
            avg_buy = 0.0
            avg_sell = 0.0
            num_trades = 0
            volatility = 0.0
        
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
            
        symbols = set()
        if not acc_trades.empty: symbols.update(acc_trades['Symbol'].unique())
        if not acc_positions.empty: symbols.update(acc_positions['Com_cd'].unique())
        
        # Trade History
        trades_history = []
        if not acc_trades.empty:
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
            'name': acc_name,
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

    # Write atomically to prevent partially-written file reads on the web app frontend
    temp_file = 'trader_data.json.tmp'
    try:
        with open(temp_file, 'w') as f:
            json.dump(traders_list, f, indent=2)
        os.replace(temp_file, 'trader_data.json')
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

def live_processor_loop():
    print("Starting Live Data Processor Loop...")
    trades_file = '111.csv'
    positions_file = 'PHILLIP_Open_Position_XOF9000_20260514.csv'
    
    last_mtime_trades = 0
    last_mtime_positions = 0
    
    # Process once on start
    process_trading_data()
    last_mtime_trades = os.path.getmtime(trades_file) if os.path.exists(trades_file) else 0
    last_mtime_positions = os.path.getmtime(positions_file) if os.path.exists(positions_file) else 0

    while True:
        try:
            mtime_trades = os.path.getmtime(trades_file) if os.path.exists(trades_file) else 0
            mtime_positions = os.path.getmtime(positions_file) if os.path.exists(positions_file) else 0
            
            if mtime_trades != last_mtime_trades or mtime_positions != last_mtime_positions:
                print(f"[{time.strftime('%H:%M:%S')}] Change detected in data source files. Reprocessing...")
                process_trading_data()
                last_mtime_trades = mtime_trades
                last_mtime_positions = mtime_positions
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error in live processor loop: {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        live_processor_loop()
    else:
        process_trading_data()
