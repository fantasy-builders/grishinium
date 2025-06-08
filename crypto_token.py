"""
Grishinium Blockchain - Токены и криптовалюта
"""

import time
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumToken')

# Константы для токена GRI
TOKEN_NAME = "Grishinium"
TOKEN_SYMBOL = "GRI"
TOKEN_DECIMALS = 8  # Количество знаков после запятой (как в Bitcoin)
TOKEN_INITIAL_SUPPLY = 100_000_000 * (10 ** TOKEN_DECIMALS)  # 100 миллионов GRI
TOKEN_MAX_SUPPLY = 1_000_000_000 * (10 ** TOKEN_DECIMALS)  # 1 миллиард GRI
BLOCK_REWARD_START = 50 * (10 ** TOKEN_DECIMALS)  # Начальная награда за блок
BLOCK_REWARD_HALVING_BLOCKS = 210000  # Количество блоков до уменьшения награды вдвое
TX_MIN_FEE = 0.0001 * (10 ** TOKEN_DECIMALS)  # Минимальная комиссия за транзакцию

class TokenTransactionType(Enum):
    """Типы токеновых транзакций."""
    TRANSFER = "transfer"  # Перевод между адресами
    STAKE = "stake"  # Стейкинг токенов
    UNSTAKE = "unstake"  # Вывод из стейкинга
    REWARD = "reward"  # Награда валидатору
    GENESIS = "genesis"  # Начальная эмиссия
    FEE = "fee"  # Комиссия за транзакцию

