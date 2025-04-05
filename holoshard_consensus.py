"""
Grishinium Blockchain - HoloShard Consensus Integration

Этот модуль интегрирует технологию HoloShard с механизмом консенсуса блокчейна,
обеспечивая эффективное хранение и восстановление данных в распределенной сети.
"""

import logging
import time
import math
import random
from typing import List, Dict, Any, Optional, Tuple, Set
import hashlib
import json

import consensus
from holoshard import HoloShard, SHARD_COUNT, RECOVERY_THRESHOLD
from blockchain import Blockchain, Block

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumHoloShardConsensus')

# Константы для управления интеграцией HoloShard
HOLOSHARD_MIN_BLOCK_HEIGHT = 10  # Начиная с какой высоты блока применять HoloShard
HOLOSHARD_FULL_BLOCK_INTERVAL = 100  # Как часто сохранять полные копии блоков
HOLOSHARD_REBALANCE_INTERVAL = 24 * 60 * 60  # Интервал ребалансировки шардов (в секундах)
HOLOSHARD_VERIFICATION_NODES = 10  # Количество узлов для верификации при восстановлении
HOLOSHARD_RECOVERY_WINDOW = 50  # Окно блоков для восстановления данных при форке

# Глобальные объекты для работы с HoloShard
holoshard_instance = None
last_rebalance_time = 0
active_nodes = set()
shard_distribution = {}  # node_id -> list of shard_ids
block_shard_mapping = {}  # block_hash -> {shard_id: [node_ids]}


def initialize_holoshard(blockchain_id: str, genesis_seed: str) -> None:
    """
    Инициализирует систему HoloShard.
    
    Args:
        blockchain_id: Идентификатор блокчейна
        genesis_seed: Начальное значение для генерации ключей
    """
    global holoshard_instance, last_rebalance_time
    
    holoshard_instance = HoloShard(blockchain_id, genesis_seed)
    last_rebalance_time = time.time()
    
    logger.info(f"HoloShard инициализирован для блокчейна {blockchain_id}")


def register_node(node_id: str) -> None:
    """
    Регистрирует узел в системе HoloShard.
    
    Args:
        node_id: Идентификатор узла
    """
    global active_nodes
    
    active_nodes.add(node_id)
    logger.info(f"Узел {node_id} зарегистрирован в системе HoloShard")


def unregister_node(node_id: str) -> None:
    """
    Удаляет узел из системы HoloShard.
    
    Args:
        node_id: Идентификатор узла
    """
    global active_nodes, shard_distribution
    
    if node_id in active_nodes:
        active_nodes.remove(node_id)
        if node_id in shard_distribution:
            del shard_distribution[node_id]
        
        logger.info(f"Узел {node_id} удален из системы HoloShard")
        
        # Запускаем ребалансировку при удалении узла
        rebalance_shards()


def rebalance_shards() -> None:
    """
    Перераспределяет шарды между активными узлами для обеспечения отказоустойчивости.
    """
    global holoshard_instance, shard_distribution, last_rebalance_time
    
    if not holoshard_instance:
        logger.warning("HoloShard не инициализирован, ребалансировка невозможна")
        return
    
    # Проверяем, нужно ли выполнять ребалансировку
    current_time = time.time()
    if current_time - last_rebalance_time < HOLOSHARD_REBALANCE_INTERVAL and shard_distribution:
        logger.debug("Слишком рано для ребалансировки")
        return
    
    logger.info("Начало ребалансировки шардов")
    
    # Получаем активные узлы
    nodes = list(active_nodes)
    if not nodes:
        logger.warning("Нет активных узлов для ребалансировки")
        return
    
    # Запрашиваем ребалансировку у HoloShard
    try:
        new_distribution = holoshard_instance.rebalance_shards(nodes)
        shard_distribution = {node: set(shards) for node, shards in new_distribution.items()}
        last_rebalance_time = current_time
        
        logger.info(f"Ребалансировка завершена. Распределено {sum(len(s) for s in shard_distribution.values())} шардов между {len(nodes)} узлами")
    except Exception as e:
        logger.error(f"Ошибка при ребалансировке шардов: {e}")


