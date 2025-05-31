
import requests
import time
import threading
from datetime import datetime
import os

# === CONFIG ===
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')  # must be string for comparison
CHECK_INTERVAL = 60

WATCHED_WALLETS = {
    '0xcb5969b53c246a3d97e822cb50aecef34569c5af': 'Karen'
}

ETH_MIN = 0.01
TOKEN_MIN = 1000

last_seen_eth = {}
last_seen_token = {}

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_eth_tx(wallet):
    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&sort=desc&apikey={ETHERSCAN_API_KEY}'
    r = requests.get(url).json()
    return r['result'][0] if r.get('status') == '1' and r.get('result') else None

def get_token_tx(wallet):
    url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={wallet}&sort=desc&apikey={ETHERSCAN_API_KEY}'
    r = requests.get(url).json()
    return r['result'][0] if r.get('status') == '1' and r.get('result') else None

def telegram_command_listener():
    last_update_id = 0
    print("📩 Telegram command listener started...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            resp = requests.get(url).json()
            if not resp.get("ok") or "result" not in resp:
                time.sleep(5)
                continue
            for update in resp["result"]:
                update_id = update["update_id"]
                if update_id > last_update_id:
                    last_update_id = update_id
                    message = update.get("message")
                    if not message:
                        continue
                    if str(message.get("chat", {}).get("id")) != CHAT_ID:
                        continue
                    text = message.get("text", "")
                    args = text.split()
                    if text == "/status":
                        send_telegram_msg("✅ Tracker is LIVE.")
                    elif text == "/wallets":
                        wallets = "\n".join([f"{v}: {k}" for k, v in WATCHED_WALLETS.items()])
                        send_telegram_msg(f"🧾 Tracking wallets:\n{wallets}")
                    elif text == "/lasttx":
                        wallet = list(WATCHED_WALLETS.keys())[0]
                        eth = last_seen_eth.get(wallet, 'No ETH TX yet')
                        token = last_seen_token.get(wallet, 'No Token TX yet')
                        send_telegram_msg(f"📦 Last ETH TX: {eth}\n🎯 Last Token TX: {token}")
                    elif args[0] == "/addwallet" and len(args) == 3:
                        addr, name = args[1], args[2]
                        WATCHED_WALLETS[addr] = name
                        send_telegram_msg(f"✅ Added wallet {name}: {addr}")
                    elif args[0] == "/removewallet" and len(args) == 2:
                        to_remove = args[1]
                        found = [k for k, v in WATCHED_WALLETS.items() if v == to_remove]
                        if found:
                            del WATCHED_WALLETS[found[0]]
                            send_telegram_msg(f"❌ Removed wallet {to_remove}")
                        else:
                            send_telegram_msg(f"⚠️ Wallet '{to_remove}' not found.")
        except Exception as e:
            print(f"[COMMAND ERROR] {e}")
        time.sleep(5)

def tracker_loop():
    print("📡 Tracker started...")
    while True:
        for wallet, name in WATCHED_WALLETS.items():
            tx = get_eth_tx(wallet)
            if tx:
                val = int(tx['value']) / 1e18
                if wallet not in last_seen_eth or tx['hash'] != last_seen_eth[wallet]:
                    if val > ETH_MIN:
                        msg = f"💸 ETH TX for {name}:\n{val:.4f} ETH\nHash: {tx['hash']}"
                        send_telegram_msg(msg)
                        last_seen_eth[wallet] = tx['hash']

            tx = get_token_tx(wallet)
            if tx:
                val = int(tx['value']) / (10 ** int(tx['tokenDecimal']))
                if wallet not in last_seen_token or tx['hash'] != last_seen_token[wallet]:
                    if val > TOKEN_MIN:
                        msg = f"🪙 TOKEN TX for {name}:\n{val:.2f} {tx['tokenSymbol']}\nHash: {tx['hash']}"
                        send_telegram_msg(msg)
                        last_seen_token[wallet] = tx['hash']
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=telegram_command_listener).start()
    tracker_loop()
