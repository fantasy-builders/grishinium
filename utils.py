"""
Grishinium Blockchain - Utility Functions
"""

import os
import json
import time
import logging
import hashlib
import binascii
import socket
import uuid
import platform
from typing import Dict, Any, List, Union, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumUtils')


def save_to_json_file(data: Any, filepath: str) -> bool:
    """
    Сохраняет данные в JSON файл.
    
    Args:
        data: Данные для сохранения
        filepath: Путь к файлу
        
    Returns:
        True, если сохранение успешно, иначе False
    """
    try:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        
        logger.debug(f"Данные успешно сохранены в {filepath}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в {filepath}: {str(e)}")
        return False


def load_from_json_file(filepath: str) -> Any:
    """
    Загружает данные из JSON файла.
    
    Args:
        filepath: Путь к файлу
        
    Returns:
        Загруженные данные или None в случае ошибки
    """
    try:
        if not os.path.exists(filepath):
            logger.warning(f"Файл {filepath} не существует")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        logger.debug(f"Данные успешно загружены из {filepath}")
        return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из {filepath}: {str(e)}")
        return None


def timestamp_to_readable(timestamp: float) -> str:
    """
    Преобразует временную метку Unix в читаемый формат.
    
    Args:
        timestamp: Временная метка Unix
        
    Returns:
        Строка с датой и временем
    """
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))


def readable_to_timestamp(datetime_str: str) -> float:
    """
    Преобразует строку с датой и временем в метку времени Unix.
    
    Args:
        datetime_str: Строка с датой и временем в формате '%Y-%m-%d %H:%M:%S'
        
    Returns:
        Временная метка Unix
    """
    try:
        time_struct = time.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        return time.mktime(time_struct)
    except ValueError:
        logger.error(f"Неверный формат даты и времени: {datetime_str}")
        return 0.0


def calculate_hash(data: Any) -> str:
    """
    Вычисляет SHA-256 хэш данных.
    
    Args:
        data: Данные для хэширования
        
    Returns:
        Хэш в виде шестнадцатеричной строки
    """
    json_data = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(json_data).hexdigest()


def calculate_merkle_root(transactions: List[Dict[str, Any]]) -> str:
    """
    Вычисляет корень дерева Меркла для списка транзакций.
    
    Args:
        transactions: Список транзакций
        
    Returns:
        Хэш корня дерева Меркла
    """
    if not transactions:
        return "0" * 64
    
    # Преобразуем транзакции в хэши
    transaction_hashes = [calculate_hash(tx) for tx in transactions]
    
    # Если количество транзакций нечетное, дублируем последнюю
    if len(transaction_hashes) % 2 == 1:
        transaction_hashes.append(transaction_hashes[-1])
    
    # Строим дерево Меркла
    while len(transaction_hashes) > 1:
        new_level = []
        
        # Объединяем пары хэшей и хэшируем
        for i in range(0, len(transaction_hashes), 2):
            combined = transaction_hashes[i] + transaction_hashes[i + 1]
            new_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_level.append(new_hash)
        
        transaction_hashes = new_level
        
        # Если количество хэшей на новом уровне нечетное, дублируем последний
        if len(transaction_hashes) % 2 == 1 and len(transaction_hashes) > 1:
            transaction_hashes.append(transaction_hashes[-1])
    
    return transaction_hashes[0]


