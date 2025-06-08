from flask import Flask, jsonify, request
import os
import json
from datetime import datetime, timedelta
import glob

app = Flask(__name__)

# Пути к файлам блокчейна
TESTNET_DIR = "testnet"
WALLETS_DIR = os.path.join(TESTNET_DIR, "wallets")
NODES_DIR = os.path.join(TESTNET_DIR, "nodes")

def get_total_wallets():
    """Получить общее количество кошельков"""
    wallet_files = glob.glob(os.path.join(WALLETS_DIR, "*.json"))
    return len(wallet_files)

def get_total_transactions():
    """Получить общее количество транзакций"""
    total = 0
    for node_dir in os.listdir(NODES_DIR):
        node_path = os.path.join(NODES_DIR, node_dir)
        if os.path.isdir(node_path):
            blocks_dir = os.path.join(node_path, "blocks")
            if os.path.exists(blocks_dir):
                for block_file in os.listdir(blocks_dir):
                    if block_file.endswith(".json"):
                        with open(os.path.join(blocks_dir, block_file), "r") as f:
                            block = json.load(f)
                            total += len(block.get("transactions", []))
    return total

def get_total_blocks():
    """Получить общее количество блоков"""
    total = 0
    for node_dir in os.listdir(NODES_DIR):
        node_path = os.path.join(NODES_DIR, node_dir)
        if os.path.isdir(node_path):
            blocks_dir = os.path.join(node_path, "blocks")
            if os.path.exists(blocks_dir):
                total += len([f for f in os.listdir(blocks_dir) if f.endswith(".json")])
    return total

def get_circulating_supply():
    """Получить текущую циркулирующую массу токенов"""
    total = 0
    for wallet_file in os.listdir(WALLETS_DIR):
        if wallet_file.endswith(".json"):
            with open(os.path.join(WALLETS_DIR, wallet_file), "r") as f:
                wallet = json.load(f)
                total += float(wallet.get("balance", 0))
    return total

def get_wallet_growth():
    """Получить данные о росте количества кошельков"""
    wallet_files = glob.glob(os.path.join(WALLETS_DIR, "*.json"))
    dates = []
    counts = []
    
    # Получаем даты создания кошельков
    wallet_dates = []
    for wallet_file in wallet_files:
        with open(wallet_file, "r") as f:
            wallet = json.load(f)
            creation_date = datetime.fromtimestamp(wallet.get("creation_time", 0))
            wallet_dates.append(creation_date)
    
    if not wallet_dates:
        return {"dates": [], "counts": []}
    
    # Сортируем даты
    wallet_dates.sort()
    
    # Создаем временные интервалы
    start_date = wallet_dates[0]
    end_date = datetime.now()
    interval = timedelta(days=1)
    
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        count = sum(1 for d in wallet_dates if d <= current_date)
        counts.append(count)
        current_date += interval
    
    return {"dates": dates, "counts": counts}

def search_blockchain(query):
    """Поиск по блокчейну"""
    # Проверяем, является ли запрос адресом
    if len(query) == 42 and query.startswith("0x"):
        # Поиск по адресу
        for wallet_file in os.listdir(WALLETS_DIR):
            if wallet_file.endswith(".json"):
                with open(os.path.join(WALLETS_DIR, wallet_file), "r") as f:
                    wallet = json.load(f)
                    if wallet.get("address") == query:
                        return {
                            "type": "address",
                            "data": {
                                "address": wallet.get("address"),
                                "balance": float(wallet.get("balance", 0)),
                                "transactions": len(wallet.get("transactions", [])),
                            }
                        }
    
    # Проверяем, является ли запрос хешем транзакции
    if len(query) == 66 and query.startswith("0x"):
        # Поиск транзакции
        for node_dir in os.listdir(NODES_DIR):
            node_path = os.path.join(NODES_DIR, node_dir)
            if os.path.isdir(node_path):
                blocks_dir = os.path.join(node_path, "blocks")
                if os.path.exists(blocks_dir):
                    for block_file in os.listdir(blocks_dir):
                        if block_file.endswith(".json"):
                            with open(os.path.join(blocks_dir, block_file), "r") as f:
                                block = json.load(f)
                                for tx in block.get("transactions", []):
                                    if tx.get("hash") == query:
                                        return {
                                            "type": "transaction",
                                            "data": {
                                                "hash": tx.get("hash"),
                                                "from": tx.get("from"),
                                                "to": tx.get("to"),
                                                "amount": float(tx.get("amount", 0)),
                                                "timestamp": tx.get("timestamp"),
                                            }
                                        }
    
    # Проверяем, является ли запрос номером блока
    try:
        block_number = int(query)
        for node_dir in os.listdir(NODES_DIR):
            node_path = os.path.join(NODES_DIR, node_dir)
            if os.path.isdir(node_path):
                blocks_dir = os.path.join(node_path, "blocks")
                if os.path.exists(blocks_dir):
                    block_file = os.path.join(blocks_dir, f"block_{block_number}.json")
                    if os.path.exists(block_file):
                        with open(block_file, "r") as f:
                            block = json.load(f)
                            return {
                                "type": "block",
                                "data": {
                                    "number": block.get("number"),
                                    "hash": block.get("hash"),
                                    "timestamp": block.get("timestamp"),
                                    "transactions": len(block.get("transactions", [])),
                                }
                            }
    except ValueError:
        pass
    
    return None

@app.route('/api/blockchain/status', methods=['GET'])
def get_blockchain_status():
    """Получить статус блокчейна"""
    try:
        return jsonify({
            "totalWallets": get_total_wallets(),
            "totalTransactions": get_total_transactions(),
            "totalBlocks": get_total_blocks(),
            "circulatingSupply": get_circulating_supply(),
            "totalSupply": 1000000000,  # Максимальное предложение токенов
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/blockchain/status/wallet-growth', methods=['GET'])
def get_wallet_growth_data():
    """Получить данные о росте количества кошельков"""
    try:
        return jsonify(get_wallet_growth())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/blockchain/search', methods=['POST'])
def search():
    """Поиск по блокчейну"""
    try:
        data = request.get_json()
        query = data.get("query")
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        result = search_blockchain(query)
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001) 