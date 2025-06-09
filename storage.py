"""
Grishinium Storage Module - Модуль для хранения данных блокчейна
"""

import os
import json
import sqlite3
import logging
from typing import Optional, Dict, List, Any
from blockchain import Blockchain, Block

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumStorage')

class BlockchainStorage:
    """Класс для хранения данных блокчейна."""
    
    def __init__(self, data_dir: str) -> None:
        """
        Инициализация хранилища.
        
        Args:
            data_dir: Директория для хранения данных
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Инициализируем базу данных
        self.db_path = os.path.join(data_dir, 'blockchain.db')
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Создаем таблицы, если они не существуют
        self._create_tables()
        
        logger.info("База данных блокчейна инициализирована")
        logger.info(f"Хранилище блокчейна инициализировано в {data_dir}")
        
    def _create_tables(self) -> None:
        """Создает необходимые таблицы в базе данных."""
        # Таблица для блоков
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocks (
                hash TEXT PRIMARY KEY,
                block_index INTEGER,
                previous_hash TEXT,
                timestamp REAL,
                transactions TEXT,
                validator TEXT,
                signature TEXT
                )
            ''')
            
        # Таблица для транзакций
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                hash TEXT PRIMARY KEY,
                block_hash TEXT,
                sender TEXT,
                recipient TEXT,
                amount REAL,
                timestamp REAL,
                    signature TEXT,
                type TEXT,
                FOREIGN KEY (block_hash) REFERENCES blocks(hash)
                )
            ''')
            
        # Таблица для стейков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stakes (
                    address TEXT PRIMARY KEY,
                amount REAL,
                timestamp REAL,
                can_unstake INTEGER
                )
            ''')
            
        self.conn.commit()
        
    def save_state(self, blockchain: Blockchain) -> None:
        """
        Сохраняет состояние блокчейна.
        
        Args:
            blockchain: Экземпляр блокчейна для сохранения
        """
        # Очищаем таблицы
        self.cursor.execute('DELETE FROM transactions')
        self.cursor.execute('DELETE FROM blocks')
        self.cursor.execute('DELETE FROM stakes')
        
        # Сохраняем блоки и транзакции
        for block in blockchain.chain:
            # Сохраняем блок
            self.cursor.execute('''
                INSERT INTO blocks (hash, block_index, previous_hash, timestamp, transactions, validator, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                block.hash,
                block.index,
                block.previous_hash,
                block.timestamp,
                json.dumps(block.transactions),
                block.validator,
                block.signature
            ))
            
            # Сохраняем транзакции блока
            for tx in block.transactions:
                self.cursor.execute('''
                    INSERT INTO transactions (hash, block_hash, sender, recipient, amount, timestamp, signature, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tx.get('hash', ''),
                    block.hash,
                    tx.get('from', ''),
                    tx.get('to', ''),
                    tx.get('amount', 0),
                    tx.get('timestamp', 0),
                    tx.get('signature', ''),
                    tx.get('type', 'transfer')
                ))
        
        # Сохраняем стейки
        for address, stake_info in blockchain.consensus.stakes.items():
            self.cursor.execute('''
                INSERT INTO stakes (address, amount, timestamp, can_unstake)
                VALUES (?, ?, ?, ?)
        ''', (
                address,
                stake_info['amount'],
                stake_info['timestamp'],
                1 if stake_info['can_unstake'] else 0
            ))
        
        self.conn.commit()
        logger.debug("Состояние блокчейна сохранено")
        
    def load_state(self) -> Optional[Blockchain]:
        """
        Загружает состояние блокчейна.
            
        Returns:
            Optional[Blockchain]: Загруженный блокчейн или None, если нет сохраненного состояния
        """
        # Проверяем, есть ли сохраненные блоки
        self.cursor.execute('SELECT COUNT(*) FROM blocks')
        if self.cursor.fetchone()[0] == 0:
            return None
            
        # Создаем новый экземпляр блокчейна
        blockchain = Blockchain()
        
        # Загружаем блоки
        self.cursor.execute('SELECT * FROM blocks ORDER BY block_index')
        blocks = self.cursor.fetchall()
        
        for block_data in blocks:
            # Получаем транзакции блока
            self.cursor.execute('SELECT * FROM transactions WHERE block_hash = ?', (block_data[0],))
            transactions = []
            for tx_data in self.cursor.fetchall():
                transactions.append({
                    'hash': tx_data[0],
                    'from': tx_data[2],
                    'to': tx_data[3],
                    'amount': tx_data[4],
                    'timestamp': tx_data[5],
                    'signature': tx_data[6],
                    'type': tx_data[7]
                })
            
            # Создаем блок
            block = Block(
                index=block_data[1],
                previous_hash=block_data[2],
                timestamp=block_data[3],
                transactions=transactions,
                validator=block_data[5]
            )
            block.signature = block_data[6]
            
            # Добавляем блок в цепь
            blockchain.chain.append(block)
        
        # Загружаем стейки
        self.cursor.execute('SELECT * FROM stakes')
        for stake_data in self.cursor.fetchall():
            blockchain.consensus.stakes[stake_data[0]] = {
                'amount': stake_data[1],
                'timestamp': stake_data[2],
                'can_unstake': bool(stake_data[3])
            }
        
        logger.info("Состояние блокчейна загружено")
        return blockchain
        
    def close(self) -> None:
        """Закрывает соединение с базой данных."""
        self.conn.close()
        logger.debug("Соединение с базой данных закрыто")
    
    def get_balance(self, address: str) -> float:
        """
        Получает баланс адреса.
        
        Args:
            address: Адрес кошелька
            
        Returns:
            float: Баланс адреса
        """
        # Получаем все транзакции отправленные с адреса
        self.cursor.execute('''
            SELECT SUM(amount) FROM transactions
            WHERE sender = ?
        ''', (address,))
        sent = self.cursor.fetchone()[0] or 0
        
        # Получаем все транзакции полученные адресом
        self.cursor.execute('''
            SELECT SUM(amount) FROM transactions
            WHERE recipient = ?
        ''', (address,))
        received = self.cursor.fetchone()[0] or 0
        
        # Баланс = полученные - отправленные
        balance = received - sent
        
        return balance
    
    def get_staked_amount(self, address: str) -> float:
        """
        Получает сумму застейканных токенов для адреса.
        
        Args:
            address: Адрес кошелька
            
        Returns:
            float: Сумма в стейке или 0, если адрес не имеет стейка
        """
        self.cursor.execute('''
            SELECT amount FROM stakes
            WHERE address = ?
        ''', (address,))
        
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return 0.0
    
    def add_pending_transaction(self, transaction: Dict) -> None:
        """
        Добавляет транзакцию в пул ожидающих.
        
        Args:
            transaction: Данные транзакции
        """
        # Сохраняем в файл пула ожидающих транзакций
        pending_file = os.path.join(self.data_dir, 'pending_transactions.json')
        
        # Загружаем существующие ожидающие транзакции
        pending_transactions = []
        if os.path.exists(pending_file):
            try:
                with open(pending_file, 'r') as f:
                    pending_transactions = json.load(f)
            except json.JSONDecodeError:
                logger.error("Ошибка при чтении пула ожидающих транзакций")
                pending_transactions = []
        
        # Добавляем новую транзакцию
        pending_transactions.append(transaction)
        
        # Сохраняем обновленный пул транзакций
        with open(pending_file, 'w') as f:
            json.dump(pending_transactions, f, indent=2)
            
        logger.debug(f"Транзакция добавлена в пул ожидающих: {transaction.get('hash', '')}") 