def verify_merkle_proof(merkle_root: str, transaction_hash: str, proof: List[str], index: int) -> bool:
    """
    Проверяет доказательство Меркла для транзакции.
    
    Args:
        merkle_root: Корень дерева Меркла
        transaction_hash: Хэш транзакции
        proof: Список хэшей для доказательства
        index: Индекс транзакции в дереве
        
    Returns:
        True, если доказательство верно
    """
    computed_hash = transaction_hash
    
    for i, sibling_hash in enumerate(proof):
        if (index // (2 ** i)) % 2 == 0:
            computed_hash = hashlib.sha256((computed_hash + sibling_hash).encode()).hexdigest()
        else:
            computed_hash = hashlib.sha256((sibling_hash + computed_hash).encode()).hexdigest()
    
    return computed_hash == merkle_root


def format_amount(amount: float, decimals: int = 8) -> str:
    """
    Форматирует сумму Grishinium с указанным количеством десятичных знаков.
    
    Args:
        amount: Сумма в GRS
        decimals: Количество десятичных знаков
        
    Returns:
        Отформатированная строка
    """
    return f"{amount:.{decimals}f} GRS"


def bytes_to_hex(bytes_data: bytes) -> str:
    """
    Преобразует байты в шестнадцатеричную строку.
    
    Args:
        bytes_data: Байтовые данные
        
    Returns:
        Шестнадцатеричная строка
    """
    return binascii.hexlify(bytes_data).decode()


def hex_to_bytes(hex_str: str) -> bytes:
    """
    Преобразует шестнадцатеричную строку в байты.
    
    Args:
        hex_str: Шестнадцатеричная строка
        
    Returns:
        Байтовые данные
    """
    return binascii.unhexlify(hex_str)


def validate_address(address: str) -> bool:
    """
    Проверяет формат адреса Grishinium.
    
    Args:
        address: Адрес для проверки
        
    Returns:
        True, если адрес имеет правильный формат
    """
    # Простая проверка - адрес должен начинаться с 'GRS_' и иметь минимальную длину
    if not address.startswith('GRS_') or len(address) < 26:
        return False
    
    # Здесь можно добавить более сложную проверку, например, проверку контрольной суммы
    
    return True


def create_transaction_id(transaction: Dict[str, Any]) -> str:
    """
    Создает уникальный идентификатор транзакции.
    
    Args:
        transaction: Данные транзакции
        
    Returns:
        Идентификатор транзакции
    """
    # Исключаем поле 'id' из хэширования, если оно уже существует
    tx_data = transaction.copy()
    tx_data.pop('id', None)
    
    # Создаем хэш транзакции
    return calculate_hash(tx_data)


def validate_transaction(transaction: Dict[str, Any]) -> bool:
    """
    Проверяет базовую валидность транзакции.
    
    Args:
        transaction: Данные транзакции
        
    Returns:
        True, если транзакция валидна
    """
    # Проверяем наличие обязательных полей
    required_fields = ['from', 'to', 'amount', 'timestamp']
    if not all(field in transaction for field in required_fields):
        logger.warning("Транзакция не содержит все обязательные поля")
        return False
    
    # Проверяем адреса
    if not validate_address(transaction['from']) and transaction['from'] != 'system':
        logger.warning(f"Неверный адрес отправителя: {transaction['from']}")
        return False
    
    if not validate_address(transaction['to']):
        logger.warning(f"Неверный адрес получателя: {transaction['to']}")
        return False
    
    # Проверяем сумму
    if not isinstance(transaction['amount'], (int, float)) or transaction['amount'] <= 0:
        logger.warning(f"Неверная сумма: {transaction['amount']}")
        return False
    
    # Проверяем временную метку
    if not isinstance(transaction['timestamp'], (int, float)):
        logger.warning(f"Неверная временная метка: {transaction['timestamp']}")
        return False
    
    # Транзакция прошла базовую проверку
    return True


def measure_execution_time(func):
    """
    Декоратор для измерения времени выполнения функции.
    
    Args:
        func: Функция для измерения
        
    Returns:
        Обернутая функция
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"{func.__name__} выполнено за {end_time - start_time:.6f} сек.")
        return result
    return wrapper


def get_estimation_time(difficulty: int, hash_power: float) -> float:
    """
    Оценивает среднее время для майнинга блока с заданной сложностью и хэш-мощностью.
    
    Args:
        difficulty: Сложность майнинга (количество ведущих нулей)
        hash_power: Хэш-мощность в хэшах в секунду
        
    Returns:
        Ожидаемое время в секундах
    """
    # Вероятность нахождения хэша, удовлетворяющего сложности
    probability = 1.0 / (16 ** difficulty)
    
    # Среднее количество попыток
    average_attempts = 1.0 / probability
    
    # Время в секундах
    estimated_time = average_attempts / hash_power
    
    return estimated_time


def generate_node_id() -> str:
    """
    Генерирует уникальный идентификатор узла на основе характеристик системы и случайных значений.
    
    Returns:
        Строка с уникальным идентификатором узла
    """
    # Собираем характеристики системы
    system_info = [
        platform.node(),                # Имя хоста
        platform.system(),              # Операционная система
        platform.machine(),             # Архитектура
        str(uuid.getnode()),            # MAC-адрес
        socket.gethostname()            # Имя хоста
    ]
    
    # Добавляем случайное значение и текущее время для уникальности
    system_info.append(str(uuid.uuid4()))
    system_info.append(str(time.time()))
    
    # Объединяем и хешируем для получения идентификатора
    combined_info = "".join(system_info)
    node_id = hashlib.sha256(combined_info.encode()).hexdigest()
    
    logger.debug(f"Сгенерирован уникальный идентификатор узла: {node_id}")
    return node_id


# Пример использования
if __name__ == "__main__":
    # Демонстрация сохранения и загрузки данных
    test_data = {
        "name": "Grishinium",
        "version": "0.1.0",
        "blocks": [
            {"index": 0, "hash": "genesis_hash"}
        ]
    }
    
    # Сохраняем данные
    save_path = "test_data.json"
    save_to_json_file(test_data, save_path)
    
    # Загружаем данные
    loaded_data = load_from_json_file(save_path)
    print(f"Загруженные данные: {loaded_data}")
    
    # Удаляем тестовый файл
    if os.path.exists(save_path):
        os.remove(save_path)
    
    # Демонстрация работы с временными метками
    current_time = time.time()
    readable_time = timestamp_to_readable(current_time)
    print(f"Текущее время: {readable_time}")
    
    # Преобразуем обратно в метку времени
    timestamp = readable_to_timestamp(readable_time)
    print(f"Преобразовано обратно: {timestamp}")
    
    # Демонстрация вычисления корня дерева Меркла
    transactions = [
        {"from": "A", "to": "B", "amount": 10},
        {"from": "B", "to": "C", "amount": 5},
        {"from": "C", "to": "D", "amount": 3}
    ]
    
    merkle_root = calculate_merkle_root(transactions)
    print(f"Корень дерева Меркла: {merkle_root}")
    
    # Демонстрация форматирования суммы
    amount = 123.45678912345
    formatted = format_amount(amount)
    print(f"Отформатированная сумма: {formatted}")
    
    # Демонстрация оценки времени майнинга
    difficulty = 4
    hash_power = 1000000  # 1 млн хэшей в секунду
    estimate = get_estimation_time(difficulty, hash_power)
    print(f"Ориентировочное время майнинга: {estimate:.2f} сек. для сложности {difficulty} и хэш-мощности {hash_power} H/s") 