def should_use_holoshard(block_height: int) -> bool:
    """
    Определяет, нужно ли использовать HoloShard для данной высоты блока.
    
    Args:
        block_height: Высота блока
        
    Returns:
        True, если нужно использовать HoloShard, иначе False
    """
    return block_height >= HOLOSHARD_MIN_BLOCK_HEIGHT


def should_store_full_block(block_height: int) -> bool:
    """
    Определяет, нужно ли сохранить полную копию блока (не только шарды).
    
    Args:
        block_height: Высота блока
        
    Returns:
        True, если нужно сохранить полную копию, иначе False
    """
    # Сохраняем полные копии каждые HOLOSHARD_FULL_BLOCK_INTERVAL блоков
    # и для блоков меньше HOLOSHARD_MIN_BLOCK_HEIGHT
    return (block_height < HOLOSHARD_MIN_BLOCK_HEIGHT or 
            block_height % HOLOSHARD_FULL_BLOCK_INTERVAL == 0)


def process_new_block(block_data: Dict[str, Any]) -> None:
    """
    Обрабатывает новый блок, применяя технологию HoloShard при необходимости.
    
    Args:
        block_data: Данные блока
    """
    global holoshard_instance, shard_distribution, block_shard_mapping
    
    if not holoshard_instance:
        logger.warning("HoloShard не инициализирован, блок будет обработан стандартным способом")
        return
    
    block_height = block_data.get("height", 0)
    block_hash = block_data.get("hash", "")
    
    # Проверяем, нужно ли использовать HoloShard
    if not should_use_holoshard(block_height):
        logger.debug(f"Блок {block_height} не использует HoloShard (высота меньше минимальной)")
        return
    
    logger.info(f"Обработка блока {block_height} с хешем {block_hash} с использованием HoloShard")
    
    # Создаем голографические шарды
    nodes = list(active_nodes)
    if not nodes:
        logger.warning("Нет активных узлов для распределения шардов")
        return
    
    try:
        # Распределяем шарды между узлами
        node_shards = holoshard_instance.distribute_shards(block_data, nodes)
        
        # Обновляем маппинг блок -> шарды
        block_shard_mapping[block_hash] = {}
        for node_id, shard_ids in node_shards.items():
            for shard_id in shard_ids:
                if shard_id not in block_shard_mapping[block_hash]:
                    block_shard_mapping[block_hash][shard_id] = []
                block_shard_mapping[block_hash][shard_id].append(node_id)
        
        # Обновляем распределение шардов
        for node_id, shard_ids in node_shards.items():
            if node_id not in shard_distribution:
                shard_distribution[node_id] = set()
            shard_distribution[node_id].update(shard_ids)
        
        logger.info(f"Блок {block_height} успешно разделен на {SHARD_COUNT} шардов и распределен между {len(nodes)} узлами")
    except Exception as e:
        logger.error(f"Ошибка при обработке блока {block_height} с HoloShard: {e}")


def recover_block(block_hash: str) -> Optional[Dict[str, Any]]:
    """
    Восстанавливает блок из голографических шардов.
    
    Args:
        block_hash: Хэш блока
        
    Returns:
        Восстановленный блок или None, если восстановление не удалось
    """
    global holoshard_instance, block_shard_mapping, active_nodes
    
    if not holoshard_instance:
        logger.warning("HoloShard не инициализирован, восстановление невозможно")
        return None
    
    if block_hash not in block_shard_mapping:
        logger.warning(f"Нет информации о шардах для блока {block_hash}")
        return None
    
    # Получаем узлы, содержащие шарды данного блока
    nodes_with_shards = set()
    for shard_id, node_ids in block_shard_mapping[block_hash].items():
        for node_id in node_ids:
            if node_id in active_nodes:
                nodes_with_shards.add(node_id)
    
    if not nodes_with_shards:
        logger.warning(f"Нет активных узлов с шардами для блока {block_hash}")
        return None
    
    # Выбираем подмножество узлов для верификации
    verification_nodes = list(nodes_with_shards)
    if len(verification_nodes) > HOLOSHARD_VERIFICATION_NODES:
        verification_nodes = random.sample(verification_nodes, HOLOSHARD_VERIFICATION_NODES)
    
    try:
        # Пытаемся восстановить блок
        logger.info(f"Попытка восстановления блока {block_hash} из шардов от {len(verification_nodes)} узлов")
        recovered_block = holoshard_instance.recover_block(block_hash, verification_nodes)
        
        if recovered_block:
            logger.info(f"Блок {block_hash} успешно восстановлен")
            return recovered_block
        else:
            logger.warning(f"Не удалось восстановить блок {block_hash}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при восстановлении блока {block_hash}: {e}")
        return None


