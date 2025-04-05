#!/usr/bin/env python3
"""
Grishinium Wallet Server - сервер для работы с кошельками Grishinium
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from cryptography.fernet import Fernet
import base64
import requests

# Импортируем модуль кошелька
from wallet import GrishiniumWallet, create_new_wallet, load_existing_wallet
from wallet import InvalidSeedError, InvalidPasswordError, WalletExistsError, WalletNotFoundError

# Импортируем компоненты блокчейна
from storage import BlockchainStorage

# Initialize constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
NODE_URL = "http://localhost:5000"  # URL ноды по умолчанию

# Initialize the Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = app.logger

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet_api():
    """
    Создает новый кошелек.
    
    JSON параметры:
        password (str): Пароль для кошелька
        wallet_name (str, опционально): Имя кошелька
        
    Возвращает:
        JSON с адресом и seed-фразой кошелька
    """
    try:
        data = request.get_json()
        
        if not data or 'password' not in data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Password is required'
            }), 400
        
        password = data['password']
        wallet_name = data.get('wallet_name', 'default_wallet')
        
        # Создаем кошелек
        wallet = GrishiniumWallet.create_wallet(password, wallet_name)
        
        return jsonify({
            'status': 'success',
            'message': 'Wallet created successfully',
            'address': wallet.get_address(),
            'seed_phrase': wallet.get_seed_phrase()
        }), 200
    except WalletExistsError as e:
        return jsonify({
            'error': 'Wallet exists',
            'message': str(e)
        }), 400
    except Exception as e:
        app.logger.error(f"Error creating wallet: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/wallet/load', methods=['POST'])
def load_wallet_api():
    """
    Загружает существующий кошелек.
    
    JSON параметры:
        seed_phrase (str): Seed-фраза
        password (str): Пароль для кошелька
        wallet_name (str, опционально): Имя кошелька
        
    Возвращает:
        JSON с адресом кошелька
    """
    try:
        data = request.get_json()
        
        if not data or 'seed_phrase' not in data or 'password' not in data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Seed phrase and password are required'
            }), 400
        
        seed_phrase = data['seed_phrase']
        password = data['password']
        wallet_name = data.get('wallet_name', 'default_wallet')
        
        # Загружаем кошелек
        wallet = GrishiniumWallet.load_wallet(seed_phrase, password, wallet_name)
        
        return jsonify({
            'status': 'success',
            'message': 'Wallet loaded successfully',
            'address': wallet.get_address()
        }), 200
    except (InvalidSeedError, InvalidPasswordError) as e:
        return jsonify({
            'error': 'Invalid credentials',
            'message': str(e)
        }), 400
    except WalletNotFoundError as e:
        return jsonify({
            'error': 'Wallet not found',
            'message': str(e)
        }), 404
    except Exception as e:
        app.logger.error(f"Error loading wallet: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/wallet/send', methods=['POST'])
def send_transaction_api():
    """
    Создает и отправляет транзакцию.
    
    JSON параметры:
        seed_phrase (str): Seed-фраза
        password (str): Пароль для кошелька
        recipient (str): Адрес получателя
        amount (float): Сумма для отправки
        fee (float, опционально): Комиссия за транзакцию
        
    Возвращает:
        JSON с результатом отправки транзакции
    """
    try:
        data = request.get_json()
        
        required_fields = ['seed_phrase', 'password', 'recipient', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': 'Bad request',
                    'message': f'Field {field} is required'
                }), 400
        
        seed_phrase = data['seed_phrase']
        password = data['password']
        recipient = data['recipient']
        amount = float(data['amount'])
        fee = float(data.get('fee', 0.001))
        
        # Загружаем кошелек
        wallet = GrishiniumWallet.load_wallet(seed_phrase, password)
        
        # Создаем транзакцию
        transaction = wallet.create_transaction(recipient, amount, fee)
        
        # Получаем доступ к хранилищу и добавляем транзакцию
        storage = BlockchainStorage(data_dir=DATA_DIR)
        
        # Проверяем баланс отправителя
        balance = storage.get_balance(wallet.get_address())
        if balance < amount + fee:
            return jsonify({
                'error': 'Insufficient funds',
                'message': f'Balance: {balance} GRS, Required: {amount + fee} GRS'
            }), 400
        
        # Добавляем транзакцию в пул неподтвержденных транзакций
        transaction_id = f"{hash(str(transaction))}-{int(time.time())}"
        if hasattr(transaction, 'id'):
            transaction.id = transaction_id
        
        storage.add_pending_transaction(transaction)
        
        return jsonify({
            'status': 'success',
            'message': 'Transaction sent successfully',
            'transaction_id': transaction_id if hasattr(transaction, 'id') else 'Unknown'
        }), 200
    except (InvalidSeedError, InvalidPasswordError) as e:
        return jsonify({
            'error': 'Invalid credentials',
            'message': str(e)
        }), 400
    except Exception as e:
        app.logger.error(f"Error sending transaction: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/balance/<address>', methods=['GET'])
def get_balance_api(address):
    """
    Получает баланс адреса.
    
    Параметры:
        address (str): Адрес кошелька Grishinium
        
    Возвращает:
        JSON с балансом адреса
    """
    if not address.startswith('GRS_'):
        return jsonify({
            'error': 'Invalid address format',
            'message': 'Address must start with GRS_'
        }), 400
    
    try:
        # Получаем доступ к хранилищу
        storage = BlockchainStorage(data_dir=DATA_DIR)
        
        # Получаем баланс
        balance = storage.get_balance(address)
        
        return jsonify({
            'address': address,
            'balance': balance
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting balance for {address}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/transactions/<address>', methods=['GET'])
def get_transactions_api(address):
    """
    Получает историю транзакций для адреса.
    
    Параметры:
        address (str): Адрес кошелька Grishinium
        
    Параметры запроса:
        limit (int, опционально): Максимальное количество транзакций
        offset (int, опционально): Смещение для пагинации
        
    Возвращает:
        JSON со списком транзакций
    """
    try:
        # Получаем параметры пагинации
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Получаем доступ к хранилищу
        storage = BlockchainStorage(data_dir=DATA_DIR)
        
        # Получаем историю транзакций для адреса
        transactions = storage.get_transactions_by_address(address, limit, offset)
        
        # Преобразуем транзакции в JSON
        transactions_json = []
        for tx in transactions:
            # Если tx это словарь, используем его напрямую, иначе используем __dict__
            if isinstance(tx, dict):
                tx_dict = tx.copy()
            else:
                tx_dict = tx.__dict__.copy() if hasattr(tx, '__dict__') else {'error': 'Unknown transaction format'}
            
            # Убедимся, что у нас есть все необходимые поля
            if 'id' not in tx_dict and hasattr(tx, 'id'):
                tx_dict['id'] = tx.id
            if 'sender' not in tx_dict and hasattr(tx, 'sender'):
                tx_dict['sender'] = tx.sender
            if 'recipient' not in tx_dict and hasattr(tx, 'recipient'):
                tx_dict['recipient'] = tx.recipient
            if 'amount' not in tx_dict and hasattr(tx, 'amount'):
                tx_dict['amount'] = tx.amount
            if 'timestamp' not in tx_dict and hasattr(tx, 'timestamp'):
                tx_dict['timestamp'] = tx.timestamp
            if 'fee' not in tx_dict and hasattr(tx, 'fee'):
                tx_dict['fee'] = tx.fee
            
            # Добавляем индикатор, подтверждена ли транзакция
            tx_dict['confirmed'] = True  # По умолчанию считаем транзакцию подтвержденной
            
            transactions_json.append(tx_dict)
        
        return jsonify({
            'address': address,
            'count': len(transactions_json),
            'transactions': transactions_json
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting transactions for {address}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/pending-transactions', methods=['GET'])
def get_pending_transactions_api():
    """
    Получает список ожидающих транзакций.
    
    Параметры запроса:
        address (str, опционально): Фильтр по адресу
        
    Возвращает:
        JSON со списком ожидающих транзакций
    """
    try:
        # Получаем адрес для фильтрации, если он указан
        address = request.args.get('address', None)
        
        # Получаем доступ к хранилищу
        storage = BlockchainStorage(data_dir=DATA_DIR)
        
        # Получаем список ожидающих транзакций
        pending_transactions = storage.get_pending_transactions()
        
        # Фильтруем транзакции по адресу, если он указан
        if address:
            filtered_transactions = []
            for tx in pending_transactions:
                sender = tx.sender if hasattr(tx, 'sender') else None
                recipient = tx.recipient if hasattr(tx, 'recipient') else None
                if sender == address or recipient == address:
                    filtered_transactions.append(tx)
        else:
            filtered_transactions = pending_transactions
        
        # Преобразуем транзакции в JSON
        transactions_json = []
        for tx in filtered_transactions:
            if isinstance(tx, dict):
                tx_dict = tx.copy()
            else:
                tx_dict = tx.__dict__.copy() if hasattr(tx, '__dict__') else {'error': 'Unknown transaction format'}
            
            # Убедимся, что у нас есть все необходимые поля
            if 'id' not in tx_dict and hasattr(tx, 'id'):
                tx_dict['id'] = tx.id
            if 'sender' not in tx_dict and hasattr(tx, 'sender'):
                tx_dict['sender'] = tx.sender
            if 'recipient' not in tx_dict and hasattr(tx, 'recipient'):
                tx_dict['recipient'] = tx.recipient
            if 'amount' not in tx_dict and hasattr(tx, 'amount'):
                tx_dict['amount'] = tx.amount
            if 'timestamp' not in tx_dict and hasattr(tx, 'timestamp'):
                tx_dict['timestamp'] = tx.timestamp
            if 'fee' not in tx_dict and hasattr(tx, 'fee'):
                tx_dict['fee'] = tx.fee
            
            # Добавляем индикатор, что это неподтвержденная транзакция
            tx_dict['confirmed'] = False
            
            transactions_json.append(tx_dict)
        
        return jsonify({
            'count': len(transactions_json),
            'transactions': transactions_json
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting pending transactions: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Маршрут для обслуживания фронтенда
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """Обслуживает React приложение."""
    # Путь к директории с фронтендом
    static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Wallet')
    
    if path and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    else:
        return send_from_directory(static_folder, 'index.html')

def main():
    """Основная функция для запуска сервера."""
    # Объявляем, что будем использовать глобальные переменные
    global DATA_DIR, NODE_URL
    
    parser = argparse.ArgumentParser(description='Grishinium Wallet Server')
    
    parser.add_argument('--host', type=str, default='0.0.0.0',
                      help='Хост для запуска сервера (по умолчанию: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080,
                      help='Порт для запуска сервера (по умолчанию: 8080)')
    parser.add_argument('--data-dir', type=str, default=DATA_DIR,
                      help=f'Директория для данных блокчейна (по умолчанию: {DATA_DIR})')
    parser.add_argument('--node-url', type=str, default=NODE_URL,
                      help=f'URL ноды блокчейна (по умолчанию: {NODE_URL})')
    
    args = parser.parse_args()
    
    # Обновляем глобальные настройки
    DATA_DIR = args.data_dir
    NODE_URL = args.node_url
    
    # Проверяем, что директория данных существует
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"Создана директория для данных: {DATA_DIR}")
    
    # Запускаем сервер
    print(f"Запуск сервера Grishinium Wallet на http://{args.host}:{args.port}")
    print(f"Директория данных: {DATA_DIR}")
    print(f"URL ноды блокчейна: {NODE_URL}")
    app.run(host=args.host, port=args.port, debug=True)

if __name__ == "__main__":
    main() 