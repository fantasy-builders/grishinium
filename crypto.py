"""
Grishinium Blockchain - Cryptographic Functions

Усиленный криптографический модуль с дополнительными функциями безопасности.
"""

import hashlib
import base64
import json
import os
import logging
import hmac
import time
from typing import Tuple, Dict, Any, Optional, List, Union
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidSignature
from secrets import token_bytes, randbelow

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumCrypto')

# Константы для криптографической безопасности
KEY_SIZE = 3072  # Увеличенный размер ключа RSA для большей безопасности
EC_CURVE = ec.SECP384R1()  # Эллиптическая кривая для ED25519
PBKDF2_ITERATIONS = 600000  # Увеличенное количество итераций для PBKDF2
AES_KEY_SIZE = 256  # Размер ключа AES в битах
AUTH_TAG_SIZE = 16  # Размер тега аутентификации для GCM в байтах
NONCE_SIZE = 12  # Размер nonce для AES-GCM в байтах
SALT_SIZE = 32  # Размер соли в байтах

# Опции для безопасного RSA подписывания
SECURE_PADDING = padding.PSS(
    mgf=padding.MGF1(hashes.SHA512()),
    salt_length=padding.PSS.MAX_LENGTH
)
SECURE_HASH = hashes.SHA512()

def generate_key_pair(key_type: str = "rsa") -> Tuple[str, str]:
    """
    Генерирует новую пару криптографических ключей.
    
    Args:
        key_type: Тип ключа - "rsa" или "ec" (эллиптическая кривая)
    
    Returns:
        Кортеж (приватный ключ, публичный ключ) в PEM формате
    """
    if key_type.lower() == "rsa":
        # Генерируем RSA ключи с улучшенной безопасностью
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=KEY_SIZE
        )
    elif key_type.lower() == "ec":
        # Генерируем ключи на основе эллиптической кривой
        private_key = ec.generate_private_key(EC_CURVE)
    else:
        raise ValueError(f"Неподдерживаемый тип ключа: {key_type}")
    
    # Извлекаем публичный ключ
    public_key = private_key.public_key()
    
    # Сериализуем приватный ключ в PEM формат
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Сериализуем публичный ключ в PEM формат
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    logger.info(f"Сгенерирована новая пара ключей {key_type.upper()}")
    
    return private_pem, public_pem


def get_address_from_public_key(public_key: str, version: int = 0) -> str:
    """
    Генерирует адрес Grishinium из открытого ключа с улучшенной безопасностью.
    
    Args:
        public_key: Публичный ключ в PEM формате
        version: Версия адреса для поддержки будущих изменений формата
        
    Returns:
        Адрес кошелька Grishinium
    """
    # Хэшируем публичный ключ с SHA3-256 (более безопасная версия SHA)
    sha3_hash = hashlib.sha3_256(public_key.encode()).digest()
    
    # Применяем RIPEMD-160 к результату SHA3-256
    ripemd160_hash = hashlib.new('ripemd160')
    ripemd160_hash.update(sha3_hash)
    
    # Добавляем префикс версии сети (1 байт)
    versioned_hash = bytes([version]) + ripemd160_hash.digest()
    
    # Вычисляем двойной SHA3-256 для контрольной суммы
    checksum_data = hashlib.sha3_256(versioned_hash).digest()
    checksum_data = hashlib.sha3_256(checksum_data).digest()
    
    # Берем первые 4 байта для контрольной суммы
    checksum = checksum_data[:4]
    
    # Объединяем версионный хэш и контрольную сумму
    binary_address = versioned_hash + checksum
    
    # Кодируем в base58 для удобочитаемости и компактности
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    value = int.from_bytes(binary_address, byteorder='big')
    result = ''
    
    while value:
        value, mod = divmod(value, 58)
        result = alphabet[mod] + result
    
    # Кодируем ведущие нули
    for byte in binary_address:
        if byte == 0:
            result = alphabet[0] + result
        else:
            break
    
    # Добавляем префикс GRS для адресов Grishinium
    address = 'GRS_' + result
    
    logger.debug(f"Создан адрес Grishinium: {address}")
    
    return address


