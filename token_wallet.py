"""
Grishinium Blockchain - Кошелек для работы с токенами
"""

import os
import json
import time
import hashlib
import logging
import getpass
from typing import Dict, List, Any, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from crypto_token import TokenTransaction, TokenTransactionType, format_token_amount, parse_token_amount

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumTokenWallet')

class TokenWalletError(Exception):
    """Базовый класс для ошибок кошелька."""
    pass

class TokenWallet:
    """Класс для работы с кошельком токенов Grishinium."""
    
    DEFAULT_PATH = os.path.expanduser("~/.grishinium/wallets")
    
    def __init__(self, private_key: Optional[ec.EllipticCurvePrivateKey] = None, name: str = "default") -> None:
        """
        Инициализация кошелька с существующим ключом или создание нового.
        
        Args:
            private_key: Закрытый ключ. Если None, будет сгенерирован новый.
            name: Имя кошелька
        """
        self.name = name
        self.wallet_dir = self.DEFAULT_PATH
        os.makedirs(self.wallet_dir, exist_ok=True)
        
        if private_key:
            self.private_key = private_key
        else:
            # Генерируем новую пару ключей
            self.private_key = ec.generate_private_key(ec.SECP256K1())
            
        # Получаем публичный ключ из закрытого
        self.public_key = self.private_key.public_key()
        
        # Генерируем адрес из публичного ключа
        self.address = self._generate_address()
        
        # Кэш для истории транзакций
        self.transaction_history: List[Dict[str, Any]] = []
        
        logger.info(f"Инициализирован кошелек {self.name} с адресом {self.address}")
        
    def _generate_address(self) -> str:
        """
        Генерирует адрес кошелька из публичного ключа.
        
        Returns:
            str: Адрес кошелька
        """
        # Сериализуем публичный ключ
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )
        
        # Создаем хеш публичного ключа
        key_hash = hashlib.sha256(public_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(key_hash)
        hash160 = ripemd160.digest()
        
        # Добавляем префикс "G" для Grishinium (0x47 в hex)
        versioned_hash = b'\x47' + hash160
        
        # Добавляем контрольную сумму
        checksum = hashlib.sha256(hashlib.sha256(versioned_hash).digest()).digest()[:4]
        binary_address = versioned_hash + checksum
        
        # Конвертируем в base58
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        value = int.from_bytes(binary_address, byteorder='big')
        result = ''
        
        while value:
            value, mod = divmod(value, 58)
            result = alphabet[mod] + result
            
        # Добавляем ведущие '1' для каждого ведущего нуля в двоичном представлении
        for byte in binary_address:
            if byte == 0:
                result = '1' + result
            else:
                break
                
        return result
        
    def sign_transaction(self, transaction: TokenTransaction) -> None:
        """
        Подписывает транзакцию закрытым ключом.
        
        Args:
            transaction: Транзакция для подписи
        """
        def sign_data(data: bytes) -> str:
            """
            Подписывает данные закрытым ключом.
            
            Args:
                data: Данные для подписи
                
            Returns:
                str: Подпись в формате base64
            """
            signature = self.private_key.sign(
                data,
                ec.ECDSA(hashes.SHA256())
            )
            
            # Конвертируем подпись в строку
            r, s = decode_dss_signature(signature)
            signature_str = f"{r:064x}{s:064x}"
            
            return signature_str
            
        # Подписываем транзакцию
        transaction.sign(sign_data)
        
    def create_transaction(self, recipient: str, amount: float, fee: float = 0.001) -> TokenTransaction:
        """
        Создает новую транзакцию перевода токенов.
        
        Args:
            recipient: Адрес получателя
            amount: Количество токенов
            fee: Комиссия
            
        Returns:
            TokenTransaction: Созданная транзакция
        """
        # Преобразуем значения в минимальные единицы
        amount_int = int(amount * (10 ** 8))
        fee_int = int(fee * (10 ** 8))
        
        # Создаем транзакцию
        tx = TokenTransaction(
            tx_type=TokenTransactionType.TRANSFER,
            sender=self.address,
            recipient=recipient,
            amount=amount_int,
            fee=fee_int
        )
        
        # Подписываем транзакцию
        self.sign_transaction(tx)
        
        logger.info(f"Создана транзакция {tx.tx_id}: {self.address} -> {recipient}, {format_token_amount(amount_int)}")
        
        return tx
        
    def create_stake_transaction(self, amount: float, fee: float = 0.001) -> TokenTransaction:
        """
        Создает транзакцию стейкинга токенов.
        
        Args:
            amount: Количество токенов
            fee: Комиссия
            
        Returns:
            TokenTransaction: Созданная транзакция
        """
        # Преобразуем значения в минимальные единицы
        amount_int = int(amount * (10 ** 8))
        fee_int = int(fee * (10 ** 8))
        
        # Создаем транзакцию
        tx = TokenTransaction(
            tx_type=TokenTransactionType.STAKE,
            sender=self.address,
            recipient="staking_pool",
            amount=amount_int,
            fee=fee_int
        )
        
        # Подписываем транзакцию
        self.sign_transaction(tx)
        
        logger.info(f"Создана транзакция стейкинга {tx.tx_id}: {self.address} -> стейкинг, {format_token_amount(amount_int)}")
        
        return tx
        
    def create_unstake_transaction(self, amount: float, fee: float = 0.001) -> TokenTransaction:
        """
        Создает транзакцию вывода из стейкинга.
        
        Args:
            amount: Количество токенов
            fee: Комиссия
            
        Returns:
            TokenTransaction: Созданная транзакция
        """
        # Преобразуем значения в минимальные единицы
        amount_int = int(amount * (10 ** 8))
        fee_int = int(fee * (10 ** 8))
        
        # Создаем транзакцию
        tx = TokenTransaction(
            tx_type=TokenTransactionType.UNSTAKE,
            sender=self.address,
            recipient=self.address,
            amount=amount_int,
            fee=fee_int
        )
        
        # Подписываем транзакцию
        self.sign_transaction(tx)
        
        logger.info(f"Создана транзакция вывода из стейкинга {tx.tx_id}: {self.address}, {format_token_amount(amount_int)}")
        
        return tx
        
    def save_to_file(self, password: str) -> None:
        """
        Сохраняет кошелек в файл с защитой паролем.
        
        Args:
            password: Пароль для шифрования
            
        Returns:
            bool: Успешность операции
        """
        # Сериализуем закрытый ключ с защитой паролем
        encrypted_key = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
        )
        
        # Создаем объект кошелька для сохранения
        wallet_data = {
            "name": self.name,
            "address": self.address,
            "encrypted_key": encrypted_key.decode('utf-8')
        }
        
        # Сохраняем в файл
        file_path = os.path.join(self.wallet_dir, f"{self.name}.wallet")
        with open(file_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
            
        logger.info(f"Кошелек сохранен в файл {file_path}")
        
    @classmethod
    def load_from_file(cls, wallet_name: str, password: str) -> 'TokenWallet':
        """
        Загружает кошелек из файла.
        
        Args:
            wallet_name: Имя кошелька
            password: Пароль для расшифровки
            
        Returns:
            TokenWallet: Загруженный кошелек
        """
        file_path = os.path.join(cls.DEFAULT_PATH, f"{wallet_name}.wallet")
        
        if not os.path.exists(file_path):
            raise TokenWalletError(f"Файл кошелька {file_path} не найден")
            
        try:
            with open(file_path, 'r') as f:
                wallet_data = json.load(f)
                
            # Проверяем наличие необходимых полей
            if not all(k in wallet_data for k in ["name", "address", "encrypted_key"]):
                raise TokenWalletError("Недопустимый формат файла кошелька")
                
            # Расшифровываем закрытый ключ
            try:
                private_key = serialization.load_pem_private_key(
                    wallet_data["encrypted_key"].encode('utf-8'),
                    password=password.encode(),
                )
            except (ValueError, TypeError):
                raise TokenWalletError("Неверный пароль или поврежденный ключ")
                
            # Создаем и возвращаем кошелек
            wallet = cls(private_key=private_key, name=wallet_data["name"])
            
            # Проверяем соответствие адреса
            if wallet.address != wallet_data["address"]:
                logger.warning(f"Адрес кошелька {wallet.address} не соответствует сохраненному {wallet_data['address']}")
                
            return wallet
            
        except json.JSONDecodeError:
            raise TokenWalletError("Недопустимый формат JSON в файле кошелька")
        except Exception as e:
            raise TokenWalletError(f"Ошибка при загрузке кошелька: {str(e)}")
            
    @staticmethod
    def verify_signature(data: bytes, signature: str, address: str) -> bool:
        """
        Проверяет подпись данных.
        
        Args:
            data: Подписанные данные
            signature: Подпись в формате hex
            address: Адрес отправителя
            
        Returns:
            bool: Результат проверки
        """
        # В реальной системе здесь должна быть извлечение публичного ключа из подписи
        # и проверка, что адрес соответствует этому ключу
        # Упрощенная версия:
        
        # Преобразуем подпись из hex-строки в числа r и s
        try:
            if len(signature) != 128:
                return False
                
            r = int(signature[:64], 16)
            s = int(signature[64:], 16)
            
            # Воссоздаем DER-подпись
            # В реальной системе здесь должно быть восстановление публичного ключа
            # и проверка, что адрес соответствует этому ключу
            
            # Это заглушка, всегда возвращает True
            return True
            
        except (ValueError, TypeError):
            return False
            
    def update_transaction_history(self, transactions: List[Dict[str, Any]]) -> None:
        """
        Обновляет историю транзакций.
        
        Args:
            transactions: Список транзакций
        """
        self.transaction_history = transactions
        
    def get_formatted_history(self) -> List[Dict[str, Any]]:
        """
        Возвращает отформатированную историю транзакций.
        
        Returns:
            List[Dict[str, Any]]: Отформатированная история
        """
        formatted_history = []
        
        for tx in self.transaction_history:
            # Пропускаем, если это не токеновая транзакция
            if "tx_type" not in tx:
                continue
                
            tx_type = tx["tx_type"]
            amount = tx["amount"]
            fee = tx.get("fee", 0)
            timestamp = tx.get("timestamp", 0)
            is_outgoing = tx.get("sender") == self.address
            
            formatted_tx = {
                "tx_id": tx.get("tx_id", "unknown"),
                "type": tx_type,
                "amount": format_token_amount(amount),
                "fee": format_token_amount(fee),
                "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
                "direction": "outgoing" if is_outgoing else "incoming",
                "counterparty": tx.get("recipient", "unknown") if is_outgoing else tx.get("sender", "unknown"),
                "block": tx.get("block_index", "pending")
            }
            
            formatted_history.append(formatted_tx)
            
        # Сортируем по времени (от новых к старым)
        formatted_history.sort(key=lambda x: time.strptime(x["date"], "%Y-%m-%d %H:%M:%S"), reverse=True)
        
        return formatted_history
        

# Функции для интерактивной работы с кошельком
def create_new_wallet(wallet_name: Optional[str] = None) -> TokenWallet:
    """
    Создает новый кошелек с интерактивными запросами.
    
    Args:
        wallet_name: Имя кошелька (опционально)
        
    Returns:
        TokenWallet: Созданный кошелек
    """
    if wallet_name is None:
        wallet_name = input("Введите имя кошелька (по умолчанию 'default'): ").strip() or "default"
        
    wallet = TokenWallet(name=wallet_name)
    
    save = input("Сохранить кошелек? (y/n): ").lower().strip() == 'y'
    if save:
        while True:
            password = getpass.getpass("Создайте пароль для кошелька: ")
            password_confirm = getpass.getpass("Подтвердите пароль: ")
            
            if password == password_confirm:
                wallet.save_to_file(password)
                break
            else:
                print("Пароли не совпадают, попробуйте еще раз")
                
    print(f"\nВаш адрес кошелька: {wallet.address}")
    print("Сохраните его в надежном месте!")
    
    return wallet
    
def load_wallet(wallet_name: Optional[str] = None) -> Optional[TokenWallet]:
    """
    Загружает существующий кошелек с интерактивными запросами.
    
    Args:
        wallet_name: Имя кошелька (опционально)
        
    Returns:
        TokenWallet: Загруженный кошелек или None в случае ошибки
    """
    if wallet_name is None:
        wallet_name = input("Введите имя кошелька (по умолчанию 'default'): ").strip() or "default"
        
    password = getpass.getpass("Введите пароль: ")
    
    try:
        wallet = TokenWallet.load_from_file(wallet_name, password)
        print(f"Кошелек загружен успешно! Адрес: {wallet.address}")
        return wallet
    except TokenWalletError as e:
        print(f"Ошибка при загрузке кошелька: {str(e)}")
        return None
        
        
# Пример использования
if __name__ == "__main__":
    print("=== Grishinium Token Wallet ===")
    print("1. Создать новый кошелек")
    print("2. Загрузить существующий кошелек")
    
    choice = input("Выберите действие (1/2): ").strip()
    
    if choice == "1":
        wallet = create_new_wallet()
    elif choice == "2":
        wallet = load_wallet()
        if wallet is None:
            print("Не удалось загрузить кошелек. Выход.")
            exit(1)
    else:
        print("Неверный выбор. Выход.")
        exit(1)
        
    # Пример создания транзакции
    recipient = input("Введите адрес получателя для тестовой транзакции (или пропустите): ").strip()
    if recipient:
        try:
            amount = float(input("Введите сумму перевода: ").strip())
            tx = wallet.create_transaction(recipient, amount)
            print(f"Создана транзакция: {tx.tx_id}")
            print(f"Отправитель: {tx.sender}")
            print(f"Получатель: {tx.recipient}")
            print(f"Сумма: {format_token_amount(tx.amount)}")
            print(f"Комиссия: {format_token_amount(tx.fee)}")
        except ValueError:
            print("Неверный формат суммы.")
            
    print("\nРабота с кошельком завершена. Выход.") 