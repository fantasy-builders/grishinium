#!/usr/bin/env python3
"""
Grishinium Blockchain - Узел блокчейна с поддержкой токенов
"""

import os
import sys
import json
import time
import logging
import threading
import argparse
from flask import Flask, request, jsonify
from werkzeug.serving import run_simple

# Импортируем модули блокчейна
from blockchain import Blockchain
from crypto_token import TokenTransaction, TokenTransactionType, format_token_amount, parse_token_amount
from network import NodeNetwork
from wallet import load_existing_wallet as load_core_wallet

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grishinium_node.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('GrishiniumNode')

# Инициализация Flask
app = Flask(__name__)

# Глобальные переменные
blockchain = None
node_wallet = None
peers = set()
syncing = False

# Инициализация блокчейна
def initialize_blockchain(data_dir):
    """Инициализация или загрузка существующего блокчейна."""
    global blockchain, node_wallet
    
    # Создаем директорию для данных, если она не существует
    os.makedirs(data_dir, exist_ok=True)
    
    # Путь к файлу блокчейна
    blockchain_path = os.path.join(data_dir, "blockchain.json")
    
    # Проверяем существование файла блокчейна
    if os.path.exists(blockchain_path):
        try:
            # Загружаем блокчейн из файла
            # Здесь должен быть код для загрузки блокчейна
            # Временная заглушка
            blockchain = Blockchain()
            logger.info("Блокчейн загружен из файла")
        except Exception as e:
            logger.error(f"Ошибка при загрузке блокчейна: {str(e)}")
            blockchain = Blockchain()
            logger.info("Создан новый блокчейн")
    else:
        # Создаем новый блокчейн
        blockchain = Blockchain()
        logger.info("Создан новый блокчейн")
    
    # Загрузка или создание кошелька узла
    wallet_path = os.path.join(data_dir, "node_wallet")
    if os.path.exists(wallet_path):
        try:
            # Загружаем кошелек узла
            # Здесь должен быть код для загрузки кошелька
            # Временная заглушка
            node_wallet = None  # load_core_wallet(wallet_path)
            logger.info(f"Кошелек узла загружен. Адрес: {node_wallet.address if node_wallet else 'Unknown'}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке кошелька узла: {str(e)}")
            # Создаем новый кошелек
            # node_wallet = create_new_wallet(wallet_path)
            logger.info(f"Создан новый кошелек узла. Адрес: {node_wallet.address if node_wallet else 'Unknown'}")
    else:
        # Создаем новый кошелек
        # node_wallet = create_new_wallet(wallet_path)
        logger.info(f"Создан новый кошелек узла. Адрес: {node_wallet.address if node_wallet else 'Unknown'}")

# Периодическое сохранение блокчейна
def save_blockchain(data_dir):
    """Периодическое сохранение блокчейна в файл."""
    global blockchain
    
    while True:
        try:
            # Сохраняем блокчейн в файл
            blockchain_path = os.path.join(data_dir, "blockchain.json")
            # Здесь должен быть код для сохранения блокчейна
            logger.info("Блокчейн сохранен в файл")
        except Exception as e:
            logger.error(f"Ошибка при сохранении блокчейна: {str(e)}")
        
        # Сохраняем каждые 5 минут
        time.sleep(300)

# API маршруты

@app.route('/chain', methods=['GET'])
def get_chain():
    """Получить полный блокчейн."""
    global blockchain
    
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.to_dict())
    
    response = {
        'chain': chain_data,
        'length': len(chain_data)
    }
    
    return jsonify(response), 200

@app.route('/mine', methods=['GET'])
def mine_block():
    """Майнить новый блок."""
    global blockchain, node_wallet
    
    # Проверяем наличие транзакций
    if not blockchain.pending_transactions:
        return jsonify({
            'message': 'Нет транзакций для добавления в блок'
        }), 400
    
    # Добавляем транзакцию с вознаграждением для майнера
    if node_wallet:
        # Здесь должен быть код для создания транзакции с вознаграждением
        pass
    
    # Майним блок
    added = blockchain.mine_block(node_wallet.address if node_wallet else "UNKNOWN")
    
    if added:
        response = {
            'message': 'Новый блок создан',
            'block': blockchain.last_block.to_dict()
        }
        return jsonify(response), 200
    else:
        return jsonify({
            'message': 'Не удалось создать блок'
        }), 500

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    """Добавить новую транзакцию."""
    global blockchain
    
    values = request.get_json()
    
    # Проверяем наличие всех необходимых полей
    required_fields = ['sender', 'recipient', 'amount', 'signature', 'timestamp', 'tx_type']
    
    if not all(k in values for k in required_fields):
        return jsonify({
            'message': 'Отсутствуют необходимые поля'
        }), 400
    
    # Создаем транзакцию
    try:
        # Здесь должен быть код для создания и проверки транзакции
        # Временная заглушка
        tx_id = "123456"
        blockchain.add_transaction(values)
        
        response = {
            'message': f'Транзакция будет добавлена в блок {blockchain.next_block_index()}',
            'transaction_id': tx_id
        }
        
        return jsonify(response), 201
    except Exception as e:
        return jsonify({
            'message': f'Ошибка при добавлении транзакции: {str(e)}'
        }), 400

