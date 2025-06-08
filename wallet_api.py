#!/usr/bin/env python3
"""
Grishinium Wallet API - API-интерфейс для интеграции кошельков с блокчейном Grishinium
"""

import os
import time
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Tuple, Any, Union
import base64

# Flask и зависимости API
from flask import Blueprint, request, jsonify, current_app

# Импортируем компоненты блокчейна
from Blockchain.storage import BlockchainStorage
from Blockchain.transaction import Transaction, validate_transaction
from Blockchain.mining import calculate_transaction_hash

# Импортируем модуль кошелька
from Blockchain.wallet import GrishiniumWallet

# Создаем Blueprint для API кошелька
wallet_api = Blueprint('wallet_api', __name__)

@wallet_api.route('/api/create-wallet', methods=['POST'])
def create_wallet():
    """
    Creates a new wallet with optional seed phrase.
    
    JSON parameters:
        name (str): The name of the wallet
        seed_phrase (str, optional): Seed phrase to use for wallet generation
        
    Returns:
        JSON with the created wallet details
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Wallet name is required'
            }), 400
        
        wallet_name = data['name']
        seed_phrase = data.get('seed_phrase', None)
        
        # Create a new wallet
        if seed_phrase:
            # Use provided seed phrase
            wallet = GrishiniumWallet.from_seed_phrase(seed_phrase, wallet_name)
        else:
            # Generate a new wallet with random seed
            wallet = GrishiniumWallet.create(wallet_name)
            # Generate a seed phrase from the private key
            seed_phrase = wallet.generate_seed_phrase()
        
        # Save wallet to storage
        wallet_data = {
            'name': wallet_name,
            'address': wallet.address,
            'public_key': wallet.get_public_key_str(),
            'private_key': wallet.get_private_key_str(),  # Encrypted in the real implementation
            'seed_phrase': seed_phrase,  # Should be encrypted in real implementation
            'created_at': time.time()
        }
        
        # Get wallet storage path
        wallet_dir = os.path.join(current_app.config.get('DATA_DIR', './data'), 'wallets')
        os.makedirs(wallet_dir, exist_ok=True)
        
        # Save wallet data to file
        wallet_file = os.path.join(wallet_dir, f"{wallet.address}.json")
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        # Return wallet info without sensitive data
        return jsonify({
            'status': 'success',
            'wallet': {
                'name': wallet_name,
                'address': wallet.address,
                'balance': 0,  # New wallet starts with 0 balance
                'created_at': wallet_data['created_at']
            }
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error creating wallet: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/import-wallet', methods=['POST'])
def import_wallet():
    """
    Imports a wallet using a seed phrase.
    
    JSON parameters:
        name (str): The name for the imported wallet
        seed_phrase (str): The seed phrase to recover the wallet
        
    Returns:
        JSON with the imported wallet details
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'seed_phrase' not in data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Wallet name and seed phrase are required'
            }), 400
        
        wallet_name = data['name']
        seed_phrase = data['seed_phrase']
        
        # Validate seed phrase
        if not seed_phrase or len(seed_phrase.split()) != 12:
            return jsonify({
                'error': 'Invalid seed phrase',
                'message': 'Seed phrase must contain 12 words'
            }), 400
        
        # Import wallet from seed phrase
        try:
            wallet = GrishiniumWallet.from_seed_phrase(seed_phrase, wallet_name)
        except Exception as e:
            return jsonify({
                'error': 'Invalid seed phrase',
                'message': str(e)
            }), 400
        
        # Check if wallet already exists
        wallet_dir = os.path.join(current_app.config.get('DATA_DIR', './data'), 'wallets')
        wallet_file = os.path.join(wallet_dir, f"{wallet.address}.json")
        
        if os.path.exists(wallet_file):
            # Wallet already exists, just return it
            with open(wallet_file, 'r') as f:
                existing_wallet_data = json.load(f)
            
            # Just update the name if needed
            if existing_wallet_data['name'] != wallet_name:
                existing_wallet_data['name'] = wallet_name
                with open(wallet_file, 'w') as f:
                    json.dump(existing_wallet_data, f, indent=2)
            
            # Get balance
            storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
            balance = storage.get_balance(wallet.address)
            
            return jsonify({
                'status': 'success',
                'message': 'Wallet already exists and has been updated',
                'wallet': {
                    'name': wallet_name,
                    'address': wallet.address,
                    'balance': balance,
                    'created_at': existing_wallet_data['created_at']
                }
            }), 200
        
        # Save new wallet data
        wallet_data = {
            'name': wallet_name,
            'address': wallet.address,
            'public_key': wallet.get_public_key_str(),
            'private_key': wallet.get_private_key_str(),  # Should be encrypted in real implementation
            'seed_phrase': seed_phrase,  # Should be encrypted in real implementation
            'created_at': time.time()
        }
        
        # Ensure wallet directory exists
        os.makedirs(wallet_dir, exist_ok=True)
        
        # Save wallet data to file
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        return jsonify({
            'status': 'success',
            'wallet': {
                'name': wallet_name,
                'address': wallet.address,
                'balance': 0,  # New wallet starts with 0 balance
                'created_at': wallet_data['created_at']
            }
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error importing wallet: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/wallets', methods=['GET'])
def get_wallets():
    """
    Gets the list of all wallets.
    
    Returns:
        JSON with the list of wallets and their balances
    """
    try:
        # Get wallet storage path
        wallet_dir = os.path.join(current_app.config.get('DATA_DIR', './data'), 'wallets')
        
        if not os.path.exists(wallet_dir):
            return jsonify({
                'wallets': []
            }), 200
        
        # Get blockchain storage for balance calculations
        storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
        
        # List all wallet files
        wallet_files = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
        
        wallets = []
        for wallet_file in wallet_files:
            with open(os.path.join(wallet_dir, wallet_file), 'r') as f:
                wallet_data = json.load(f)
            
            address = wallet_data['address']
            balance = storage.get_balance(address)
            
            # Get staked amount if applicable
            staked_amount = storage.get_staked_amount(address)
            
            wallets.append({
                'name': wallet_data['name'],
                'address': address,
                'balance': balance,
                'stake': staked_amount,
                'created_at': wallet_data.get('created_at', 0)
            })
        
        # Sort wallets by creation time, newest first
        wallets.sort(key=lambda w: w['created_at'], reverse=True)
        
        return jsonify({
            'wallets': wallets
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting wallets: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/balance/<address>', methods=['GET'])
def get_balance(address):
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
        # Получаем хранилище блокчейна
        storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
        
        # Получаем баланс
        balance = storage.get_balance(address)
        
        return jsonify({
            'address': address,
            'balance': balance
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting balance for {address}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/transaction', methods=['POST'])
def create_transaction():
    """
    Создает новую транзакцию и добавляет ее в пул неподтвержденных транзакций.
    
    JSON параметры:
        sender (str): Адрес отправителя
        recipient (str): Адрес получателя
        amount (float): Сумма транзакции
        fee (float): Комиссия за транзакцию
        timestamp (int): Временная метка (опционально)
        signature (str): Подпись транзакции
        public_key (str): Публичный ключ отправителя
        nonce (int): Случайное число для уникальности (опционально)
        
    Возвращает:
        JSON с результатом создания транзакции
    """
    try:
        # Получаем данные транзакции из запроса
        transaction_data = request.get_json()
        
        if not transaction_data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Transaction data is required'
            }), 400
        
        # Проверяем обязательные поля
        required_fields = ['sender', 'recipient', 'amount', 'fee', 'signature', 'public_key']
        for field in required_fields:
            if field not in transaction_data:
                return jsonify({
                    'error': 'Bad request',
                    'message': f'Field {field} is required'
                }), 400
        
        # Добавляем timestamp, если его нет
        if 'timestamp' not in transaction_data:
            transaction_data['timestamp'] = time.time()
        
        # Получаем хранилище блокчейна
        storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
        
        # Проверяем баланс отправителя
        sender_balance = storage.get_balance(transaction_data['sender'])
        total_amount = float(transaction_data['amount']) + float(transaction_data['fee'])
        
        if sender_balance < total_amount:
            return jsonify({
                'error': 'Insufficient funds',
                'message': f'Sender has {sender_balance} GRS, needs {total_amount} GRS'
            }), 400
        
        # Проверяем подпись транзакции
        # Создаем копию транзакции без подписи для проверки
        tx_for_verification = transaction_data.copy()
        signature = tx_for_verification.pop('signature')
        public_key_str = tx_for_verification.pop('public_key')
        
        # Импортируем публичный ключ
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        public_key_data = base64.b64decode(public_key_str)
        public_key = serialization.load_pem_public_key(
            public_key_data,
            backend=default_backend()
        )
        
        # Создаем строковое представление транзакции
        tx_string = json.dumps(tx_for_verification, sort_keys=True)
        
        # Хешируем транзакцию
        tx_hash = hashlib.sha256(tx_string.encode()).digest()
        
        # Проверяем подпись
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import hashes
            
            public_key.verify(
                base64.b64decode(signature),
                tx_hash,
                ec.ECDSA(hashes.SHA256())
            )
        except Exception as e:
            current_app.logger.error(f"Transaction signature verification failed: {str(e)}")
            return jsonify({
                'error': 'Invalid signature',
                'message': 'Transaction signature verification failed'
            }), 400
        
        # Создаем объект транзакции
        transaction = Transaction(
            sender=transaction_data['sender'],
            recipient=transaction_data['recipient'],
            amount=float(transaction_data['amount']),
            fee=float(transaction_data['fee']),
            timestamp=transaction_data['timestamp'],
            signature=signature,
            public_key=public_key_str
        )
        
        # Вычисляем хеш транзакции
        transaction_id = calculate_transaction_hash(transaction)
        transaction.id = transaction_id
        
        # Добавляем транзакцию в пул неподтвержденных транзакций
        storage.add_pending_transaction(transaction)
        
        current_app.logger.info(f"Transaction created: {transaction_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Transaction created and added to pending pool',
            'transaction_id': transaction_id
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error creating transaction: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/pending-transactions', methods=['GET'])
def get_pending_transactions():
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
        
        # Получаем хранилище блокчейна
        storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
        
        # Получаем список ожидающих транзакций
        pending_transactions = storage.get_pending_transactions()
        
        # Фильтруем транзакции по адресу, если он указан
        if address:
            filtered_transactions = [
                tx for tx in pending_transactions
                if tx.sender == address or tx.recipient == address
            ]
        else:
            filtered_transactions = pending_transactions
        
        # Преобразуем транзакции в JSON
        transactions_json = []
        for tx in filtered_transactions:
            tx_dict = tx.__dict__.copy()
            tx_dict['timestamp'] = tx.timestamp
            transactions_json.append(tx_dict)
        
        return jsonify({
            'count': len(transactions_json),
            'transactions': transactions_json
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting pending transactions: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/transactions/<address>', methods=['GET'])
def get_transactions(address):
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
        
        # Получаем хранилище блокчейна
        storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
        
        # Получаем историю транзакций для адреса
        transactions = storage.get_transactions_by_address(address, limit, offset)
        
        # Преобразуем транзакции в JSON
        transactions_json = []
        for tx in transactions:
            tx_dict = tx.__dict__.copy() if hasattr(tx, '__dict__') else tx
            if hasattr(tx, 'timestamp'):
                tx_dict['timestamp'] = tx.timestamp
            transactions_json.append(tx_dict)
        
        return jsonify({
            'address': address,
            'count': len(transactions_json),
            'transactions': transactions_json
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting transactions for {address}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@wallet_api.route('/api/transactions/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """
    Получает информацию о конкретной транзакции.
    
    Параметры:
        transaction_id (str): ID транзакции
        
    Возвращает:
        JSON с информацией о транзакции
    """
    try:
        # Получаем хранилище блокчейна
        storage = BlockchainStorage(current_app.config.get('DATA_DIR', './data'))
        
        # Получаем транзакцию
        transaction = storage.get_transaction_by_id(transaction_id)
        
        if not transaction:
            return jsonify({
                'error': 'Not found',
                'message': f'Transaction with ID {transaction_id} not found'
            }), 404
        
        # Преобразуем транзакцию в JSON
        tx_dict = transaction.__dict__.copy() if hasattr(transaction, '__dict__') else transaction
        if hasattr(transaction, 'timestamp'):
            tx_dict['timestamp'] = transaction.timestamp
        
        return jsonify({
            'transaction': tx_dict
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting transaction {transaction_id}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

def register_wallet_api(app):
    """
    Регистрирует API-маршруты кошелька в приложении Flask.
    
    Args:
        app: Flask-приложение
    """
    app.register_blueprint(wallet_api)
    app.logger.info("Wallet API routes registered") 