#!/usr/bin/env python3
"""
Grishinium Wallet Module - Модуль для работы с кошельками Grishinium блокчейна
"""

import os
import json
import time
import random
import hashlib
import binascii
import getpass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
import base64

# Импорт стандартных библиотек для криптографии
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Список слов для BIP39 (упрощенная версия)
# В реальном приложении используйте полный словарь BIP39
BIP39_WORDLIST = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse",
    "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act",
    "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit",
    "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
    "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert",
    "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter",
    "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger",
    "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
    "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic",
    "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest",
    "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset",
    "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction",
    "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid", "awake",
    "aware", "away", "awesome", "awful", "awkward", "axis"
]

class WalletError(Exception):
    """Базовый класс для ошибок кошелька."""
    pass

class InvalidSeedError(WalletError):
    """Ошибка при использовании некорректной seed-фразы."""
    pass

class InvalidPasswordError(WalletError):
    """Ошибка при использовании некорректного пароля."""
    pass

class WalletExistsError(WalletError):
    """Ошибка при попытке создать уже существующий кошелек."""
    pass

class WalletNotFoundError(WalletError):
    """Ошибка при попытке открыть несуществующий кошелек."""
    pass

class GrishiniumWallet:
    """Класс для управления кошельком Grishinium."""
    
    DEFAULT_PATH = os.path.expanduser("~/.grishinium/wallets")
    
    def __init__(self, seed_phrase: Optional[str] = None, password: Optional[str] = None, wallet_name: Optional[str] = None):
        """
        Инициализация кошелька с существующей seed-фразой или создание новой.
        
        Args:
            seed_phrase: Seed-фраза (12 слов) для восстановления кошелька. Если None, будет сгенерирована новая.
            password: Пароль для защиты кошелька.
            wallet_name: Имя кошелька для сохранения.
        """
        self.wallet_path = self.DEFAULT_PATH
        self.wallet_name = wallet_name or "default_wallet"
        self.wallet_file = os.path.join(self.wallet_path, f"{self.wallet_name}.wallet")
        
        # Создаем директорию для кошельков, если она не существует
        os.makedirs(self.wallet_path, exist_ok=True)
        
        # Если мы восстанавливаем кошелек из seed-фразы
        if seed_phrase:
            self.seed_phrase = seed_phrase
            self.seed_bytes = self._seed_phrase_to_bytes(seed_phrase)
        else:
            # Генерируем новую seed-фразу
            self.seed_bytes = self._generate_seed()
            self.seed_phrase = self._bytes_to_seed_phrase(self.seed_bytes)
        
        # Генерируем пары ключей из seed
        self.private_key, self.public_key = self._derive_keys_from_seed(self.seed_bytes)
        
        # Получаем адрес из публичного ключа
        self.address = self._generate_address(self.public_key)
        
        # Если был предоставлен пароль, сохраняем кошелек
        if password:
            self.save_wallet(password)
    
    def _generate_seed(self, entropy_bytes: int = 16) -> bytes:
        """
        Генерирует случайный seed для BIP39.
        
        Args:
            entropy_bytes: Количество байт энтропии (16 = 128 бит).
        
        Returns:
            bytes: Случайные байты для seed.
        """
        return os.urandom(entropy_bytes)
    
    def _bytes_to_seed_phrase(self, seed_bytes: bytes) -> str:
        """
        Конвертирует байты seed в seed-фразу (12 слов).
        
        Args:
            seed_bytes: Байты seed.
        
        Returns:
            str: Seed-фраза из 12 слов.
        """
        # Преобразуем байты в битовую строку
        bits = bin(int.from_bytes(seed_bytes, byteorder='big'))[2:].zfill(len(seed_bytes) * 8)
        
        # Разделяем на группы по 11 бит
        chunks = [bits[i:i+11] for i in range(0, len(bits), 11)]
        
        # Каждая группа соответствует индексу слова в списке BIP39
        words = []
        for chunk in chunks:
            index = int(chunk, 2)
            # Проверяем, что индекс в пределах длины словаря
            if index < len(BIP39_WORDLIST):
                words.append(BIP39_WORDLIST[index])
            else:
                # Если индекс выходит за пределы, берем остаток от деления
                words.append(BIP39_WORDLIST[index % len(BIP39_WORDLIST)])
        
        # Возвращаем 12 слов (или меньше, если seed был маленький)
        return " ".join(words[:12])
    
    def _seed_phrase_to_bytes(self, seed_phrase: str) -> bytes:
        """
        Конвертирует seed-фразу обратно в байты.
        
        Args:
            seed_phrase: Seed-фраза (12 слов).
        
        Returns:
            bytes: Байты seed.
        
        Raises:
            InvalidSeedError: Если seed-фраза некорректна.
        """
        words = seed_phrase.strip().lower().split()
        
        if len(words) != 12:
            raise InvalidSeedError("Seed-фраза должна содержать 12 слов")
        
        # Проверяем, что все слова есть в словаре
        for word in words:
            if word not in BIP39_WORDLIST:
                raise InvalidSeedError(f"Слово '{word}' отсутствует в словаре BIP39")
        
        # Преобразуем слова в индексы
        indices = [BIP39_WORDLIST.index(word) for word in words]
        
        # Преобразуем индексы в биты
        bits = ""
        for index in indices:
            bits += bin(index)[2:].zfill(11)
        
        # Преобразуем биты в байты
        bytes_length = len(bits) // 8
        seed_bytes = int(bits[:bytes_length * 8], 2).to_bytes(bytes_length, byteorder='big')
        
        return seed_bytes
    
    def _derive_keys_from_seed(self, seed_bytes: bytes) -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """
        Выводит пару ключей из seed.
        
        Args:
            seed_bytes: Байты seed.
        
        Returns:
            Tuple[EllipticCurvePrivateKey, EllipticCurvePublicKey]: Пара ключей.
        """
        # Создаем детерминированный ключ из seed
        digest = hashlib.sha256(seed_bytes).digest()
        
        # Создаем приватный ключ из хеша
        private_key = ec.derive_private_key(
            int.from_bytes(digest, byteorder='big'),
            ec.SECP256K1(),
            default_backend()
        )
        
        # Получаем соответствующий публичный ключ
        public_key = private_key.public_key()
        
        return private_key, public_key
    
    def _generate_address(self, public_key: ec.EllipticCurvePublicKey) -> str:
        """
        Генерирует адрес Grishinium из публичного ключа.
        
        Args:
            public_key: Публичный ключ.
        
        Returns:
            str: Адрес Grishinium.
        """
        # Получаем публичный ключ в формате байтов
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )
        
        # Получаем SHA-256 хеш от публичного ключа
        h = hashlib.sha256(public_bytes).digest()
        
        # Берем первые 20 байт (160 бит) для создания адреса
        ripemd_hash = hashlib.new('ripemd160')
        ripemd_hash.update(h)
        ripemd_digest = ripemd_hash.digest()
        
        # Префикс для адресов Grishinium
        prefix = "GRS_"
        
        # Создаем адрес в формате Base58Check
        address = prefix + self._base58_encode(ripemd_digest)
        
        return address
    
    def _base58_encode(self, data: bytes) -> str:
        """
        Кодирует байты в Base58.
        
        Args:
            data: Байты для кодирования.
        
        Returns:
            str: Строка в формате Base58.
        """
        # Алфавит Base58
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        
        # Преобразуем в большое целое число
        n = int.from_bytes(data, byteorder='big')
        
        # Конвертируем в Base58
        result = ""
        while n > 0:
            n, remainder = divmod(n, 58)
            result = alphabet[remainder] + result
        
        # Добавляем ведущие нули
        for b in data:
            if b == 0:
                result = alphabet[0] + result
            else:
                break
        
        return result
    
    def get_address(self) -> str:
        """
        Возвращает адрес кошелька.
        
        Returns:
            str: Адрес Grishinium.
        """
        return self.address
    
    def get_seed_phrase(self) -> str:
        """
        Возвращает seed-фразу кошелька.
        
        Returns:
            str: Seed-фраза из 12 слов.
        """
        return self.seed_phrase
    
    def sign_transaction(self, transaction_data: Dict) -> str:
        """
        Подписывает транзакцию приватным ключом.
        
        Args:
            transaction_data: Данные транзакции для подписи.
        
        Returns:
            str: Подпись транзакции в виде строки.
        """
        # Создаем строковое представление транзакции
        tx_string = json.dumps(transaction_data, sort_keys=True)
        
        # Хешируем транзакцию
        tx_hash = hashlib.sha256(tx_string.encode()).digest()
        
        # Подписываем хеш приватным ключом
        signature = self.private_key.sign(
            tx_hash,
            ec.ECDSA(hashes.SHA256())
        )
        
        # Возвращаем подпись в виде строки (Base64)
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_transaction(self, transaction_data: Dict, signature: str) -> bool:
        """
        Проверяет подпись транзакции.
        
        Args:
            transaction_data: Данные транзакции для проверки.
            signature: Подпись транзакции в виде строки.
        
        Returns:
            bool: True, если подпись верна.
        """
        # Создаем строковое представление транзакции
        tx_string = json.dumps(transaction_data, sort_keys=True)
        
        # Хешируем транзакцию
        tx_hash = hashlib.sha256(tx_string.encode()).digest()
        
        # Декодируем подпись из Base64
        signature_bytes = base64.b64decode(signature)
        
        try:
            # Проверяем подпись публичным ключом
            self.public_key.verify(
                signature_bytes,
                tx_hash,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except:
            return False
    
    def save_wallet(self, password: str) -> None:
        """
        Сохраняет кошелек в защищенном виде.
        
        Args:
            password: Пароль для защиты кошелька.
            
        Raises:
            WalletExistsError: Если кошелек с таким именем уже существует.
        """
        # Проверяем, существует ли уже такой кошелек
        if os.path.exists(self.wallet_file) and not hasattr(self, 'overwrite'):
            raise WalletExistsError(f"Кошелек с именем {self.wallet_name} уже существует")
        
        # Экспортируем приватный ключ в формат PEM
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Создаем соль для PBKDF2
        salt = os.urandom(16)
        
        # Создаем ключ для шифрования из пароля
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        # Создаем вектор инициализации
        iv = os.urandom(16)
        
        # Шифруем приватный ключ
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(private_pem) + padder.finalize()
        encrypted_key = encryptor.update(padded_data) + encryptor.finalize()
        
        # Создаем структуру для сохранения кошелька
        wallet_data = {
            "address": self.address,
            "encrypted_key": base64.b64encode(encrypted_key).decode('utf-8'),
            "salt": base64.b64encode(salt).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "public_key": base64.b64encode(
                self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            ).decode('utf-8'),
            "created_at": time.time()
        }
        
        # Сохраняем кошелек в файл
        with open(self.wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=4)
    
    @classmethod
    def load_wallet(cls, seed_phrase: str, password: str, wallet_name: Optional[str] = None) -> 'GrishiniumWallet':
        """
        Загружает кошелек из seed-фразы и пароля.
        
        Args:
            seed_phrase: Seed-фраза (12 слов).
            password: Пароль для доступа к кошельку.
            wallet_name: Имя кошелька для загрузки. По умолчанию "default_wallet".
            
        Returns:
            GrishiniumWallet: Экземпляр кошелька.
            
        Raises:
            WalletNotFoundError: Если кошелек не найден.
            InvalidPasswordError: Если пароль неверный.
        """
        wallet_name = wallet_name or "default_wallet"
        wallet_path = cls.DEFAULT_PATH
        wallet_file = os.path.join(wallet_path, f"{wallet_name}.wallet")
        
        # Проверяем, существует ли такой кошелек
        if not os.path.exists(wallet_file):
            # Если кошелька нет, создаем новый из seed-фразы
            wallet = cls(seed_phrase=seed_phrase, password=password, wallet_name=wallet_name)
            wallet.overwrite = True
            return wallet
        
        # Загружаем данные кошелька
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        # Создаем кошелек из seed-фразы
        wallet = cls(seed_phrase=seed_phrase, wallet_name=wallet_name)
        
        # Проверяем, совпадает ли адрес
        if wallet.address != wallet_data["address"]:
            raise InvalidSeedError("Недействительная seed-фраза для этого кошелька")
        
        # Пытаемся расшифровать приватный ключ для проверки пароля
        try:
            # Получаем соль и IV
            salt = base64.b64decode(wallet_data["salt"])
            iv = base64.b64decode(wallet_data["iv"])
            encrypted_key = base64.b64decode(wallet_data["encrypted_key"])
            
            # Создаем ключ из пароля
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode())
            
            # Расшифровываем приватный ключ
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_key) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            decrypted_key = unpadder.update(decrypted_padded) + unpadder.finalize()
            
            # Проверяем, что ключ можно загрузить
            serialization.load_pem_private_key(
                decrypted_key,
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            raise InvalidPasswordError("Неверный пароль для этого кошелька") from e
        
        # Если всё прошло успешно, возвращаем кошелек
        return wallet
    
    @classmethod
    def create_wallet(cls, password: str, wallet_name: Optional[str] = None) -> 'GrishiniumWallet':
        """
        Создает новый кошелек с новой seed-фразой.
        
        Args:
            password: Пароль для защиты кошелька.
            wallet_name: Имя кошелька. По умолчанию "default_wallet".
            
        Returns:
            GrishiniumWallet: Экземпляр кошелька.
            
        Raises:
            WalletExistsError: Если кошелек с таким именем уже существует.
        """
        return cls(password=password, wallet_name=wallet_name)
    
    def create_transaction(self, recipient: str, amount: float, fee: float = 0.001) -> Dict:
        """
        Создает транзакцию для отправки монет.
        
        Args:
            recipient: Адрес получателя.
            amount: Сумма для отправки.
            fee: Комиссия за транзакцию.
            
        Returns:
            Dict: Данные транзакции.
        """
        # Создаем структуру транзакции
        transaction = {
            "sender": self.address,
            "recipient": recipient,
            "amount": amount,
            "fee": fee,
            "timestamp": time.time(),
            "nonce": random.randint(0, 1000000000)  # Добавляем nonce для уникальности
        }
        
        # Подписываем транзакцию
        signature = self.sign_transaction(transaction)
        
        # Добавляем подпись и публичный ключ
        transaction["signature"] = signature
        transaction["public_key"] = base64.b64encode(
            self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        ).decode('utf-8')
        
        return transaction
    
    def create_stake_transaction(self, amount: float, fee: float = 0.001) -> Dict:
        """
        Создает транзакцию для стейкинга монет.
        
        Args:
            amount: Количество монет для стейкинга
            fee: Комиссия за транзакцию
            
        Returns:
            Dict: Транзакция стейкинга
        """
        if amount <= 0:
            raise WalletError("Amount must be positive")
            
        if amount < 100:  # Минимальный стейк
            raise WalletError("Stake amount must be at least 100 coins")
            
        # Создаем базовую транзакцию
        transaction = {
            "from": self.get_address(),
            "to": "staking_pool",
            "amount": amount,
            "fee": fee,
            "timestamp": time.time(),
            "type": "stake"
        }
        
        # Подписываем транзакцию
        transaction["signature"] = self.sign_transaction(transaction)
        
        return transaction
        
    def create_unstake_transaction(self, fee: float = 0.001) -> Dict:
        """
        Создает транзакцию для вывода монет из стейкинга.
        
        Args:
            fee: Комиссия за транзакцию
            
        Returns:
            Dict: Транзакция анстейкинга
        """
        # Создаем базовую транзакцию
        transaction = {
            "from": "staking_pool",
            "to": self.get_address(),
            "amount": 0,  # Сумма будет определена на основе текущего стейка
            "fee": fee,
            "timestamp": time.time(),
            "type": "unstake"
        }
        
        # Подписываем транзакцию
        transaction["signature"] = self.sign_transaction(transaction)
        
        return transaction
        
    def get_stake_info(self) -> Dict[str, Any]:
        """
        Получает информацию о текущем стейке.
        
        Returns:
            Dict[str, Any]: Информация о стейке
        """
        # В реальном приложении здесь будет запрос к блокчейну
        return {
            "staked_amount": 0,
            "stake_time": 0,
            "is_validator": False,
            "can_unstake": False
        }
        
    def get_validator_status(self) -> Dict[str, Any]:
        """
        Получает статус валидатора.
        
        Returns:
            Dict[str, Any]: Статус валидатора
        """
        stake_info = self.get_stake_info()
        return {
            "is_validator": stake_info["is_validator"],
            "staked_amount": stake_info["staked_amount"],
            "stake_time": stake_info["stake_time"],
            "can_unstake": stake_info["can_unstake"]
        }
        
    def get_stake_rewards(self) -> float:
        """
        Получает накопленные награды за стейкинг.
        
        Returns:
            float: Сумма наград
        """
        # В реальном приложении здесь будет запрос к блокчейну
        return 0.0
        
    def claim_stake_rewards(self, fee: float = 0.001) -> Dict:
        """
        Создает транзакцию для получения наград за стейкинг.
        
        Args:
            fee: Комиссия за транзакцию
            
        Returns:
            Dict: Транзакция получения наград
        """
        rewards = self.get_stake_rewards()
        if rewards <= 0:
            raise WalletError("No rewards available to claim")
            
        transaction = {
            "from": "staking_pool",
            "to": self.get_address(),
            "amount": rewards,
            "fee": fee,
            "timestamp": time.time(),
            "type": "claim_rewards"
        }
        
        transaction["signature"] = self.sign_transaction(transaction)
        return transaction

def create_new_wallet(password: str = None, wallet_name: str = None) -> Tuple[str, str]:
    """
    Функция для создания нового кошелька с интерактивным запросом пароля.
    
    Args:
        password: Пароль для кошелька. Если None, будет запрошен интерактивно.
        wallet_name: Имя кошелька. Если None, будет использовано имя по умолчанию.
        
    Returns:
        Tuple[str, str]: Адрес кошелька и seed-фраза.
    """
    if password is None:
        password = getpass.getpass("Введите пароль для нового кошелька: ")
        password_confirm = getpass.getpass("Подтвердите пароль: ")
        
        if password != password_confirm:
            print("Пароли не совпадают!")
            return None, None
    
    # Создаем кошелек
    try:
        wallet = GrishiniumWallet.create_wallet(password, wallet_name)
        print(f"Кошелек успешно создан с адресом: {wallet.get_address()}")
        print("\nВнимание! Запишите вашу seed-фразу и храните ее в надежном месте:")
        print(wallet.get_seed_phrase())
        print("\nВы не сможете восстановить доступ к кошельку без этой фразы!")
        
        return wallet.get_address(), wallet.get_seed_phrase()
    except WalletExistsError:
        print(f"Кошелек с именем {wallet_name or 'default_wallet'} уже существует!")
        return None, None

def load_existing_wallet(seed_phrase: str = None, password: str = None, wallet_name: str = None) -> Optional[GrishiniumWallet]:
    """
    Функция для загрузки существующего кошелька с интерактивным запросом данных.
    
    Args:
        seed_phrase: Seed-фраза. Если None, будет запрошена интерактивно.
        password: Пароль для кошелька. Если None, будет запрошен интерактивно.
        wallet_name: Имя кошелька. Если None, будет использовано имя по умолчанию.
        
    Returns:
        Optional[GrishiniumWallet]: Загруженный кошелек или None в случае ошибки.
    """
    if seed_phrase is None:
        seed_phrase = input("Введите вашу seed-фразу (12 слов): ")
    
    if password is None:
        password = getpass.getpass("Введите пароль от кошелька: ")
    
    try:
        wallet = GrishiniumWallet.load_wallet(seed_phrase, password, wallet_name)
        print(f"Кошелек успешно загружен с адресом: {wallet.get_address()}")
        return wallet
    except (InvalidSeedError, InvalidPasswordError, WalletNotFoundError) as e:
        print(f"Ошибка при загрузке кошелька: {str(e)}")
        return None

def main():
    """Основная функция для интерактивной работы с кошельками."""
    print("Grishinium Wallet Manager")
    print("=========================")
    print("1. Создать новый кошелек")
    print("2. Загрузить существующий кошелек")
    print("3. Выйти")
    
    choice = input("Выберите действие (1-3): ")
    
    if choice == "1":
        create_new_wallet()
    elif choice == "2":
        wallet = load_existing_wallet()
        if wallet:
            # Меню для работы с кошельком
            print("\nОперации с кошельком:")
            print("1. Показать адрес")
            print("2. Создать транзакцию")
            print("3. Выйти")
            
            op_choice = input("Выберите операцию (1-3): ")
            
            if op_choice == "1":
                print(f"Адрес вашего кошелька: {wallet.get_address()}")
            elif op_choice == "2":
                recipient = input("Введите адрес получателя: ")
                amount = float(input("Введите сумму для отправки: "))
                fee = float(input("Введите комиссию (по умолчанию 0.001): ") or "0.001")
                
                tx = wallet.create_transaction(recipient, amount, fee)
                print("\nТранзакция создана:")
                print(json.dumps(tx, indent=4))
                print("\nДля отправки транзакции используйте API ноды Grishinium.")
    else:
        print("До свидания!")

if __name__ == "__main__":
    main() 