def verify_recovered_block(block_data: Dict[str, Any]) -> bool:
    """
    Проверяет достоверность восстановленного блока.
    
    Args:
        block_data: Данные восстановленного блока
        
    Returns:
        True, если блок достоверен, иначе False
    """
    global holoshard_instance
    
    if not holoshard_instance:
        logger.warning("HoloShard не инициализирован, проверка невозможна")
        return False
    
    try:
        # Проверяем подлинность блока через HoloShard
        is_authentic = holoshard_instance.verify_block_authenticity(block_data)
        
        if is_authentic:
            # Дополнительная проверка через консенсус
            # (предполагается, что у нас есть доступ к предыдущему блоку и сложности)
            block_height = block_data.get("height", 0)
            prev_block_hash = block_data.get("previous_hash", "")
            
            # Здесь должна быть логика получения предыдущего блока и текущей сложности
            # Для примера используем фиктивные данные
            previous_block = {"hash": prev_block_hash, "height": block_height - 1}
            difficulty = block_data.get("difficulty", consensus.INITIAL_DIFFICULTY)
            
            # Проверяем блок через механизм консенсуса
            is_valid = consensus.verify_block(block_data, previous_block, difficulty)
            
            if is_valid:
                logger.info(f"Восстановленный блок {block_data.get('hash', '')} успешно проверен")
                return True
            else:
                logger.warning(f"Восстановленный блок не прошел проверку консенсуса")
                return False
        else:
            logger.warning(f"Восстановленный блок не прошел проверку аутентичности HoloShard")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке восстановленного блока: {e}")
        return False