def sign_transaction(private_key_pem: str, transaction_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Подписывает транзакцию с приватным ключом, используя усиленный алгоритм подписи.
    
    Args:
        private_key_pem: Приватный ключ в PEM формате
        transaction_data: Данные транзакции
        
    Returns:
        Словарь с подписью в base64 и метаданными
    """
    # Загружаем приватный ключ
    private_key = load_pem_private_key(
        private_key_pem.encode(),
        password=None
    )
    
    # Получаем метку времени для предотвращения replay атак
    current_time = int(time.time())
    
    # Добавляем nonce для уникальности каждой подписи
    nonce = base64.b64encode(os.urandom(16)).decode('utf-8')
    
    # Добавляем метаданные к подписываемым данным для предотвращения атак
    to_sign = transaction_data.copy()
    to_sign['signature_metadata'] = {
        'timestamp': current_time,
        'nonce': nonce,
        'version': '1.0'
    }
    
    # Преобразуем данные транзакции в строку JSON с кодировкой UTF-8 и сортировкой ключей
    transaction_json = json.dumps(to_sign, sort_keys=True, ensure_ascii=False).encode('utf-8')
    
    # Создаем подпись с использованием более безопасных алгоритмов
    if isinstance(private_key, rsa.RSAPrivateKey):
        signature = private_key.sign(
            transaction_json,
            SECURE_PADDING,
            SECURE_HASH
        )
    elif isinstance(private_key, ec.EllipticCurvePrivateKey):
        signature = private_key.sign(
            transaction_json,
            ec.ECDSA(hashes.SHA512())
        )
    else:
        raise TypeError("Неподдерживаемый тип ключа")
    
    # Кодируем подпись в base64
    signature_base64 = base64.b64encode(signature).decode()
    
    logger.debug(f"Создана подпись для транзакции с nonce {nonce}")
    
    # Возвращаем подпись и метаданные
    return {
        'signature': signature_base64,
        'timestamp': current_time,
        'nonce': nonce,
        'version': '1.0'
    }


def verify_signature(public_key_pem: str, transaction_data: Dict[str, Any], 
                    signature_data: Dict[str, str]) -> bool:
    """
    Проверяет подпись транзакции с защитой от различных атак.
    
    Args:
        public_key_pem: Публичный ключ в PEM формате
        transaction_data: Данные транзакции
        signature_data: Словарь с подписью и метаданными
        
    Returns:
        True, если подпись верна, иначе False
    """
    try:
        # Загружаем публичный ключ
        public_key = load_pem_public_key(
            public_key_pem.encode()
        )
        
        # Извлекаем данные подписи
        signature_base64 = signature_data.get('signature')
        timestamp = signature_data.get('timestamp')
        nonce = signature_data.get('nonce')
        version = signature_data.get('version', '1.0')
        
        # Проверяем наличие всех необходимых компонентов
        if not all([signature_base64, timestamp, nonce]):
            logger.warning("Отсутствуют необходимые данные подписи")
            return False
        
        # Проверка времени подписи (не старше 15 минут) для защиты от replay-атак
        current_time = int(time.time())
        if current_time - timestamp > 900:  # 15 минут в секундах
            logger.warning("Подпись устарела")
            return False
        
        # Декодируем подпись из base64
        signature = base64.b64decode(signature_base64)
        
        # Реконструируем подписанные данные
        to_verify = transaction_data.copy()
        to_verify['signature_metadata'] = {
            'timestamp': timestamp,
            'nonce': nonce,
            'version': version
        }
        
        # Преобразуем данные транзакции в строку JSON
        transaction_json = json.dumps(to_verify, sort_keys=True, ensure_ascii=False).encode('utf-8')
        
        # Проверяем подпись с соответствующим алгоритмом в зависимости от типа ключа
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature,
                transaction_json,
                SECURE_PADDING,
                SECURE_HASH
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                signature,
                transaction_json,
                ec.ECDSA(hashes.SHA512())
            )
        else:
            logger.warning("Неподдерживаемый тип ключа")
            return False
        
        logger.debug("Подпись транзакции верифицирована успешно")
        return True
    
    except InvalidSignature:
        logger.warning("Неверная подпись транзакции")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке подписи: {str(e)}")
        return False


def hash_data(data: Any, algorithm: str = 'sha3_256') -> str:
    """
    Вычисляет криптографический хэш для данных с выбором алгоритма.
    
    Args:
        data: Данные для хэширования
        algorithm: Алгоритм хэширования ('sha256', 'sha3_256', 'blake2b')
        
    Returns:
        Хэш в виде шестнадцатеричной строки
    """
    # Преобразуем данные в JSON с сортировкой ключей для детерминированности
    data_json = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
    
    # Выбираем алгоритм хэширования
    if algorithm == 'sha256':
        hash_obj = hashlib.sha256(data_json)
    elif algorithm == 'sha3_256':
        hash_obj = hashlib.sha3_256(data_json)
    elif algorithm == 'blake2b':
        hash_obj = hashlib.blake2b(data_json)
    else:
        raise ValueError(f"Неподдерживаемый алгоритм хэширования: {algorithm}")
    
    return hash_obj.hexdigest()


def generate_secure_random(size: int = 32) -> bytes:
    """
    Генерирует криптографически безопасное случайное число.
    
    Args:
        size: Размер случайного числа в байтах
        
    Returns:
        Случайные байты
    """
    return token_bytes(size)


def encrypt_data(data: Union[str, bytes], key: bytes) -> Dict[str, str]:
    """
    Шифрует данные с использованием AES-GCM с аутентификацией.
    
    Args:
        data: Данные для шифрования (строка или байты)
        key: Ключ шифрования (должен быть 32 байта для AES-256)
        
    Returns:
        Словарь с зашифрованными данными, nonce и тегом аутентификации
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Проверяем длину ключа
    if len(key) != AES_KEY_SIZE // 8:
        raise ValueError(f"Ключ должен быть {AES_KEY_SIZE // 8} байт для AES-{AES_KEY_SIZE}")
    
    # Генерируем nonce (не должен повторяться с тем же ключом)
    nonce = token_bytes(NONCE_SIZE)
    
    # Создаем шифр AES-GCM
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    
    # Шифруем данные и получаем тег аутентификации
    ciphertext = encryptor.update(data) + encryptor.finalize()
    tag = encryptor.tag
    
    # Возвращаем результаты в формате, удобном для хранения
    return {
        'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
        'nonce': base64.b64encode(nonce).decode('utf-8'),
        'tag': base64.b64encode(tag).decode('utf-8')
    }


def decrypt_data(encrypted_data: Dict[str, str], key: bytes) -> bytes:
    """
    Расшифровывает данные, зашифрованные с помощью AES-GCM.
    
    Args:
        encrypted_data: Словарь с зашифрованными данными, nonce и тегом
        key: Ключ расшифрования
        
    Returns:
        Расшифрованные данные в виде байтов
    """
    # Декодируем данные из base64
    ciphertext = base64.b64decode(encrypted_data['ciphertext'])
    nonce = base64.b64decode(encrypted_data['nonce'])
    tag = base64.b64decode(encrypted_data['tag'])
    
    # Создаем шифр AES-GCM для расшифровки
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()
    
    # Расшифровываем данные
    try:
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext
    except Exception as e:
        logger.error(f"Ошибка при расшифровке данных: {str(e)}")
        raise ValueError("Ошибка расшифровки: данные повреждены или ключ неверный")


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Выводит криптографический ключ из пароля с использованием PBKDF2.
    
    Args:
        password: Пароль пользователя
        salt: Соль (если None, будет сгенерирована новая)
        
    Returns:
        Кортеж (ключ, соль)
    """
    # Генерируем соль, если она не предоставлена
    if salt is None:
        salt = token_bytes(SALT_SIZE)
    
    # Используем PBKDF2 для получения ключа
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA512(),
        length=AES_KEY_SIZE // 8,  # 32 байта для AES-256
        salt=salt,
        iterations=PBKDF2_ITERATIONS
    )
    
    # Выводим ключ из пароля
    key = kdf.derive(password.encode('utf-8'))
    
    return key, salt


def create_hmac(data: Union[str, bytes], key: bytes) -> str:
    """
    Создает HMAC для аутентификации данных.
    
    Args:
        data: Данные для аутентификации
        key: Ключ для HMAC
        
    Returns:
        HMAC в виде hex-строки
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Создаем HMAC с SHA-512
    h = hmac.new(key, data, hashlib.sha512)
    return h.hexdigest()


def verify_hmac(data: Union[str, bytes], key: bytes, expected_hmac: str) -> bool:
    """
    Проверяет HMAC для аутентификации данных.
    
    Args:
        data: Данные для аутентификации
        key: Ключ для HMAC
        expected_hmac: Ожидаемый HMAC
        
    Returns:
        True, если HMAC верный, иначе False
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Вычисляем HMAC
    h = hmac.new(key, data, hashlib.sha512)
    calculated_hmac = h.hexdigest()
    
    # Сравниваем вычисленный HMAC с ожидаемым (защита от атак по времени)
    return hmac.compare_digest(calculated_hmac, expected_hmac)


def generate_session_key() -> str:
    """
    Генерирует уникальный сессионный ключ для защиты от replay-атак.
    
    Returns:
        Сессионный ключ в виде hex-строки
    """
    # Генерируем случайные данные
    random_data = token_bytes(32)
    
    # Добавляем метку времени для уникальности
    timestamp = int(time.time()).to_bytes(8, byteorder='big')
    
    # Комбинируем данные и хэшируем
    session_key = hashlib.blake2b(random_data + timestamp).hexdigest()
    
    return session_key


def generate_zero_knowledge_proof(private_key_pem: str, challenge: str) -> Dict[str, str]:
    """
    Генерирует доказательство с нулевым разглашением для аутентификации без передачи ключа.
    
    Args:
        private_key_pem: Приватный ключ в PEM формате
        challenge: Случайная строка-вызов для предотвращения replay-атак
        
    Returns:
        Словарь с данными доказательства
    """
    # Загружаем приватный ключ
    private_key = load_pem_private_key(
        private_key_pem.encode(),
        password=None
    )
    
    # Подписываем вызов с помощью приватного ключа
    if isinstance(private_key, rsa.RSAPrivateKey):
        signature = private_key.sign(
            challenge.encode(),
            SECURE_PADDING,
            SECURE_HASH
        )
    elif isinstance(private_key, ec.EllipticCurvePrivateKey):
        signature = private_key.sign(
            challenge.encode(),
            ec.ECDSA(hashes.SHA512())
        )
    else:
        raise TypeError("Неподдерживаемый тип ключа")
    
    # Получаем публичный ключ
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Возвращаем доказательство
    return {
        'public_key': public_pem,
        'challenge': challenge,
        'response': base64.b64encode(signature).decode(),
        'timestamp': str(int(time.time()))
    }


def verify_zero_knowledge_proof(proof: Dict[str, str], challenge: str) -> bool:
    """
    Проверяет доказательство с нулевым разглашением.
    
    Args:
        proof: Словарь с данными доказательства
        challenge: Ожидаемый вызов
        
    Returns:
        True, если доказательство верное, иначе False
    """
    try:
        # Проверяем, что вызов соответствует
        if proof['challenge'] != challenge:
            logger.warning("Несоответствие вызова")
            return False
        
        # Проверяем время (не старше 1 минуты)
        timestamp = int(proof['timestamp'])
        if int(time.time()) - timestamp > 60:
            logger.warning("Доказательство устарело")
            return False
        
        # Загружаем публичный ключ
        public_key = load_pem_public_key(proof['public_key'].encode())
        
        # Декодируем подпись
        signature = base64.b64decode(proof['response'])
        
        # Проверяем подпись
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature,
                challenge.encode(),
                SECURE_PADDING,
                SECURE_HASH
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                signature,
                challenge.encode(),
                ec.ECDSA(hashes.SHA512())
            )
        else:
            logger.warning("Неподдерживаемый тип ключа")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при проверке доказательства: {str(e)}")
        return False


# Пример использования
if __name__ == "__main__":
    # Генерируем пару ключей RSA
    private_key_rsa, public_key_rsa = generate_key_pair("rsa")
    print(f"RSA приватный ключ: {private_key_rsa[:64]}...")
    print(f"RSA публичный ключ: {public_key_rsa[:64]}...")
    
    # Генерируем пару ключей на эллиптической кривой
    private_key_ec, public_key_ec = generate_key_pair("ec")
    print(f"EC приватный ключ: {private_key_ec[:64]}...")
    print(f"EC публичный ключ: {public_key_ec[:64]}...")
    
    # Генерируем адрес из публичного ключа
    address = get_address_from_public_key(public_key_rsa)
    print(f"Адрес Grishinium: {address}")
    
    # Создаем тестовую транзакцию
    transaction = {
        "from": address,
        "to": "GRS_AnotherAddress",
        "amount": 10.0,
        "timestamp": time.time()
    }
    
    # Подписываем транзакцию
    signature_data = sign_transaction(private_key_rsa, transaction)
    print(f"Подпись: {signature_data['signature'][:64]}...")
    
    # Проверяем подпись
    is_valid = verify_signature(public_key_rsa, transaction, signature_data)
    print(f"Подпись верна: {is_valid}")
    
    # Пример шифрования данных
    password = "strong_password"
    key, salt = derive_key_from_password(password)
    
    secret_message = "Секретные данные для блокчейна"
    encrypted = encrypt_data(secret_message, key)
    print(f"Зашифрованные данные: {encrypted['ciphertext'][:30]}...")
    
    # Расшифровка данных
    decrypted = decrypt_data(encrypted, key)
    print(f"Расшифрованные данные: {decrypted.decode('utf-8')}")
    
    # Генерация доказательства с нулевым разглашением
    challenge = base64.b64encode(os.urandom(32)).decode('utf-8')
    proof = generate_zero_knowledge_proof(private_key_rsa, challenge)
    print(f"Доказательство создано: {proof['response'][:30]}...")
    
    # Проверка доказательства
    is_valid_proof = verify_zero_knowledge_proof(proof, challenge)
    print(f"Доказательство верно: {is_valid_proof}") 