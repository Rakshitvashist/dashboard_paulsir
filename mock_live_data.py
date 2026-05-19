import time
import random
import os
import shutil
import pandas as pd
from datetime import datetime

TRADES_FILE = '111.csv'

# Dynamically resolve POSITIONS_FILE to match the latest active positions file
import glob
pos_files = glob.glob('PHILLIP_Open_Position_*.csv')
POSITIONS_FILE = 'PHILLIP_Open_Position_XOF9000_20260514.csv'
if pos_files:
    dates = []
    for fn in pos_files:
        parts = fn.split('_')
        if len(parts) >= 5:
            date_code = parts[-1].split('.')[0]
            if date_code.isdigit() and len(date_code) == 8:
                dates.append(date_code)
    if dates:
        latest_date = max(dates)
        xof_files = [f for f in pos_files if latest_date in f and 'XOF9000' in f]
        if xof_files:
            POSITIONS_FILE = xof_files[0]
        else:
            POSITIONS_FILE = [f for f in pos_files if latest_date in f][0]

print(f"Target positions file for live simulation: {POSITIONS_FILE}")

# Create backups first
if not os.path.exists(f"{TRADES_FILE}.bak") and os.path.exists(TRADES_FILE):
    shutil.copy(TRADES_FILE, f"{TRADES_FILE}.bak")
    print(f"Backed up {TRADES_FILE}")

if not os.path.exists(f"{POSITIONS_FILE}.bak") and os.path.exists(POSITIONS_FILE):
    shutil.copy(POSITIONS_FILE, f"{POSITIONS_FILE}.bak")
    print(f"Backed up {POSITIONS_FILE}")

# Extract sample symbols and accounts
try:
    df_trades = pd.read_csv(f"{TRADES_FILE}.bak" if os.path.exists(f"{TRADES_FILE}.bak") else TRADES_FILE, header=None)
    accounts = df_trades[10].unique().tolist()
    symbols = df_trades[4].unique().tolist()
    exchanges = df_trades[9].unique().tolist()
except:
    accounts = ['XOF8016', 'XOF8012', 'XOF8013', 'XOF9000']
    symbols = ['IUK26', 'IUM26', 'DINR']
    exchanges = ['SGX', 'DGCX']

print(f"Using {len(accounts)} accounts and {len(symbols)} symbols to mock data.")

def generate_mock_trade():
    """Generates a random trade execution as a CSV string."""
    trade_id = random.randint(10000, 99999)
    qty = random.randint(1, 100)
    price = round(random.uniform(80.0, 120.0), 2)
    unknown = 1111
    sym = random.choice(symbols)
    side = random.choice(['B', 'S'])
    date_str = datetime.now().strftime("%d-%b-%Y")
    time_str = datetime.now().strftime("%H:%M:%S")
    exec_price = price
    exchange = random.choice(exchanges)
    acc = random.choice(accounts)
    
    return f"{trade_id},{qty},{price},{unknown},{sym},{side},{date_str},{time_str},{exec_price},{exchange},{acc},{acc},{sym}"

def update_positions():
    """Modifies the MTM and Settlement prices in the positions file slightly."""
    if not os.path.exists(POSITIONS_FILE):
        return
        
    try:
        df = pd.read_csv(POSITIONS_FILE)
        # Randomly select a few rows to update
        update_indices = random.sample(range(len(df)), min(10, len(df)))
        
        for idx in update_indices:
            # Fluctuate P&L by up to +/- $50
            change = random.uniform(-50, 50)
            curr_pl = float(df.at[idx, 'Unrealised_pl_value']) if pd.notna(df.at[idx, 'Unrealised_pl_value']) else 0.0
            df.at[idx, 'Unrealised_pl_value'] = round(curr_pl + change, 2)
            
            # Fluctuate Settlement Price slightly
            curr_px = float(df.at[idx, 'Settlement_Price']) if pd.notna(df.at[idx, 'Settlement_Price']) else 100.0
            price_change = random.uniform(-0.5, 0.5)
            df.at[idx, 'Settlement_Price'] = round(curr_px + price_change, 4)
            
        df.to_csv(POSITIONS_FILE, index=False)
    except Exception as e:
        print(f"Failed to update positions: {e}")

if __name__ == "__main__":
    print("Starting Live Synthetic Data Generator...")
    print("Press Ctrl+C to stop.")
    print("=========================================")
    
    try:
        while True:
            # 1. Append new trades to 111.csv
            num_trades = random.randint(1, 5)
            with open(TRADES_FILE, 'a') as f:
                for _ in range(num_trades):
                    trade_line = generate_mock_trade()
                    f.write(f"{trade_line}\n")
            
            # 2. Update positions file
            update_positions()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Simulated {num_trades} new trades and updated MTM positions.")
            
            # Wait 1 second
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")