def handle_fork(main_chain: List[Dict[str, Any]], fork_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Обрабатывает форк с использованием HoloShard для восстановления данных.
    
    Args:
        main_chain: Основная цепь блоков
        fork_chain: Форк-цепь блоков
        
    Returns:
        Выбранная цепь блоков после разрешения форка
    """
    global holoshard_instance
    
    if not holoshard_instance:
        logger.warning("HoloShard не инициализирован, форк будет обработан стандартным способом")
        # Используем стандартный алгоритм выбора форка
        return consensus.select_fork([main_chain, fork_chain], {})
    
    # Находим точку расхождения
    fork_point = 0
    for i in range(min(len(main_chain), len(fork_chain))):
        if main_chain[i]["hash"] != fork_chain[i]["hash"]:
            fork_point = i
            break
    
    logger.info(f"Обработка форка. Точка расхождения: блок {fork_point}")
    
    # Используем HoloShard для восстановления любых отсутствующих блоков в обеих цепях
    for chain in [main_chain, fork_chain]:
        for i in range(fork_point, len(chain)):
            block_hash = chain[i]["hash"]
            # Проверяем, нужно ли восстанавливать блок
            # (например, если у нас только его шарды, но не полное содержимое)
            if block_hash in block_shard_mapping and not should_store_full_block(chain[i]["height"]):
                # Восстанавливаем блок
                recovered_block = recover_block(block_hash)
                if recovered_block:
                    # Обновляем данные блока в цепи
                    chain[i].update(recovered_block)
    
    # Используем расширенный алгоритм выбора форка, который учитывает дополнительные факторы
    # благодаря голографическому хранению
    return select_holoshard_fork(main_chain, fork_chain)


def select_holoshard_fork(main_chain: List[Dict[str, Any]], fork_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Выбирает цепь на основе алгоритма, оптимизированного для использования с HoloShard.
    
    Args:
        main_chain: Основная цепь блоков
        fork_chain: Альтернативная цепь блоков (форк)
        
    Returns:
        Выбранная цепь блоков
    """
    # Базовое правило: выбираем более длинную цепь
    if len(fork_chain) > len(main_chain):
        logger.info(f"Выбран форк: длина {len(fork_chain)} > {len(main_chain)}")
        return fork_chain
    elif len(main_chain) > len(fork_chain):
        logger.info(f"Сохранена основная цепь: длина {len(main_chain)} > {len(fork_chain)}")
        return main_chain
    
    # Если цепи одинаковой длины, используем дополнительные критерии
    
    # 1. Суммарная сложность цепи
    main_difficulty = sum(block.get("difficulty", 0) for block in main_chain)
    fork_difficulty = sum(block.get("difficulty", 0) for block in fork_chain)
    
    if fork_difficulty > main_difficulty:
        logger.info(f"Выбран форк: сложность {fork_difficulty} > {main_difficulty}")
        return fork_chain
    elif main_difficulty > fork_difficulty:
        logger.info(f"Сохранена основная цепь: сложность {main_difficulty} > {fork_difficulty}")
        return main_chain
    
    # 2. Голографическая целостность (количество узлов, хранящих шарды)
    main_integrity = calculate_chain_integrity(main_chain)
    fork_integrity = calculate_chain_integrity(fork_chain)
    
    if fork_integrity > main_integrity:
        logger.info(f"Выбран форк: целостность {fork_integrity} > {main_integrity}")
        return fork_chain
    elif main_integrity > fork_integrity:
        logger.info(f"Сохранена основная цепь: целостность {main_integrity} > {fork_integrity}")
        return main_chain
    
    # 3. Если все критерии равны, сохраняем текущую цепь
    logger.info("Все критерии равны, сохраняем основную цепь")
    return main_chain


def calculate_chain_integrity(chain: List[Dict[str, Any]]) -> float:
    """
    Вычисляет интегральную метрику целостности цепи на основе распределения шардов.
    
    Args:
        chain: Цепь блоков
        
    Returns:
        Метрика целостности от 0 до 1
    """
    global block_shard_mapping, active_nodes
    
    if not chain or not active_nodes:
        return 0.0
    
    # Получаем блоки, для которых нужны шарды
    relevant_blocks = [
        block for block in chain 
        if should_use_holoshard(block.get("height", 0)) and not should_store_full_block(block.get("height", 0))
    ]
    
    if not relevant_blocks:
        return 1.0  # Все блоки хранятся полностью
    
    total_integrity = 0.0
    
    for block in relevant_blocks:
        block_hash = block.get("hash", "")
        
        if block_hash not in block_shard_mapping:
            continue
        
        # Подсчитываем количество активных узлов, хранящих шарды блока
        shard_map = block_shard_mapping[block_hash]
        active_shard_nodes = set()
        
        for shard_id, node_ids in shard_map.items():
            active_shard_nodes.update(node_id for node_id in node_ids if node_id in active_nodes)
        
        # Вычисляем соотношение активных узлов к общему количеству
        node_ratio = len(active_shard_nodes) / len(active_nodes) if active_nodes else 0
        
        # Учитываем количество доступных шардов
        shard_coverage = len(shard_map) / SHARD_COUNT
        
        # Вычисляем интегральную метрику для блока
        block_integrity = (node_ratio * 0.7 + shard_coverage * 0.3)
        total_integrity += block_integrity
    
    # Возвращаем среднюю целостность
    return total_integrity / len(relevant_blocks) if relevant_blocks else 0.0


class HoloShardConsensus:
    """
    Класс для интеграции HoloShard с консенсусом блокчейна.
    """
    
    def __init__(self, blockchain_id: str, genesis_seed: str, initial_difficulty: int = 4) -> None:
        """
        Инициализирует механизм консенсуса HoloShard.
        
        Args:
            blockchain_id: Идентификатор блокчейна
            genesis_seed: Начальный сид для генерации ключей
            initial_difficulty: Начальная сложность майнинга
        """
        self.blockchain_id = blockchain_id
        self.genesis_seed = genesis_seed
        self.difficulty = initial_difficulty
        self.mining_async_active = False
        
        # Инициализируем HoloShard
        initialize_holoshard(blockchain_id, genesis_seed)
        
        logger.info(f"Механизм консенсуса HoloShard инициализирован с начальной сложностью {initial_difficulty}")
    
    def mine_block(self, block_data: Dict[str, Any], miner_address: str) -> Tuple[int, str]:
        """
        Майнит блок с использованием алгоритма доказательства работы.
        
        Args:
            block_data: Данные блока
            miner_address: Адрес майнера
            
        Returns:
            Кортеж (nonce, hash)
        """
        return consensus.mine_block(block_data, self.difficulty)
    
    def mine_block_async(self, block_data: Dict[str, Any], miner_address: str, callback) -> None:
        """
        Запускает асинхронный майнинг блока.
        
        Args:
            block_data: Данные блока
            miner_address: Адрес майнера
            callback: Функция обратного вызова при завершении майнинга
        """
        self.mining_async_active = True
        
        import threading
        
        def mining_thread():
            if not self.mining_async_active:
                callback(None, None)
                return
            
            nonce, block_hash = self.mine_block(block_data, miner_address)
            
            if self.mining_async_active:
                callback(nonce, block_hash)
        
        thread = threading.Thread(target=mining_thread)
        thread.daemon = True
        thread.start()
    
    def stop_mining_async(self) -> None:
        """Останавливает асинхронный майнинг."""
        self.mining_async_active = False
    
    def adjust_difficulty(self, blockchain: List[Dict[str, Any]]) -> None:
        """
        Корректирует сложность на основе времени создания последних блоков.
        
        Args:
            blockchain: Текущий блокчейн
        """
        self.difficulty = consensus.adjust_difficulty(blockchain, self.difficulty)
    
    def verify_block(self, block: Dict[str, Any], previous_block: Dict[str, Any]) -> bool:
        """
        Проверяет валидность блока.
        
        Args:
            block: Проверяемый блок
            previous_block: Предыдущий блок
            
        Returns:
            True, если блок валиден, иначе False
        """
        # Проверяем блок через стандартный механизм консенсуса
        is_valid = consensus.verify_block(block, previous_block, self.difficulty)
        
        if not is_valid:
            return False
        
        # Если блок должен использовать HoloShard, проводим дополнительную проверку
        if should_use_holoshard(block.get("height", 0)):
            # Обрабатываем блок через HoloShard
            process_new_block(block)
        
        return True
    
    def resolve_fork(self, main_chain: List[Dict[str, Any]], fork_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Разрешает форк, выбирая одну из цепей.
        
        Args:
            main_chain: Основная цепь блоков
            fork_chain: Форк-цепь блоков
            
        Returns:
            Выбранная цепь блоков
        """
        return handle_fork(main_chain, fork_chain)
    
    def on_block_added(self, block: Dict[str, Any]) -> None:
        """
        Обрабатывает добавление нового блока в цепь.
        
        Args:
            block: Добавленный блок
        """
        # Если блок должен использовать HoloShard, обрабатываем его
        if should_use_holoshard(block.get("height", 0)):
            process_new_block(block)
    
    def on_node_joined(self, node_id: str) -> None:
        """
        Обрабатывает присоединение нового узла к сети.
        
        Args:
            node_id: Идентификатор узла
        """
        register_node(node_id)
        # При необходимости запускаем ребалансировку
        if len(active_nodes) % 10 == 0:  # Каждые 10 узлов
            rebalance_shards()
    
    def on_node_left(self, node_id: str) -> None:
        """
        Обрабатывает выход узла из сети.
        
        Args:
            node_id: Идентификатор узла
        """
        unregister_node(node_id) 