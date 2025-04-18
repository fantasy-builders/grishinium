"""
Grishinium Blockchain - Web Interface
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
import requests
import json
import time
from typing import Dict, List, Any
import logging
import os
from wallet import GrishiniumWallet
from blockchain import Blockchain
from storage import BlockchainStorage
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blockchain.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
CORS(app)  # Включаем CORS для всех маршрутов
app.config['SECRET_KEY'] = 'grishinium_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")  # Разрешаем CORS для WebSocket

# Конфигурация нод
NODES = [
    {"url": "http://localhost:6000", "name": "Node 0"},
    {"url": "http://localhost:6001", "name": "Node 1"},
    {"url": "http://localhost:6002", "name": "Node 2"}
]

# Инициализация хранилища для кошельков
WALLETS_DIR = "testnet/wallets"
os.makedirs(WALLETS_DIR, exist_ok=True)
logging.info(f"Initialized wallets directory at {WALLETS_DIR}")

# Инициализация блокчейна и хранилища
try:
    storage = BlockchainStorage("testnet/main_node/blockchain.db")
    blockchain = Blockchain()
    logging.info("Blockchain and storage initialized successfully")
except Exception as e:
    logging.error(f"Error initializing blockchain: {str(e)}")
    raise

# Главный кошелек тестнета
main_wallet = None

def initialize_main_wallet():
    global main_wallet
    try:
        wallet_path = os.path.join(WALLETS_DIR, "main_wallet.json")
        if os.path.exists(wallet_path):
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
                seed_phrase = wallet_data.get('seed_phrase')
                if seed_phrase:
                    main_wallet = GrishiniumWallet(seed_phrase=seed_phrase, wallet_name="main_wallet")
                    main_wallet.address = wallet_data.get('address')
                    main_wallet.balance = wallet_data.get('balance', 21_000_000)
                    logging.info(f"Loaded main wallet from {wallet_path}")
                else:
                    raise ValueError("Invalid wallet data: missing seed phrase")
        else:
            main_wallet = GrishiniumWallet.create_wallet(password="testnet", wallet_name="main_wallet")
            main_wallet.balance = 21_000_000  # Устанавливаем начальный баланс
            wallet_data = {
                'seed_phrase': main_wallet.get_seed_phrase(),
                'address': main_wallet.get_address(),
                'balance': main_wallet.balance
            }
            with open(wallet_path, 'w') as f:
                json.dump(wallet_data, f)
            logging.info(f"Created new main wallet at {wallet_path}")
    except Exception as e:
        logging.error(f"Error initializing main wallet: {str(e)}")
        raise

# Инициализация главного кошелька при запуске
initialize_main_wallet()

# Добавляем константы для заданий
TASK_REWARDS = {
    'telegram': 0.1,  # 0.1 GRISH за подписку на Telegram канал
    'twitter': 0.1,   # 0.1 GRISH за подписку на Twitter
    'linkedin': 0.1   # 0.1 GRISH за подписку на LinkedIn
}

# Список доступных заданий
AVAILABLE_TASKS = {
    'telegram': [
        {'id': 'grishinium_news', 'name': 'Grishinium News', 'url': 'https://t.me/grishinium_news'},
        {'id': 'grishinium_community', 'name': 'Grishinium Community', 'url': 'https://t.me/grishinium_community'},
        {'id': 'grishinium_announcements', 'name': 'Grishinium Announcements', 'url': 'https://t.me/grishinium_announcements'},
        {'id': 'grishinium_tech', 'name': 'Grishinium Tech', 'url': 'https://t.me/grishinium_tech'},
        {'id': 'grishinium_events', 'name': 'Grishinium Events', 'url': 'https://t.me/grishinium_events'}
    ],
    'twitter': [
        {'id': 'grishinium_official', 'name': 'Grishinium Official', 'url': 'https://twitter.com/grishinium'},
        {'id': 'grishinium_dev', 'name': 'Grishinium Dev', 'url': 'https://twitter.com/grishinium_dev'}
    ],
    'linkedin': [
        {'id': 'grishinium_company', 'name': 'Grishinium Company', 'url': 'https://linkedin.com/company/grishinium'}
    ]
}

@app.route('/')
def index():
    """Главная страница."""
    return render_template('index.html', nodes=NODES)

@app.route('/wallets')
def wallets_page():
    return render_template('wallets.html')

@app.route('/blocks')
def blocks_page():
    return render_template('blocks.html')

@app.route('/api/wallets')
def get_wallets():
    try:
        wallets = []
        for filename in os.listdir(WALLETS_DIR):
            if filename != "main_wallet.json" and filename.endswith('.json'):
                with open(os.path.join(WALLETS_DIR, filename), 'r') as f:
                    wallet_data = json.load(f)
                    seed_phrase = wallet_data.get('seed_phrase')
                    if seed_phrase:
                        wallet = GrishiniumWallet(seed_phrase=seed_phrase, wallet_name=filename[:-5])
                        wallets.append({
                            'name': filename[:-5],  # Убираем .json
                            'address': wallet.get_address(),
                            'balance': blockchain.get_balance(wallet.get_address())
                        })
        return jsonify({'wallets': wallets})
    except Exception as e:
        logging.error(f"Error getting wallets: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/main-wallet')
def get_main_wallet():
    try:
        return jsonify({
            'address': main_wallet.get_address(),
            'balance': blockchain.get_balance(main_wallet.get_address())
        })
    except Exception as e:
        logging.error(f"Error getting main wallet: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-wallet', methods=['POST'])
def create_wallet():
    try:
        logging.info("Received create wallet request")
        logging.info(f"Request headers: {dict(request.headers)}")
        logging.info(f"Request content type: {request.content_type}")
        
        if not request.is_json:
            logging.error("Request is not JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        logging.info(f"Received create wallet request with data: {data}")
        
        if not data:
            logging.error("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        wallet_name = data.get('name')
        logging.info(f"Wallet name from request: {wallet_name}")
        
        if not wallet_name:
            logging.error("No wallet name provided")
            return jsonify({'error': 'Wallet name is required'}), 400
        
        if not isinstance(wallet_name, str):
            logging.error(f"Invalid wallet name type: {type(wallet_name)}")
            return jsonify({'error': 'Wallet name must be a string'}), 400
            
        wallet_name = wallet_name.strip()
        if not wallet_name:
            logging.error("Empty wallet name after stripping")
            return jsonify({'error': 'Wallet name cannot be empty'}), 400
        
        wallet_path = os.path.join(WALLETS_DIR, f"{wallet_name}.json")
        logging.info(f"Checking if wallet exists at path: {wallet_path}")
        
        if os.path.exists(wallet_path):
            logging.error(f"Wallet already exists at path: {wallet_path}")
            return jsonify({'error': 'Wallet with this name already exists'}), 400
        
        logging.info("Creating new wallet")
        try:
            new_wallet = GrishiniumWallet.create_wallet(password="testnet", wallet_name=wallet_name)
            logging.info("Wallet created successfully")
        except Exception as e:
            logging.error(f"Error creating wallet object: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to create wallet: {str(e)}'}), 500
        
        wallet_data = {
            'seed_phrase': new_wallet.get_seed_phrase(),
            'address': new_wallet.get_address()
        }
        logging.info(f"Saving wallet data: {wallet_data}")
        
        try:
            with open(wallet_path, 'w') as f:
                json.dump(wallet_data, f)
            logging.info(f"Wallet data saved successfully to {wallet_path}")
        except Exception as e:
            logging.error(f"Error saving wallet data: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to save wallet data: {str(e)}'}), 500
        
        logging.info(f"Wallet created successfully at {wallet_path}")
        return jsonify({
            'success': True,
            'address': new_wallet.get_address()
        })
    except Exception as e:
        logging.error(f"Error creating wallet: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/initialize-main-wallet', methods=['POST'])
def initialize_main_wallet_balance():
    try:
        # Создаем начальную транзакцию с 21 миллионом токенов
        initial_balance = 21_000_000
        
        # Проверяем, не был ли уже инициализирован кошелек
        current_balance = blockchain.get_balance(main_wallet.get_address())
        if current_balance > 0:
            return jsonify({'error': 'Main wallet is already initialized'}), 400
        
        # Создаем genesis-транзакцию
        tx = blockchain.create_genesis_transaction(main_wallet.get_address(), initial_balance)
        blockchain.add_transaction(tx)
        
        # Создаем genesis-блок, если его еще нет
        if len(blockchain.chain) == 0:
            blockchain.create_genesis_block()
        
        return jsonify({
            'success': True,
            'balance': initial_balance
        })
    except Exception as e:
        logging.error(f"Error initializing main wallet: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/claim', methods=['POST'])
def claim_tokens():
    try:
        data = request.get_json()
        address = data.get('address')
        if not address:
            return jsonify({'error': 'Address is required'}), 400

        # Проверяем, существует ли кошелек
        wallet_exists = False
        for filename in os.listdir(WALLETS_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(WALLETS_DIR, filename), 'r') as f:
                    wallet_data = json.load(f)
                    if wallet_data.get('address') == address:
                        wallet_exists = True
                        break

        if not wallet_exists:
            return jsonify({'error': 'Wallet not found'}), 404

        # Проверяем, прошло ли 24 часа с последнего клейма
        last_claim_file = os.path.join(WALLETS_DIR, f"{address}_last_claim.json")
        if os.path.exists(last_claim_file):
            with open(last_claim_file, 'r') as f:
                last_claim_data = json.load(f)
                last_claim_time = last_claim_data.get('timestamp', 0)
                current_time = time.time()
                if current_time - last_claim_time < 24 * 60 * 60:  # 24 hours in seconds
                    return jsonify({'error': 'Please wait 24 hours between claims'}), 400

        # Создаем транзакцию для клейма
        claim_amount = 100  # Количество токенов за клейм
        tx = blockchain.create_transaction(main_wallet.get_address(), address, claim_amount)
        blockchain.add_transaction(tx)

        # Сохраняем время последнего клейма
        with open(last_claim_file, 'w') as f:
            json.dump({'timestamp': time.time()}, f)

        return jsonify({
            'success': True,
            'amount': claim_amount
        })
    except Exception as e:
        logging.error(f"Error claiming tokens: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    try:
        statuses = {}
        for node in NODES:
            try:
                response = requests.get(f"{node['url']}/ping", timeout=5)
                if response.status_code == 200:
                    statuses[node["url"]] = {
                        "status": "online",
                        "data": response.json()
                    }
                else:
                    statuses[node["url"]] = {
                        "status": "error",
                        "message": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                statuses[node["url"]] = {
                    "status": "offline",
                    "message": str(e)
                }
        return jsonify(statuses)
    except Exception as e:
        logging.error(f"Error getting node status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chain')
def get_chain():
    try:
        return jsonify({
            'current_node': {
                'blocks': [block.to_dict() for block in blockchain.chain],
                'pending_transactions': [tx.to_dict() for tx in blockchain.pending_transactions]
            }
        })
    except Exception as e:
        logging.error(f"Error getting chain info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet_new():
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Wallet name is required'}), 400
            
        wallet_name = data['name'].strip()
        if not wallet_name:
            return jsonify({'error': 'Wallet name cannot be empty'}), 400
            
        # Check if wallet already exists
        wallet_path = os.path.join(WALLETS_DIR, f"{wallet_name}.json")
        if os.path.exists(wallet_path):
            return jsonify({'error': 'Wallet with this name already exists'}), 400
            
        # Create wallet with the provided name
        wallet = GrishiniumWallet.create_wallet(password="testnet", wallet_name=wallet_name)
        wallet_data = {
            'address': wallet.address,
            'seed_phrase': wallet.seed_phrase,
            'balance': 0
        }
        
        # Save wallet
        with open(wallet_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        logging.info(f"Created new wallet: {wallet.address} with name: {wallet_name}")
        return jsonify(wallet_data)
    except Exception as e:
        logging.error(f"Error creating wallet: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wallet/balance/<address>', methods=['GET'])
def get_balance(address):
    try:
        balance = blockchain.get_balance(address)
        return jsonify({'balance': balance})
    except Exception as e:
        logging.error(f"Error getting balance for {address}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wallet/claim', methods=['POST'])
def claim_tokens_new():
    try:
        data = request.get_json()
        if not data or 'address' not in data:
            return jsonify({'error': 'Address is required'}), 400
        
        address = data['address']
        wallet_path = os.path.join(WALLETS_DIR, f'{address}.json')
        
        if not os.path.exists(wallet_path):
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Проверяем, не получал ли кошелек токены ранее
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            if wallet_data.get('has_claimed', False):
                return jsonify({'error': 'Tokens already claimed'}), 400
        
        # Отправляем токены
        amount = 1000  # Количество токенов для клейма
        blockchain.send_tokens(main_wallet.address, address, amount)
        
        # Обновляем баланс и статус клейма
        wallet_data['balance'] = amount
        wallet_data['has_claimed'] = True
        with open(wallet_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        logging.info(f"Claimed {amount} tokens for {address}")
        return jsonify(wallet_data)
    except Exception as e:
        logging.error(f"Error claiming tokens: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_available_tasks():
    """Получить список доступных заданий"""
    try:
        return jsonify({
            'tasks': AVAILABLE_TASKS,
            'rewards': TASK_REWARDS
        })
    except Exception as e:
        logging.error(f"Error getting available tasks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/subscribe', methods=['POST'])
def subscribe_to_channel():
    try:
        data = request.get_json()
        if not data or 'address' not in data or 'taskId' not in data or 'taskType' not in data:
            return jsonify({'error': 'Address, taskId and taskType are required'}), 400
        
        address = data['address']
        task_id = data['taskId']
        task_type = data['taskType']
        
        # Проверяем существование кошелька
        wallet_path = os.path.join(WALLETS_DIR, f'{address}.json')
        if not os.path.exists(wallet_path):
            return jsonify({'error': 'Wallet not found'}), 404
            
        # Проверяем тип задания
        if task_type not in AVAILABLE_TASKS:
            return jsonify({'error': 'Invalid task type'}), 400
            
        # Проверяем существование задания
        task_exists = any(task['id'] == task_id for task in AVAILABLE_TASKS[task_type])
        if not task_exists:
            return jsonify({'error': 'Task not found'}), 404
            
        # Проверяем, не было ли уже выполнено это задание
        completed_tasks_file = os.path.join(WALLETS_DIR, f'{address}_completed_tasks.json')
        completed_tasks = {}
        if os.path.exists(completed_tasks_file):
            with open(completed_tasks_file, 'r') as f:
                completed_tasks = json.load(f)
                
        task_key = f"{task_type}_{task_id}"
        if task_key in completed_tasks:
            return jsonify({'error': 'Task already completed'}), 400
            
        # Отправляем награду
        reward = TASK_REWARDS[task_type]
        blockchain.send_tokens(main_wallet.address, address, reward)
        
        # Обновляем баланс кошелька
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            wallet_data['balance'] = blockchain.get_balance(address)
            with open(wallet_path, 'w') as f:
                json.dump(wallet_data, f, indent=2)
        
        # Отмечаем задание как выполненное
        completed_tasks[task_key] = {
            'timestamp': time.time(),
            'reward': reward
        }
        with open(completed_tasks_file, 'w') as f:
            json.dump(completed_tasks, f, indent=2)
        
        logging.info(f"User {address} completed task {task_key} and received {reward} GRISH")
        return jsonify({
            'success': True,
            'message': f'Successfully completed task and received {reward} GRISH',
            'new_balance': wallet_data['balance']
        })
    except Exception as e:
        logging.error(f"Error completing task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/completed', methods=['GET'])
def get_completed_tasks():
    """Получить список выполненных заданий для кошелька"""
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({'error': 'Address is required'}), 400
            
        completed_tasks_file = os.path.join(WALLETS_DIR, f'{address}_completed_tasks.json')
        if not os.path.exists(completed_tasks_file):
            return jsonify({'completed_tasks': {}})
            
        with open(completed_tasks_file, 'r') as f:
            completed_tasks = json.load(f)
            
        return jsonify({'completed_tasks': completed_tasks})
    except Exception as e:
        logging.error(f"Error getting completed tasks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/blockchain/status', methods=['GET'])
def get_blockchain_status():
    try:
        status = {
            'total_supply': blockchain.get_total_supply(),
            'block_height': blockchain.get_block_height(),
            'last_block_hash': blockchain.get_last_block_hash(),
            'difficulty': blockchain.get_difficulty(),
            'network_hash_rate': blockchain.get_network_hash_rate(),
            'main_wallet_balance': blockchain.get_balance(main_wallet.address)
        }
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error getting blockchain status: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        # Запускаем сервер на всех интерфейсах
        socketio.run(app, host='0.0.0.0', port=5001, debug=True)
    except Exception as e:
        logging.error(f"Error starting server: {str(e)}")
        raise 