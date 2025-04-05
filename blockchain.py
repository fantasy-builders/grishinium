"""
Grishinium Blockchain - Core Blockchain Implementation
"""

import time
import json
import hashlib
from typing import List, Dict, Any, Optional
import logging
from pos_consensus import ProofOfStake

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumBlockchain')

class Block:
    def __init__(self, index: int, previous_hash: str, timestamp: float, 
                 transactions: List[Dict[str, Any]], validator: str) -> None:
        """
        Инициализация блока в блокчейне.
        
        Args:
            index: Индекс блока в цепи
            previous_hash: Хэш предыдущего блока
            timestamp: Временная метка создания блока
            transactions: Список транзакций в блоке
            validator: Адрес валидатора, создавшего блок
        """
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.validator = validator
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Вычисляет SHA-256 хэш блока.
        
        Returns:
            Хэш блока в виде шестнадцатеричной строки
        """
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "validator": self.validator
        }, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует блок в словарь для сериализации.
        
        Returns:
            Словарь с данными блока
        """
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "validator": self.validator,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """
        Создает блок из словаря.
        
        Args:
            block_dict: Словарь с данными блока
            
        Returns:
            Экземпляр блока
        """
        block = cls(
            index=block_dict["index"],
            previous_hash=block_dict["previous_hash"],
            timestamp=block_dict["timestamp"],
            transactions=block_dict["transactions"],
            validator=block_dict["validator"]
        )
        # Проверка, совпадает ли вычисленный хэш с сохраненным
        if block.hash != block_dict["hash"]:
            logger.warning(f"Восстановленный хэш блока {block.index} не совпадает с сохраненным")
        return block


class Blockchain:
    def __init__(self) -> None:
        """
        Инициализация блокчейна.
        """
        self.chain: List[Block] = []
        self.consensus = ProofOfStake()
        self.create_genesis_block()
        
    def create_genesis_block(self) -> None:
        """Создает генезис-блок."""
        genesis_block = Block(
            index=0,
            previous_hash="0",
            timestamp=time.time(),
            transactions=[],
            validator="genesis"
        )
        self.chain.append(genesis_block)
        
    def get_latest_block(self) -> Block:
        """Возвращает последний блок в цепи."""
        return self.chain[-1]
        
    def add_block(self, transactions: List[Dict[str, Any]], validator: str) -> bool:
        """
        Добавляет новый блок в цепь.
        
        Args:
            transactions: Список транзакций
            validator: Адрес валидатора
            
        Returns:
            bool: Успешность операции
        """
        previous_block = self.get_latest_block()
        
        new_block = Block(
            index=len(self.chain),
            previous_hash=previous_block.hash,
            timestamp=time.time(),
            transactions=transactions,
            validator=validator
        )
        
        # Проверяем валидность блока
        if not self.consensus.verify_block(new_block.to_dict(), previous_block.to_dict()):
            logger.warning("Invalid block rejected")
            return False
            
        # Добавляем блок в цепь
        self.chain.append(new_block)
        
        # Рассчитываем и добавляем награду валидатору
        reward = self.consensus.calculate_block_reward(validator)
        if reward > 0:
            reward_transaction = {
                "from": "system",
                "to": validator,
                "amount": reward,
                "timestamp": time.time()
            }
            new_block.transactions.append(reward_transaction)
            
        return True
        
    def is_chain_valid(self) -> bool:
        """
        Проверяет валидность всей цепи.
        
        Returns:
            bool: Валидность цепи
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Проверяем хэш текущего блока
            if current_block.hash != current_block.calculate_hash():
                return False
                
            # Проверяем связь с предыдущим блоком
            if current_block.previous_hash != previous_block.hash:
                return False
                
            # Проверяем валидность блока через консенсус
            if not self.consensus.verify_block(current_block.to_dict(), previous_block.to_dict()):
                return False
                
        return True
        
    def get_balance(self, address: str) -> float:
        """
        Получает баланс адреса.
        
        Args:
            address: Адрес для проверки
            
        Returns:
            float: Баланс адреса
        """
        balance = 0.0
        
        for block in self.chain:
            for transaction in block.transactions:
                if transaction["to"] == address:
                    balance += transaction["amount"]
                if transaction["from"] == address:
                    balance -= transaction["amount"]
                    
        return balance


# Пример использования
if __name__ == "__main__":
    # Создаем экземпляр блокчейна
    grishinium = Blockchain()
    
    # Добавляем несколько транзакций
    grishinium.add_transaction("address1", "address2", 10.0)
    grishinium.add_transaction("address2", "address3", 5.0)
    
    # Майним блок
    miner_address = "miner_address"
    new_block = grishinium.mine_pending_transactions(miner_address)
    
    # Выводим информацию о блоке
    print(f"Добыт новый блок с индексом {new_block.index}")
    print(f"Хэш блока: {new_block.hash}")
    print(f"Транзакции: {len(new_block.transactions)}")
    
    # Проверяем валидность цепи
    is_valid = grishinium.is_chain_valid()
    print(f"Цепь валидна: {is_valid}") 