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
        idx_xof = acc.find('XOF')
        idx_xob = acc.find('XOB')
        idx = idx_xof if idx_xof != -1 else idx_xob
        if idx != -1:
            if idx >= 2 and acc[idx-2:idx] == 'S-':
                return acc[idx-2:]
            return acc[idx:]
        return acc

    df_trades['Account'] = df_trades['Account'].apply(clean_acc)
    df_trades['Value'] = df_trades['Price'] * df_trades['Qty']

    MONTH_MAP = {
        'F': 'Jan', 'G': 'Feb', 'H': 'Mar', 'J': 'Apr', 'K': 'May', 'M': 'Jun',
        'N': 'Jul', 'Q': 'Aug', 'U': 'Sep', 'V': 'Oct', 'X': 'Nov', 'Z': 'Dec'
    }

    def parse_trade_symbol(symbol):
        symbol = str(symbol).strip()
        if '-' in symbol:
            return None, None
        if len(symbol) >= 4:
            month_char = symbol[-3]
            year_code = symbol[-2:]
            base_symbol = symbol[:-3]
            if month_char in MONTH_MAP and year_code.isdigit():
                month_name = f"{MONTH_MAP[month_char]} {year_code}"
                return base_symbol, month_name
        return symbol, None

    parsed_symbols = df_trades['Symbol'].apply(parse_trade_symbol)
    df_trades['BaseSymbol'] = [p[0] for p in parsed_symbols]
    df_trades['ContractMonth'] = [p[1] for p in parsed_symbols]

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
        client_map = {}
        for _, row in df_clients.iterrows():
            client_acc = str(row['Account']).strip()
            client_map[client_acc] = {
                'name': str(row['Name']).strip(),
                'backcode': str(row['BackCode']).strip()
            }
    except Exception as e:
        print(f"Error reading client master file: {e}")
        client_map = {}
    
    positions_groups = {}
    if not df_positions.empty:
        positions_groups = {name: group for name, group in df_positions.groupby('Client_No')}
        
    traders_list = []

    for acc in all_accounts:
        if not client_map or acc not in client_map:
            continue
            
        acc_info = client_map[acc]
        acc_name = acc_info['name']
        acc_backcode = acc_info['backcode']
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
                sym = str(row['Symbol'])
                if '-' in sym:
                    continue
                trades_history.append({
                    'Time': str(row['Time']),
                    'Symbol': sym,
                    'Side': str(row['Side']),
                    'Qty': int(row['Qty']),
                    'Price': float(row['Price']),
                    'Value': float(row['Value']),
                    'Exchange': str(row['Exchange'])
                })
        
        # Current Positions Detail in sampe.xlsx format
        current_positions = []
        if not acc_positions.empty:
            groups = acc_positions.groupby(['Com_cd', 'Contract_Month'])
            for (com_cd, contract_month), gp in groups:
                com_cd_clean = str(com_cd).strip()
                month_clean = str(contract_month).strip()
                
                # Fetch first row for common properties
                first_row = gp.iloc[0]
                exch = str(first_row.get('Exch_Cd', '')).strip()
                scrip = f"{com_cd_clean}-{exch}"
                
                strike = first_row.get('Strike_Price', 0)
                if pd.isna(strike):
                    strike = 0
                else:
                    strike = float(strike)
                    
                callput = first_row.get('Call_Put', '')
                if pd.isna(callput) or str(callput).strip() == '':
                    callput = 'NaN'
                else:
                    callput = str(callput).strip()
                
                # Today's trades matching this symbol and month
                matching_trades = acc_trades[
                    (acc_trades['BaseSymbol'] == com_cd_clean) & 
                    (acc_trades['ContractMonth'] == month_clean)
                ] if 'BaseSymbol' in acc_trades.columns else pd.DataFrame()
                
                buy_qty = int(matching_trades[matching_trades['Side'] == 'B']['Qty'].sum()) if not matching_trades.empty else 0
                sell_qty = int(matching_trades[matching_trades['Side'] == 'S']['Qty'].sum()) if not matching_trades.empty else 0
                
                # Net position from PHILLIP positions
                net_qty = int(gp.apply(lambda r: r['Traded_Qty'] if r['Buy_Sell'] == 'B' else -r['Traded_Qty'], axis=1).sum())
                bf_qty = net_qty - buy_qty + sell_qty
                
                # Weighted Entry Rate
                buy_gp = gp[gp['Buy_Sell'] == 'B']
                sell_gp = gp[gp['Buy_Sell'] == 'S']
                
                buy_val = float((buy_gp['Traded_Qty'] * buy_gp['Traded_Price']).sum())
                sell_val = float((sell_gp['Traded_Qty'] * sell_gp['Traded_Price']).sum())
                
                total_buy_qty = float(buy_gp['Traded_Qty'].sum())
                total_sell_qty = float(sell_gp['Traded_Qty'].sum())
                
                if net_qty > 0 and total_buy_qty > 0:
                    average_rate = buy_val / total_buy_qty
                elif net_qty < 0 and total_sell_qty > 0:
                    average_rate = sell_val / total_sell_qty
                else:
                    total_trades_qty = total_buy_qty + total_sell_qty
                    average_rate = (buy_val + sell_val) / total_trades_qty if total_trades_qty > 0 else 0.0
                
                # Weighted average Closing Price (LTP)
                total_qty_abs = gp['Traded_Qty'].sum()
                weighted_closing_sum = (gp['Traded_Qty'] * gp['Settlement_Price']).sum()
                ltp = float(weighted_closing_sum / total_qty_abs) if total_qty_abs > 0 else 0.0
                
                # MTM
                mtm = float(gp['Unrealised_pl_value'].sum())
                
                # Intraday MTM
                intraday_mtm = 0.0
                
                # Exchange Delta
                com_type = str(first_row.get('Com_Type', '')).strip()
                exchange_delta = 1 if com_type == 'F' else 0
                
                current_positions.append({
                    'scrip': scrip,
                    'exchange': exch,
                    'scrip_name': com_cd_clean,
                    'expiry_date': month_clean,
                    'callput': callput,
                    'strike': strike,
                    'bf_qty': bf_qty,
                    'buy_qty': buy_qty,
                    'sell_qty': sell_qty,
                    'net_qty': net_qty,
                    'average_rate': average_rate,
                    'ltp': ltp,
                    'mtm': mtm,
                    'intraday_mtm': intraday_mtm,
                    'exchange_delta': exchange_delta,
                    'day_bought_qty': buy_qty,
                    'day_sold_qty': sell_qty
                })
            
        traders_list.append({
            'account': str(acc),
            'name': acc_name,
            'backcode': acc_backcode,
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
