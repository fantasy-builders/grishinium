"""
Grishinium Blockchain - Core Blockchain Implementation
"""

import time
import json
import hashlib
from typing import List, Dict, Any, Optional
import logging
from pos_consensus import ProofOfStake
from crypto_token import TokenLedger, TokenTransaction, TokenTransactionType, format_token_amount, parse_token_amount

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
        self.pending_transactions: List[Dict[str, Any]] = []
        # Добавляем реестр токенов
        self.token_ledger = TokenLedger()
        self.create_genesis_block()
        
    def create_genesis_block(self) -> None:
        """Создает генезис-блок и выполняет первоначальную эмиссию токенов."""
        # Создаем генезис-транзакцию для токенов
        genesis_token_tx = TokenTransaction(
            tx_type=TokenTransactionType.GENESIS,
            sender="system",
            recipient="genesis_wallet",  # В реальной системе здесь должен быть адрес основателя
            amount=parse_token_amount("100000000 GRI"),  # 100 миллионов GRI
            fee=0
        )
        
        # Применяем генезис-транзакцию к реестру токенов
        self.token_ledger.apply_transaction(genesis_token_tx)
        
        # Преобразуем транзакцию в формат для блока
        genesis_tx_dict = genesis_token_tx.to_dict()
        
        # Создаем генезис-блок с токеновой транзакцией
        genesis_block = Block(
            index=0,
            previous_hash="0",
            timestamp=time.time(),
            transactions=[genesis_tx_dict],
            validator="genesis"
        )
        self.chain.append(genesis_block)
        
        logger.info(f"Создан генезис-блок с начальной эмиссией {format_token_amount(genesis_token_tx.amount)}")
        
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
        
        # Проверяем транзакции перед добавлением
        valid_transactions = []
        for tx in transactions:
            # Если это токеновая транзакция
            if "tx_type" in tx:
                token_tx = TokenTransaction.from_dict(tx)
                # Проверяем подпись и валидность транзакции
                if self._validate_token_transaction(token_tx):
                    valid_transactions.append(tx)
                else:
                    logger.warning(f"Невалидная токеновая транзакция {token_tx.tx_id} отклонена")
            else:
                # Обычная транзакция (не токеновая)
                valid_transactions.append(tx)
        
        # Добавляем награду за блок валидатору
        block_reward = self.token_ledger.calculate_block_reward(len(self.chain))
        if block_reward > 0:
            reward_tx = TokenTransaction(
                tx_type=TokenTransactionType.REWARD,
                sender="system",
                recipient=validator,
                amount=block_reward,
                fee=0
            )
            valid_transactions.append(reward_tx.to_dict())
        
        # Создаем новый блок
        new_block = Block(
            index=len(self.chain),
            previous_hash=previous_block.hash,
            timestamp=time.time(),
            transactions=valid_transactions,
            validator=validator
        )
        
        # Проверяем валидность блока через консенсус
        if not self.consensus.verify_block(new_block.to_dict(), previous_block.to_dict()):
            logger.warning("Невалидный блок отклонен")
            return False
        
        # Добавляем блок в цепь
        self.chain.append(new_block)
        
        # Применяем все токеновые транзакции к реестру токенов
        for tx in valid_transactions:
            if "tx_type" in tx:
                token_tx = TokenTransaction.from_dict(tx)
                self.token_ledger.apply_transaction(token_tx)
        
        # Очищаем подтвержденные транзакции из списка ожидающих
        self._remove_confirmed_transactions(valid_transactions)
        
        logger.info(f"Добавлен новый блок #{new_block.index} с хешем {new_block.hash}")
        if block_reward > 0:
            logger.info(f"Валидатор {validator} получил награду {format_token_amount(block_reward)}")
        
        return True
    
    def _validate_token_transaction(self, tx: TokenTransaction) -> bool:
        """
        Проверяет валидность токеновой транзакции.
        
        Args:
            tx: Транзакция для проверки
            
        Returns:
            bool: Валидность транзакции
        """
        # Для системных транзакций и наград проверка особая
        if tx.tx_type in [TokenTransactionType.GENESIS, TokenTransactionType.REWARD]:
            return True
        
        # Проверяем, достаточно ли средств у отправителя
        if tx.tx_type == TokenTransactionType.TRANSFER:
            balance = self.token_ledger.get_balance(tx.sender)
            if balance < tx.amount + tx.fee:
                logger.warning(f"Недостаточно средств у {tx.sender} для транзакции {tx.tx_id}")
                return False
        elif tx.tx_type == TokenTransactionType.STAKE:
            balance = self.token_ledger.get_balance(tx.sender)
            if balance < tx.amount + tx.fee:
                logger.warning(f"Недостаточно средств у {tx.sender} для стейкинга {tx.tx_id}")
                return False
        elif tx.tx_type == TokenTransactionType.UNSTAKE:
            staked = self.token_ledger.get_staked_amount(tx.sender)
            balance = self.token_ledger.get_balance(tx.sender)
            if staked < tx.amount or balance < tx.fee:
                logger.warning(f"Недостаточно средств для анстейкинга {tx.tx_id}")
                return False
        
        # Здесь должна быть проверка подписи (в реальной системе)
        # return tx.verify_signature(verify_function)
        
        return True
    
    def _remove_confirmed_transactions(self, confirmed_txs: List[Dict[str, Any]]) -> None:
        """
        Удаляет подтвержденные транзакции из списка ожидающих.
        
        Args:
            confirmed_txs: Список подтвержденных транзакций
        """
        # Создаем множество ID подтвержденных транзакций для быстрого поиска
        confirmed_ids = set()
        for tx in confirmed_txs:
            if "tx_id" in tx:
                confirmed_ids.add(tx["tx_id"])
        
        # Фильтруем список ожидающих транзакций
        self.pending_transactions = [
            tx for tx in self.pending_transactions 
            if not ("tx_id" in tx and tx["tx_id"] in confirmed_ids)
        ]
        
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
        return self.token_ledger.get_balance(address)
    
    def get_staked_amount(self, address: str) -> float:
        """
        Получает количество токенов в стейкинге.
        
        Args:
            address: Адрес для проверки
            
        Returns:
            float: Количество токенов в стейкинге
        """
        return self.token_ledger.get_staked_amount(address)
    
    def add_transaction(self, sender: str, recipient: str, amount: float, fee: float = 0.001) -> bool:
        """
        Добавляет новую транзакцию в список ожидающих.
        
        Args:
            sender: Адрес отправителя
            recipient: Адрес получателя
            amount: Количество токенов
            fee: Комиссия за транзакцию
            
        Returns:
            bool: Успешность операции
        """
        # Преобразуем значения в минимальные единицы
        amount_int = int(amount * (10 ** 8))
        fee_int = int(fee * (10 ** 8))
        
        # Создаем токеновую транзакцию
        tx = TokenTransaction(
            tx_type=TokenTransactionType.TRANSFER,
            sender=sender,
            recipient=recipient,
            amount=amount_int,
            fee=fee_int
        )
        
        # Проверяем валидность
        if not self._validate_token_transaction(tx):
            return False
        
        # Добавляем в список ожидающих
        self.pending_transactions.append(tx.to_dict())
        
        logger.info(f"Добавлена новая транзакция {tx.tx_id}: {sender} -> {recipient}, {format_token_amount(amount_int)}")
        
        return True
    
    def add_stake_transaction(self, sender: str, amount: float, fee: float = 0.001) -> bool:
        """
        Добавляет транзакцию стейкинга в список ожидающих.
        
        Args:
            sender: Адрес стейкера
            amount: Количество токенов для стейкинга
            fee: Комиссия за транзакцию
            
        Returns:
            bool: Успешность операции
        """
        # Преобразуем значения в минимальные единицы
        amount_int = int(amount * (10 ** 8))
        fee_int = int(fee * (10 ** 8))
        
        # Создаем токеновую транзакцию стейкинга
        tx = TokenTransaction(
            tx_type=TokenTransactionType.STAKE,
            sender=sender,
            recipient="staking_pool",  # Специальный адрес для стейкинга
            amount=amount_int,
            fee=fee_int
        )
        
        # Проверяем валидность
        if not self._validate_token_transaction(tx):
            return False
        
        # Добавляем в список ожидающих
        self.pending_transactions.append(tx.to_dict())
        
        logger.info(f"Добавлена новая транзакция стейкинга {tx.tx_id}: {sender} -> стейкинг, {format_token_amount(amount_int)}")
        
        return True
    
    def add_unstake_transaction(self, sender: str, amount: float, fee: float = 0.001) -> bool:
        """
        Добавляет транзакцию вывода из стейкинга в список ожидающих.
        
        Args:
            sender: Адрес стейкера
            amount: Количество токенов для вывода из стейкинга
            fee: Комиссия за транзакцию
            
        Returns:
            bool: Успешность операции
        """
        # Преобразуем значения в минимальные единицы
        amount_int = int(amount * (10 ** 8))
        fee_int = int(fee * (10 ** 8))
        
        # Создаем токеновую транзакцию вывода из стейкинга
        tx = TokenTransaction(
            tx_type=TokenTransactionType.UNSTAKE,
            sender=sender,
            recipient=sender,  # Токены возвращаются отправителю
            amount=amount_int,
            fee=fee_int
        )
        
        # Проверяем валидность
        if not self._validate_token_transaction(tx):
            return False
        
        # Добавляем в список ожидающих
        self.pending_transactions.append(tx.to_dict())
        
        logger.info(f"Добавлена новая транзакция вывода из стейкинга {tx.tx_id}: {sender}, {format_token_amount(amount_int)}")
        
        return True

    def get_transaction_history(self, address: str) -> List[Dict[str, Any]]:
        """
        Получает историю транзакций для указанного адреса.
        
        Args:
            address: Адрес для проверки
            
        Returns:
            List[Dict[str, Any]]: Список транзакций
        """
        transactions = []
        
        # Проходим по всем блокам в цепи
        for block in self.chain:
            for tx in block.transactions:
                # Проверяем, является ли это токеновой транзакцией
                if "tx_type" in tx and ("sender" in tx and tx["sender"] == address or "recipient" in tx and tx["recipient"] == address):
                    # Добавляем информацию о блоке к транзакции
                    tx_with_block = tx.copy()
                    tx_with_block["block_index"] = block.index
                    tx_with_block["block_hash"] = block.hash
                    tx_with_block["block_timestamp"] = block.timestamp
                    transactions.append(tx_with_block)
        
        # Сортируем по временной метке (от новых к старым)
        transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return transactions


# Пример использования
if __name__ == "__main__":
    # Создаем экземпляр блокчейна
    grishinium = Blockchain()
    
    # Адрес для тестирования
    test_address = "test_wallet"
    
    # Проверяем баланс генезис-кошелька
    genesis_balance = grishinium.get_balance("genesis_wallet")
    print(f"Баланс генезис-кошелька: {format_token_amount(genesis_balance)}")
    
    # Добавляем тестовую транзакцию
    grishinium.add_transaction("genesis_wallet", test_address, 1000)
    
    # Добавляем блок с тестовой транзакцией
    validator_address = "validator_address"
    success = grishinium.add_block(grishinium.pending_transactions, validator_address)
    
    if success:
        # Проверяем балансы
        genesis_balance = grishinium.get_balance("genesis_wallet")
        test_balance = grishinium.get_balance(test_address)
        validator_balance = grishinium.get_balance(validator_address)
        
        print(f"Баланс генезис-кошелька: {format_token_amount(genesis_balance)}")
        print(f"Баланс тестового кошелька: {format_token_amount(test_balance)}")
        print(f"Баланс валидатора: {format_token_amount(validator_balance)}")
    else:
        print("Не удалось добавить блок") 