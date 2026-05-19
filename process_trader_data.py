import pandas as pd
import json
import os
import sys
import time
import glob

def resolve_data_sources():
    # 1. Find trades file (Scan both 111.csv and all .All_*.csv files, and pick the absolute latest by mtime)
    all_trade_files = []
    if os.path.exists('111.csv'):
        all_trade_files.append('111.csv')
    all_trade_files.extend(glob.glob('.All_*.csv'))
    
    trades_file = None
    if all_trade_files:
        all_trade_files.sort(key=os.path.getmtime, reverse=True)
        trades_file = all_trade_files[0]
            
    # 2. Find latest positions files
    pos_files = glob.glob('PHILLIP_Open_Position_*.csv')
    dates = []
    for fn in pos_files:
        base = os.path.basename(fn)
        parts = base.split('_')
        if len(parts) >= 5:
            dt = parts[4].split('.')[0]
            dates.append(dt)
            
    latest_date = max(dates) if dates else None
    positions_files = []
    if latest_date:
        positions_files = [fn for fn in pos_files if latest_date in fn]
        
    return trades_file, positions_files

def process_trading_data():
    trades_file, positions_files = resolve_data_sources()
    print(f"Processing Trades from: {trades_file}")
    print(f"Processing Positions from: {positions_files}")
    
    # Load live prices if available for real-time live MTM and price updates
    live_prices = {}
    if os.path.exists('live_prices.json'):
        try:
            with open('live_prices.json', 'r') as f:
                live_prices = json.load(f)
        except Exception as e:
            print(f"Error reading live_prices.json: {e}")

    if not trades_file or not os.path.exists(trades_file):
        print("Error: No trades file found")
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
    df_trades = df_trades[~df_trades['Symbol'].str.contains('-', na=False)]

    MONTH_MAP = {
        'F': 'Jan', 'G': 'Feb', 'H': 'Mar', 'J': 'Apr', 'K': 'May', 'M': 'Jun',
        'N': 'Jul', 'Q': 'Aug', 'U': 'Sep', 'V': 'Oct', 'X': 'Nov', 'Z': 'Dec'
    }

    def parse_date_to_contract_month(date_str):
        date_str = str(date_str).strip()
        parts = date_str.split('-')
        if len(parts) == 3:
            day, month, year = parts
            if len(year) == 4:
                return f"{month} {year[-2:]}"
        return None

    def parse_trade_symbol(symbol, date_str):
        symbol = str(symbol).strip()
        
        # 1. First check if it ends with a valid standard month char and 2-digit year (like IUK26, BRLM26)
        if len(symbol) >= 4:
            month_char = symbol[-3]
            year_code = symbol[-2:]
            if month_char in MONTH_MAP and year_code.isdigit():
                base_symbol = symbol[:-3]
                contract_month = f"{MONTH_MAP[month_char]} {year_code}"
                return base_symbol, contract_month
                
        # 2. Fall back to parsing the contract month from the Date column (for plain symbols like DINR)
        base_symbol = symbol
        contract_month = parse_date_to_contract_month(date_str)
        return base_symbol, contract_month

    parsed_symbols = df_trades.apply(lambda r: parse_trade_symbol(r['Symbol'], r['Date']), axis=1)
    df_trades['BaseSymbol'] = [p[0] for p in parsed_symbols]
    df_trades['ContractMonth'] = [p[1] for p in parsed_symbols]

    # Load and combine all matching positions files
    dfs = []
    for fn in positions_files:
        try:
            df = pd.read_csv(fn)
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"Error loading positions file {fn}: {e}")
            
    if dfs:
        df_positions = pd.concat(dfs, ignore_index=True)
    else:
        df_positions = pd.DataFrame()

    # Clean Client_No in positions
    if not df_positions.empty:
        df_positions['Client_No'] = df_positions['Client_No'].apply(clean_acc)
        df_positions['Com_cd'] = df_positions['Com_cd'].astype(str).str.strip()
        df_positions['Contract_Month'] = df_positions['Contract_Month'].astype(str).str.strip()
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
                    'Exchange': str(row['Exchange']),
                    'Expiry': str(row['ContractMonth']) if 'ContractMonth' in row else None
                })
        
        # Current Positions Detail in sampe.xlsx format
        current_positions = []
        
        # Get all unique (BaseSymbol, ContractMonth) from trades and positions
        all_keys = set()
        if not acc_positions.empty:
            for _, row in acc_positions.iterrows():
                com_cd = str(row.get('Com_cd', '')).strip()
                month = str(row.get('Contract_Month', '')).strip()
                if com_cd and month and com_cd != 'nan' and month != 'nan':
                    all_keys.add((com_cd, month))
                    
        if not acc_trades.empty:
            for _, row in acc_trades.iterrows():
                base_sym = row.get('BaseSymbol')
                month = row.get('ContractMonth')
                if base_sym and month:
                    base_sym_str = str(base_sym).strip()
                    month_str = str(month).strip()
                    if base_sym_str and month_str and base_sym_str != 'nan' and month_str != 'nan':
                        all_keys.add((base_sym_str, month_str))
                    
        for com_cd_clean, month_clean in sorted(list(all_keys)):
            # Get matching positions rows
            gp = acc_positions[
                (acc_positions['Com_cd'] == com_cd_clean) & 
                (acc_positions['Contract_Month'] == month_clean)
            ] if not acc_positions.empty else pd.DataFrame()
            
            # Today's trades matching this symbol and month
            matching_trades = acc_trades[
                (acc_trades['BaseSymbol'] == com_cd_clean) & 
                (acc_trades['ContractMonth'] == month_clean)
            ] if 'BaseSymbol' in acc_trades.columns and not acc_trades.empty else pd.DataFrame()
            
            buy_qty = int(matching_trades[matching_trades['Side'] == 'B']['Qty'].sum()) if not matching_trades.empty else 0
            sell_qty = int(matching_trades[matching_trades['Side'] == 'S']['Qty'].sum()) if not matching_trades.empty else 0
            
            # Match symbol name in live prices: com_cd_clean + month letter + year code (e.g. "IUK26") or com_cd_clean ("IU")
            INV_MONTH_MAP = {v: k for k, v in MONTH_MAP.items()}
            parts = month_clean.split(' ')
            month_let = ''
            year_code = ''
            if len(parts) == 2 and parts[0] in INV_MONTH_MAP:
                month_let = INV_MONTH_MAP[parts[0]]
                year_code = parts[1]
            contract_code = f"{com_cd_clean}{month_let}{year_code}" if month_let else com_cd_clean
            
            live_ltp = None
            if live_prices:
                if contract_code in live_prices:
                    live_ltp = float(live_prices[contract_code])
                elif com_cd_clean in live_prices:
                    live_ltp = float(live_prices[com_cd_clean])
            
            if not gp.empty:
                first_row = gp.iloc[0]
                exch = str(first_row.get('Exch_Cd', '')).strip()
                strike = first_row.get('Strike_Price', 0)
                strike = 0 if pd.isna(strike) else float(strike)
                
                callput = first_row.get('Call_Put', '')
                callput = 'NaN' if pd.isna(callput) or str(callput).strip() == '' else str(callput).strip()
                
                # Net position from PHILLIP positions
                net_qty = int(gp.apply(lambda r: r['Traded_Qty'] if r['Buy_Sell'] == 'B' else -r['Traded_Qty'], axis=1).sum())
                
                # Weighted Entry Rate
                buy_gp = gp[gp['Buy_Sell'] == 'B']
                sell_gp = gp[gp['Buy_Sell'] == 'S']
                
                buy_val = float((buy_gp['Traded_Qty'] * buy_gp['Traded_Price']).sum())
                sell_val = float((sell_gp['Traded_Qty'] * sell_gp['Traded_Price']).sum())
                
                grp_buy_qty = float(buy_gp['Traded_Qty'].sum())
                grp_sell_qty = float(sell_gp['Traded_Qty'].sum())
                
                if net_qty > 0 and grp_buy_qty > 0:
                    average_rate = buy_val / grp_buy_qty
                elif net_qty < 0 and grp_sell_qty > 0:
                    average_rate = sell_val / grp_sell_qty
                else:
                    total_trades_qty = grp_buy_qty + grp_sell_qty
                    average_rate = (buy_val + sell_val) / total_trades_qty if total_trades_qty > 0 else 0.0
                
                # Weighted average Closing Price (LTP)
                total_qty_abs = gp['Traded_Qty'].sum()
                weighted_closing_sum = (gp['Traded_Qty'] * gp['Settlement_Price']).sum()
                ltp = float(weighted_closing_sum / total_qty_abs) if total_qty_abs > 0 else 0.0
                
                # Standard Broker MTM
                mtm = float(gp['Unrealised_pl_value'].sum())
                
                # If live_ltp is loaded, dynamically override LTP and calculate Live MTM
                multiplier = float(first_row.get('Tick_Value', 1.0))
                if pd.isna(multiplier) or multiplier == 0:
                    multiplier = 1.0
                    
                if live_ltp is not None:
                    ltp = live_ltp
                    live_mtm_sum = 0.0
                    for _, pos_row in gp.iterrows():
                        side_mult = 1.0 if pos_row['Buy_Sell'] == 'B' else -1.0
                        pos_qty = float(pos_row['Traded_Qty'])
                        pos_entry = float(pos_row['Traded_Price'])
                        live_mtm_sum += (live_ltp - pos_entry) * pos_qty * multiplier * side_mult
                    mtm = live_mtm_sum
                
                # Exchange Delta
                com_type = str(first_row.get('Com_Type', '')).strip()
                exchange_delta = 1 if com_type == 'F' else 0
            else:
                # No overnight position, it is an intraday-only position
                exch = matching_trades.iloc[0]['Exchange'] if not matching_trades.empty else 'SGX'
                strike = 0
                callput = 'NaN'
                net_qty = buy_qty - sell_qty
                
                # Average rate from today's trades
                if net_qty > 0:
                    average_rate = float(matching_trades[matching_trades['Side'] == 'B']['Value'].sum()) / buy_qty if buy_qty > 0 else 0.0
                elif net_qty < 0:
                    average_rate = float(matching_trades[matching_trades['Side'] == 'S']['Value'].sum()) / sell_qty if sell_qty > 0 else 0.0
                else:
                    average_rate = float(matching_trades['Value'].sum()) / (buy_qty + sell_qty) if (buy_qty + sell_qty) > 0 else 0.0
                    
                # Default ltp is last traded price of today's trades
                ltp = float(matching_trades.iloc[-1]['Price']) if not matching_trades.empty else 0.0
                
                if live_ltp is not None:
                    ltp = live_ltp
                    
                # Multiplier fallback
                multiplier = 1.0
                if com_cd_clean == 'MGC': multiplier = 10.0
                elif com_cd_clean == 'SIL': multiplier = 1000.0
                elif com_cd_clean == 'GO': multiplier = 300.0
                elif com_cd_clean == 'SVF': multiplier = 3000.0
                
                buy_val_total = float(matching_trades[matching_trades['Side'] == 'B']['Value'].sum()) if not matching_trades.empty else 0.0
                sell_val_total = float(matching_trades[matching_trades['Side'] == 'S']['Value'].sum()) if not matching_trades.empty else 0.0
                mtm = (sell_val_total - buy_val_total + (net_qty * ltp)) * multiplier
                exchange_delta = 0
                
            bf_qty = net_qty - buy_qty + sell_qty
            scrip = f"{com_cd_clean}-{exch}"
            intraday_mtm = 0.0
            
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
            
        # Net position is the sum of ending net quantities across all contracts
        net_position = sum(p['net_qty'] for p in current_positions)
        
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
        
        # Also write/copy to dist/trader_data.json if dist folder exists for static host support
        if os.path.exists('dist'):
            import shutil
            shutil.copy('trader_data.json', 'dist/trader_data.json')
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

def live_processor_loop():
    print("Starting Live Data Processor Loop...")
    monitored_files = {}
    
    def check_updates():
        trades_file, positions_files = resolve_data_sources()
        all_monitored = [trades_file] + positions_files
        all_monitored = [f for f in all_monitored if f and os.path.exists(f)]
        
        updated = False
        current_mtimes = {}
        for f in all_monitored:
            mtime = os.path.getmtime(f)
            current_mtimes[f] = mtime
            if f not in monitored_files or monitored_files[f] != mtime:
                updated = True
                
        for f in list(monitored_files.keys()):
            if f not in current_mtimes:
                updated = True
                
        return updated, current_mtimes

    # Run once at start
    process_trading_data()
    _, mtimes = check_updates()
    monitored_files = mtimes

    while True:
        try:
            updated, mtimes = check_updates()
            if updated:
                print(f"[{time.strftime('%H:%M:%S')}] Change detected in data source files. Reprocessing...")
                process_trading_data()
                monitored_files = mtimes
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error in live processor loop: {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        live_processor_loop()
    else:
        process_trading_data()