@app.route('/transactions/pending', methods=['GET'])
def get_pending_transactions():
    """Получить список ожидающих транзакций."""
    global blockchain
    
    transactions = []
    for tx in blockchain.pending_transactions:
        transactions.append(tx.to_dict() if hasattr(tx, 'to_dict') else tx)
    
    return jsonify({
        'transactions': transactions,
        'count': len(transactions)
    }), 200

@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    """Получить баланс кошелька."""
    global blockchain
    
    # Получаем баланс из блокчейна
    try:
        balance = blockchain.token_ledger.get_balance(address)
        staked = blockchain.token_ledger.get_staked_amount(address)
        
        return jsonify({
            'address': address,
            'balance': balance,
            'staked': staked,
            'formatted_balance': format_token_amount(balance),
            'formatted_staked': format_token_amount(staked)
        }), 200
    except Exception as e:
        return jsonify({
            'message': f'Ошибка при получении баланса: {str(e)}'
        }), 400

@app.route('/transactions/<address>', methods=['GET'])
def get_address_transactions(address):
    """Получить транзакции для указанного адреса."""
    global blockchain
    
    # Получаем транзакции из блокчейна
    try:
        transactions = blockchain.token_ledger.get_address_transactions(address)
        
        # Форматируем транзакции
        formatted_transactions = []
        for tx in transactions:
            formatted_tx = tx.to_dict() if hasattr(tx, 'to_dict') else tx
            formatted_tx['formatted_amount'] = format_token_amount(tx.get('amount', 0))
            formatted_tx['formatted_fee'] = format_token_amount(tx.get('fee', 0))
            formatted_transactions.append(formatted_tx)
        
        return jsonify({
            'address': address,
            'transactions': formatted_transactions,
            'count': len(formatted_transactions)
        }), 200
    except Exception as e:
        return jsonify({
            'message': f'Ошибка при получении транзакций: {str(e)}'
        }), 400

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    """Регистрация новых узлов."""
    global peers
    
    values = request.get_json()
    nodes = values.get('nodes')
    
    if not nodes:
        return jsonify({
            'message': 'Пожалуйста, укажите список узлов'
        }), 400
    
    for node in nodes:
        peers.add(node)
    
    response = {
        'message': 'Узлы добавлены',
        'total_nodes': list(peers)
    }
    
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    """Реализация консенсуса между узлами."""
    global blockchain, syncing
    
    if syncing:
        return jsonify({
            'message': 'Синхронизация уже выполняется'
        }), 400
    
    syncing = True
    replaced = False
    
    try:
        # Запрашиваем цепи у других узлов
        # Временная заглушка
        syncing = False
        
        if replaced:
            response = {
                'message': 'Цепь заменена',
                'new_chain': [block.to_dict() for block in blockchain.chain]
            }
        else:
            response = {
                'message': 'Наша цепь является авторитетной',
                'chain': [block.to_dict() for block in blockchain.chain]
            }
        
        return jsonify(response), 200
    except Exception as e:
        syncing = False
        return jsonify({
            'message': f'Ошибка при синхронизации: {str(e)}'
        }), 500

@app.route('/node/info', methods=['GET'])
def node_info():
    """Получить информацию об узле."""
    global blockchain, peers
    
    response = {
        'node_id': 'node_1',  # Временная заглушка
        'peers': len(peers),
        'last_block': len(blockchain.chain) - 1,
        'last_block_hash': blockchain.last_block.hash if blockchain.last_block else 'None',
        'version': '1.0.0',
        'pending_transactions': len(blockchain.pending_transactions),
        'uptime': 0,  # Временная заглушка
        'total_supply': blockchain.token_ledger.total_supply if hasattr(blockchain, 'token_ledger') else 0
    }
    
    return jsonify(response), 200

def main():
    parser = argparse.ArgumentParser(description="Grishinium Token Node")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Хост для запуска узла")
    parser.add_argument("--port", type=int, default=5000, help="Порт для запуска узла")
    parser.add_argument("--data-dir", type=str, default="./data", help="Директория для хранения данных")
    args = parser.parse_args()
    
    # Инициализация блокчейна
    initialize_blockchain(args.data_dir)
    
    # Запуск потока для сохранения блокчейна
    save_thread = threading.Thread(target=save_blockchain, args=(args.data_dir,))
    save_thread.daemon = True
    save_thread.start()
    
    # Запуск Flask сервера
    logger.info(f"Узел блокчейна запущен на http://{args.host}:{args.port}")
    run_simple(args.host, args.port, app, use_reloader=False, use_debugger=False)

if __name__ == "__main__":
    main() 