class TokenTransaction:
    """Класс для представления токеновой транзакции."""
    
    def __init__(self, 
                 tx_type: TokenTransactionType,
                 sender: str,
                 recipient: str,
                 amount: int,
                 fee: int,
                 timestamp: Optional[float] = None,
                 signature: Optional[str] = None,
                 tx_id: Optional[str] = None) -> None:
        """
        Создание транзакции с токенами.
        
        Args:
            tx_type: Тип транзакции
            sender: Адрес отправителя (или "system" для системных транзакций)
            recipient: Адрес получателя
            amount: Количество токенов (в минимальных единицах)
            fee: Комиссия за транзакцию (в минимальных единицах)
            timestamp: Временная метка создания
            signature: Подпись транзакции (опционально)
            tx_id: Идентификатор транзакции (генерируется автоматически, если не указан)
        """
        self.tx_type = tx_type
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.timestamp = timestamp or time.time()
        self.signature = signature
        self.tx_id = tx_id or self._generate_tx_id()
        
    def _generate_tx_id(self) -> str:
        """
        Генерирует уникальный идентификатор транзакции.
        
        Returns:
            str: Идентификатор транзакции
        """
        # Создаем строку для хеширования
        data_str = (
            f"{self.tx_type.value}:{self.sender}:{self.recipient}:"
            f"{self.amount}:{self.fee}:{self.timestamp}"
        )
        # Генерируем хеш
        tx_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return tx_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует транзакцию в словарь для сериализации.
        
        Returns:
            Dict[str, Any]: Словарь с данными транзакции
        """
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, tx_dict: Dict[str, Any]) -> 'TokenTransaction':
        """
        Создает транзакцию из словаря.
        
        Args:
            tx_dict: Словарь с данными транзакции
            
        Returns:
            TokenTransaction: Экземпляр транзакции
        """
        return cls(
            tx_type=TokenTransactionType(tx_dict["tx_type"]),
            sender=tx_dict["sender"],
            recipient=tx_dict["recipient"],
            amount=tx_dict["amount"],
            fee=tx_dict["fee"],
            timestamp=tx_dict["timestamp"],
            signature=tx_dict["signature"],
            tx_id=tx_dict["tx_id"]
        )
    
    def sign(self, private_key_func) -> None:
        """
        Подписывает транзакцию закрытым ключом.
        
        Args:
            private_key_func: Функция, принимающая данные и возвращающая подпись
        """
        # Подготавливаем данные для подписи (без TX_ID и существующей подписи)
        data_to_sign = {
            "tx_type": self.tx_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp
        }
        
        # Сериализуем и подписываем
        serialized_data = json.dumps(data_to_sign, sort_keys=True).encode()
        self.signature = private_key_func(serialized_data)
    
    def verify_signature(self, verify_func) -> bool:
        """
        Проверяет подпись транзакции.
        
        Args:
            verify_func: Функция проверки подписи
            
        Returns:
            bool: Результат проверки
        """
        if self.tx_type == TokenTransactionType.GENESIS or self.sender == "system":
            # Системные транзакции не требуют подписи
            return True
            
        if not self.signature:
            logger.warning(f"Транзакция {self.tx_id} не имеет подписи")
            return False
            
        # Подготавливаем данные для проверки (должны совпадать с данными для подписи)
        data_to_verify = {
            "tx_type": self.tx_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp
        }
        
        # Сериализуем и проверяем
        serialized_data = json.dumps(data_to_verify, sort_keys=True).encode()
        return verify_func(serialized_data, self.signature, self.sender)


class TokenLedger:
    """Класс для отслеживания балансов и состояния токенов."""
    
    def __init__(self):
        """Инициализация реестра токенов."""
        self.balances: Dict[str, int] = {}  # адрес -> баланс
        self.staked_amounts: Dict[str, int] = {}  # адрес -> количество в стейкинге
        self.transaction_history: Dict[str, List[str]] = {}  # адрес -> список tx_id
        self.total_supply = 0  # Текущее количество токенов в обращении
        
    def apply_transaction(self, transaction: TokenTransaction) -> bool:
        """
        Применяет транзакцию к состоянию токенов.
        
        Args:
            transaction: Транзакция для применения
            
        Returns:
            bool: Успешность операции
        """
        tx_type = transaction.tx_type
        sender = transaction.sender
        recipient = transaction.recipient
        amount = transaction.amount
        fee = transaction.fee
        
        # Проверка и обновление балансов в зависимости от типа транзакции
        if tx_type == TokenTransactionType.GENESIS:
            # Генезис-транзакция создает новые токены
            self.balances[recipient] = self.balances.get(recipient, 0) + amount
            self.total_supply += amount
            
        elif tx_type == TokenTransactionType.TRANSFER:
            # Обычный перевод между адресами
            sender_balance = self.balances.get(sender, 0)
            
            # Проверка достаточности средств
            if sender_balance < amount + fee:
                logger.warning(f"Недостаточно средств у {sender} для транзакции {transaction.tx_id}")
                return False
                
            # Обновляем балансы
            self.balances[sender] = sender_balance - amount - fee
            self.balances[recipient] = self.balances.get(recipient, 0) + amount
            
            # Комиссия идет майнеру/валидатору (будет обработано отдельно)
            
        elif tx_type == TokenTransactionType.STAKE:
            # Стейкинг токенов
            sender_balance = self.balances.get(sender, 0)
            
            # Проверка достаточности средств
            if sender_balance < amount + fee:
                logger.warning(f"Недостаточно средств у {sender} для стейкинга {transaction.tx_id}")
                return False
                
            # Обновляем балансы и стейк
            self.balances[sender] = sender_balance - amount - fee
            self.staked_amounts[sender] = self.staked_amounts.get(sender, 0) + amount
            
        elif tx_type == TokenTransactionType.UNSTAKE:
            # Вывод из стейкинга
            staked_amount = self.staked_amounts.get(sender, 0)
            sender_balance = self.balances.get(sender, 0)
            
            # Проверка достаточности средств для комиссии и наличия стейка
            if sender_balance < fee or staked_amount < amount:
                logger.warning(f"Недостаточно средств для анстейкинга {transaction.tx_id}")
                return False
                
            # Обновляем балансы и стейк
            self.balances[sender] = sender_balance - fee + amount
            self.staked_amounts[sender] = staked_amount - amount
            
        elif tx_type == TokenTransactionType.REWARD:
            # Награда валидатору
            self.balances[recipient] = self.balances.get(recipient, 0) + amount
            self.total_supply += amount
            
        elif tx_type == TokenTransactionType.FEE:
            # Распределение комиссии
            self.balances[recipient] = self.balances.get(recipient, 0) + amount
            
        # Обновляем историю транзакций
        if sender != "system":
            if sender not in self.transaction_history:
                self.transaction_history[sender] = []
            self.transaction_history[sender].append(transaction.tx_id)
            
        if recipient != "system":
            if recipient not in self.transaction_history:
                self.transaction_history[recipient] = []
            self.transaction_history[recipient].append(transaction.tx_id)
            
        return True
    
    def get_balance(self, address: str) -> int:
        """
        Получает баланс адреса.
        
        Args:
            address: Адрес пользователя
            
        Returns:
            int: Баланс в минимальных единицах
        """
        return self.balances.get(address, 0)
    
    def get_staked_amount(self, address: str) -> int:
        """
        Получает количество токенов в стейкинге.
        
        Args:
            address: Адрес пользователя
            
        Returns:
            int: Количество токенов в стейкинге
        """
        return self.staked_amounts.get(address, 0)
    
    def calculate_block_reward(self, block_height: int) -> int:
        """
        Рассчитывает награду за блок на основе текущей высоты.
        
        Args:
            block_height: Высота блока
            
        Returns:
            int: Награда в минимальных единицах
        """
        # Вычисляем, сколько раз произошло уменьшение награды (halving)
        halvings = block_height // BLOCK_REWARD_HALVING_BLOCKS
        
        # После 64 уменьшений награда становится 0
        if halvings >= 64:
            return 0
            
        # Уменьшаем начальную награду в 2^halvings раз
        reward = BLOCK_REWARD_START // (2 ** halvings)
        
        # Проверяем, не превышен ли максимальный объем поставок
        if self.total_supply + reward > TOKEN_MAX_SUPPLY:
            remaining = TOKEN_MAX_SUPPLY - self.total_supply
            return max(0, remaining)
            
        return reward


# Функции для форматирования
def format_token_amount(amount: int) -> str:
    """
    Форматирует количество токенов для отображения.
    
    Args:
        amount: Количество в минимальных единицах
        
    Returns:
        str: Отформатированная строка с символом токена
    """
    whole_part = amount // (10 ** TOKEN_DECIMALS)
    decimal_part = amount % (10 ** TOKEN_DECIMALS)
    
    # Форматируем десятичную часть с ведущими нулями
    decimal_str = str(decimal_part).zfill(TOKEN_DECIMALS)
    
    # Убираем лишние нули в конце
    decimal_str = decimal_str.rstrip('0')
    
    # Если десятичная часть пуста, возвращаем только целую часть
    if not decimal_str:
        return f"{whole_part} {TOKEN_SYMBOL}"
        
    return f"{whole_part}.{decimal_str} {TOKEN_SYMBOL}"


def parse_token_amount(amount_str: str) -> int:
    """
    Преобразует строку с количеством токенов в минимальные единицы.
    
    Args:
        amount_str: Строка вида "10.5 GRI" или "10.5"
        
    Returns:
        int: Количество в минимальных единицах
    """
    # Удаляем символ токена и лишние пробелы
    clean_str = amount_str.replace(TOKEN_SYMBOL, "").strip()
    
    # Разделяем на целую и дробную части
    if "." in clean_str:
        whole_part, decimal_part = clean_str.split(".")
        
        # Дополняем или обрезаем дробную часть до нужной длины
        decimal_part = decimal_part.ljust(TOKEN_DECIMALS, '0')[:TOKEN_DECIMALS]
        
        # Преобразуем в минимальные единицы
        return int(whole_part) * (10 ** TOKEN_DECIMALS) + int(decimal_part) * (10 ** (TOKEN_DECIMALS - len(decimal_part)))
    else:
        # Только целая часть
        return int(clean_str) * (10 ** TOKEN_DECIMALS)


# Пример использования
if __name__ == "__main__":
    # Создаем реестр
    ledger = TokenLedger()
    
    # Генезис-транзакция
    genesis_tx = TokenTransaction(
        tx_type=TokenTransactionType.GENESIS,
        sender="system",
        recipient="genesis_wallet",
        amount=TOKEN_INITIAL_SUPPLY,
        fee=0
    )
    
    # Применяем генезис
    ledger.apply_transaction(genesis_tx)
    
    # Создаем тестовую транзакцию
    test_tx = TokenTransaction(
        tx_type=TokenTransactionType.TRANSFER,
        sender="genesis_wallet",
        recipient="user_wallet",
        amount=parse_token_amount("1000 GRI"),
        fee=parse_token_amount("0.1 GRI")
    )
    
    # Применяем транзакцию
    ledger.apply_transaction(test_tx)
    
    # Проверяем балансы
    genesis_balance = ledger.get_balance("genesis_wallet")
    user_balance = ledger.get_balance("user_wallet")
    
    print(f"Баланс генезис-кошелька: {format_token_amount(genesis_balance)}")
    print(f"Баланс пользовательского кошелька: {format_token_amount(user_balance)}")
    print(f"Общая эмиссия: {format_token_amount(ledger.total_supply)}") 