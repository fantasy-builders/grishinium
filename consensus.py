"""
Grishinium Blockchain - Механизм консенсуса

Модуль содержит реализацию механизма консенсуса Proof-of-Work с улучшенной защитой от атак.
Включает гибридный механизм PoW/PoS для защиты от атаки 51%.
"""

import hashlib
import time
import random
import math
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import crypto
from collections import defaultdict, Counter

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumConsensus')

# Константы для настройки сложности и безопасности
INITIAL_DIFFICULTY = 4  # Начальная сложность (количество ведущих нулей)
TARGET_BLOCK_TIME = 150  # Целевое время блока в секундах (2.5 минуты)
DIFFICULTY_ADJUSTMENT_INTERVAL = 100  # Интервал пересчета сложности (блоки)
MAX_DIFFICULTY_ADJUSTMENT = 25  # Максимальное изменение сложности в процентах
STAKE_WEIGHT_FACTOR = 0.4  # Вес стейка в гибридном консенсусе
HASH_ALGORITHM = 'sha3_256'  # Алгоритм хеширования по умолчанию
MAX_FUTURE_BLOCK_TIME = 120  # Максимальное время в будущем для блока (в секундах)
MIN_STAKE_AMOUNT = 100  # Минимальное количество монет для участия в стейкинге
STAKE_MATURITY_TIME = 86400  # Время созревания стейка в секундах (24 часа)
UNCLE_BLOCKS_LIMIT = 10  # Максимальное количество uncle-блоков
UNCLE_BLOCKS_MAX_HEIGHT_DIFF = 7  # Максимальная разница в высоте для uncle-блоков

# Параметры защиты от атак
NODE_REPUTATION_DECAY = 0.99  # Коэффициент "забывания" репутации узлов
REPUTATION_THRESHOLD = -100  # Порог репутации для блокировки узла
FORK_CHOICE_ALGORITHM = "GHOST"  # Алгоритм выбора форка (GHOST, LCR, GHST)
BLOCK_REWARD_HALF_LIFE = 210000  # Интервал уменьшения награды за блок (блоки)
REWARD_VARIABILITY = 0.1  # Вариативность награды для защиты от атак
MEMPOOL_MAX_SIZE = 100000  # Максимальный размер мемпула

# Reputation хранилище (в реальной системе должно быть персистентным)
node_reputation: Dict[str, float] = defaultdict(float)
banned_nodes: Set[str] = set()
fork_histories: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


class ProofOfWork:
    """Класс реализующий механизм консенсуса Proof of Work."""
    
    def __init__(self, initial_difficulty: int = INITIAL_DIFFICULTY):
        """
        Инициализация механизма консенсуса.
        
        Args:
            initial_difficulty: Начальная сложность
        """
        self.difficulty = initial_difficulty
        logger.info(f"Инициализирован механизм ProofOfWork с начальной сложностью {initial_difficulty}")
    
    def mine_block(self, block_data: Dict[str, Any], max_nonce: int = 1000000000) -> Tuple[int, str]:
        """
        Майнит блок, находя подходящий nonce.
        
        Args:
            block_data: Данные блока
            max_nonce: Максимальное значение nonce для перебора
            
        Returns:
            Кортеж (найденный nonce, хеш блока)
        """
        return mine_block(block_data, self.difficulty, max_nonce)
    
    def verify_block(self, block_hash: str) -> bool:
        """
        Проверяет, удовлетворяет ли хеш требуемой сложности.
        
        Args:
            block_hash: Хеш блока
            
        Returns:
            True, если хеш удовлетворяет сложности, иначе False
        """
        return check_proof_of_work(block_hash, self.difficulty)
    
    def adjust_difficulty(self, blockchain: List[Dict[str, Any]]) -> None:
        """
        Корректирует сложность на основе времени создания последних блоков.
        
        Args:
            blockchain: Текущий блокчейн
        """
        self.difficulty = adjust_difficulty(blockchain, self.difficulty)
        logger.info(f"Сложность скорректирована до {self.difficulty}")


class MiningRewardsCalculator:
    """Класс для расчета вознаграждений за майнинг."""
    
    def __init__(self, initial_reward: float = 50.0):
        """
        Инициализация калькулятора вознаграждений.
        
        Args:
            initial_reward: Начальное вознаграждение за блок
        """
        self.initial_reward = initial_reward
        logger.info(f"Инициализирован калькулятор наград с начальным вознаграждением {initial_reward}")
    
    def calculate_block_reward(self, height: int) -> float:
        """
        Вычисляет награду за блок с учетом уменьшения и случайной вариации.
        
        Args:
            height: Высота блока
            
        Returns:
            Награда за блок в монетах
        """
        return calculate_block_reward(height)


def calculate_hash(block_data: Dict[str, Any], nonce: int, algorithm: str = HASH_ALGORITHM) -> str:
    """
    Вычисляет хеш блока с учетом выбранного алгоритма.
    
    Args:
        block_data: Данные блока
        nonce: Одноразовое число для майнинга
        algorithm: Алгоритм хэширования
        
    Returns:
        Хеш блока в шестнадцатеричном представлении
    """
    # Создаем копию и добавляем nonce
    data_with_nonce = block_data.copy()
    data_with_nonce['nonce'] = nonce
    
    # Используем улучшенный алгоритм хэширования
    return crypto.hash_data(data_with_nonce, algorithm)


def check_proof_of_work(block_hash: str, difficulty: int) -> bool:
    """
    Проверяет, удовлетворяет ли хеш требуемой сложности.
    
    Args:
        block_hash: Хеш блока
        difficulty: Требуемая сложность (число ведущих нулей)
        
    Returns:
        True, если хеш удовлетворяет сложности, иначе False
    """
    # Проверяем, начинается ли хеш с требуемого количества нулей
    return block_hash.startswith('0' * difficulty)


def mine_block(block_data: Dict[str, Any], difficulty: int, max_nonce: int = 1000000000) -> Tuple[int, str]:
    """
    Майнит блок, находя подходящий nonce.
    
    Args:
        block_data: Данные блока
        difficulty: Сложность майнинга
        max_nonce: Максимальное значение nonce для перебора
        
    Returns:
        Кортеж (найденный nonce, хеш блока)
    """
    logger.info(f"Начало майнинга блока с высотой {block_data.get('height', 'unknown')} и сложностью {difficulty}")
    
    # Добавляем случайное значение для дополнительной уникальности
    # и защиты от предсказуемых коллизий хеширования
    block_data['mining_entropy'] = crypto.generate_session_key()
    
    # Выбираем алгоритм хеширования в зависимости от высоты блока
    # для защиты от ASIC-майнеров
    mining_algorithm = select_mining_algorithm(block_data.get('height', 0))
    
    start_time = time.time()
    nonce = 0
    
    while nonce < max_nonce:
        # Проверяем, соответствует ли хеш требуемой сложности
        block_hash = calculate_hash(block_data, nonce, mining_algorithm)
        
        if check_proof_of_work(block_hash, difficulty):
            # Найдено решение
            end_time = time.time()
            mining_time = end_time - start_time
            logger.info(f"Блок успешно смайнен за {mining_time:.2f} секунд. Nonce: {nonce}, Хеш: {block_hash}")
            return nonce, block_hash
        
        nonce += 1
        
        # Раз в 100,000 попыток показываем прогресс
        if nonce % 100000 == 0:
            logger.debug(f"Майнинг в процессе... Перебрано {nonce} значений nonce")
    
    logger.warning(f"Майнинг не удался после {max_nonce} попыток")
    return -1, ""


def select_mining_algorithm(height: int) -> str:
    """
    Выбирает алгоритм хеширования в зависимости от высоты блока.
    Это защищает от специализированного оборудования и централизации майнинга.
    
    Args:
        height: Высота блока
        
    Returns:
        Название алгоритма хеширования
    """
    # Алгоритм меняется каждые 10,000 блоков
    algorithms = ['sha3_256', 'blake2b', 'sha256']
    algorithm_index = (height // 10000) % len(algorithms)
    return algorithms[algorithm_index]


def calculate_block_reward(height: int) -> float:
    """
    Вычисляет награду за блок с учетом уменьшения и случайной вариации.
    
    Args:
        height: Высота блока
        
    Returns:
        Награда за блок в монетах
    """
    # Базовая награда, уменьшается вдвое каждые BLOCK_REWARD_HALF_LIFE блоков
    base_reward = 50 * (0.5 ** (height // BLOCK_REWARD_HALF_LIFE))
    
    # Добавляем случайную вариацию для защиты от атак селективного майнинга
    # и улучшения анонимности
    variation = random.uniform(-REWARD_VARIABILITY, REWARD_VARIABILITY)
    reward = base_reward * (1 + variation)
    
    return max(0.01, reward)  # Минимальная награда 0.01 монеты


def adjust_difficulty(blockchain: List[Dict[str, Any]], current_difficulty: int) -> int:
    """
    Корректирует сложность на основе времени создания последних блоков.
    
    Args:
        blockchain: Текущий блокчейн
        current_difficulty: Текущая сложность
        
    Returns:
        Новое значение сложности
    """
    if len(blockchain) < DIFFICULTY_ADJUSTMENT_INTERVAL:
        return current_difficulty
    
    # Рассчитываем, за какое время были созданы последние DIFFICULTY_ADJUSTMENT_INTERVAL блоков
    start_time = blockchain[-DIFFICULTY_ADJUSTMENT_INTERVAL]['timestamp']
    end_time = blockchain[-1]['timestamp']
    time_taken = end_time - start_time
    
    # Ожидаемое время
    expected_time = TARGET_BLOCK_TIME * (DIFFICULTY_ADJUSTMENT_INTERVAL - 1)
    
    # Рассчитываем корректировку, но ограничиваем максимальное изменение
    if time_taken < expected_time // 4:
        # Слишком быстро, увеличиваем сложность, но не более чем на MAX_DIFFICULTY_ADJUSTMENT%
        new_difficulty = min(current_difficulty + 1, 
                             math.ceil(current_difficulty * (1 + MAX_DIFFICULTY_ADJUSTMENT/100)))
    elif time_taken > expected_time * 4:
        # Слишком медленно, уменьшаем сложность, но не более чем на MAX_DIFFICULTY_ADJUSTMENT%
        new_difficulty = max(INITIAL_DIFFICULTY, 
                             math.floor(current_difficulty * (1 - MAX_DIFFICULTY_ADJUSTMENT/100)))
    else:
        # Корректировка с учетом отношения ожидаемого и фактического времени
        ratio = expected_time / max(1, time_taken)
        adjustment = math.log2(ratio)
        
        # Ограничиваем изменение
        if adjustment > 0:
            adjustment = min(adjustment, MAX_DIFFICULTY_ADJUSTMENT/100)
        else:
            adjustment = max(adjustment, -MAX_DIFFICULTY_ADJUSTMENT/100)
        
        new_difficulty = max(INITIAL_DIFFICULTY, 
                             current_difficulty + math.floor(current_difficulty * adjustment))
    
    # Логируем изменение сложности
    logger.info(f"Скорректирована сложность: {current_difficulty} -> {new_difficulty}, время создания блоков: {time_taken:.2f}s (ожидалось {expected_time:.2f}s)")
    
    return new_difficulty


def verify_block(block: Dict[str, Any], previous_block: Dict[str, Any], difficulty: int) -> bool:
    """
    Проверяет валидность блока.
    
    Args:
        block: Проверяемый блок
        previous_block: Предыдущий блок
        difficulty: Текущая сложность
        
    Returns:
        True, если блок валиден, иначе False
    """
    try:
        # Проверяем, что блок ссылается на предыдущий блок
        if block['previous_hash'] != previous_block['hash']:
            logger.warning(f"Неверный previous_hash в блоке {block['height']}")
            return False
        
        # Проверяем высоту блока
        if block['height'] != previous_block['height'] + 1:
            logger.warning(f"Неверная высота блока: {block['height']}, ожидается {previous_block['height'] + 1}")
            return False
        
        # Проверяем, что временная метка блока не в будущем
        current_time = time.time()
        if block['timestamp'] > current_time + MAX_FUTURE_BLOCK_TIME:
            logger.warning(f"Блок из будущего: {block['timestamp']} > {current_time + MAX_FUTURE_BLOCK_TIME}")
            return False
        
        # Проверяем, что временная метка не раньше предыдущего блока
        if block['timestamp'] < previous_block['timestamp']:
            logger.warning(f"Временная метка блока раньше предыдущего блока")
            return False
        
        # Проверяем корректность хеша блока
        block_data = block.copy()
        # Удаляем поле hash перед проверкой, так как оно не входит в хеширование
        if 'hash' in block_data:
            block_data.pop('hash')
        
        mining_algorithm = select_mining_algorithm(block['height'])
        calculated_hash = calculate_hash(block_data, block['nonce'], mining_algorithm)
        
        if calculated_hash != block['hash']:
            logger.warning(f"Неверный хеш блока: ожидается {calculated_hash}, получено {block['hash']}")
            return False
        
        # Проверяем, что хеш удовлетворяет требуемой сложности
        if not check_proof_of_work(block['hash'], difficulty):
            logger.warning(f"Хеш блока не соответствует сложности {difficulty}")
            return False
        
        # Проверяем корректную сумму награды за майнинг
        expected_reward = calculate_block_reward(block['height'])
        reward_diff = abs(block.get('mining_reward', 0) - expected_reward)
        
        if reward_diff > expected_reward * REWARD_VARIABILITY * 1.5:
            logger.warning(f"Награда за блок ({block.get('mining_reward')}) слишком отличается от ожидаемой ({expected_reward})")
            return False
        
        # Если дошли до этой точки, все проверки прошли успешно
        logger.info(f"Блок {block['height']} с хешем {block['hash']} успешно верифицирован")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при верификации блока: {str(e)}")
        return False


def add_uncle_blocks(blockchain: List[Dict[str, Any]], orphan_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Добавляет uncle-блоки к блокчейну для компенсации валидных майнеров и защиты от майнинговых пулов.
    
    Args:
        blockchain: Текущий блокчейн
        orphan_blocks: Список orphan-блоков
        
    Returns:
        Обновленный блокчейн
    """
    if not blockchain or not orphan_blocks:
        return blockchain
    
    current_height = blockchain[-1]['height']
    
    # Инициализируем список uncle-блоков в последнем блоке, если его нет
    if 'uncle_blocks' not in blockchain[-1]:
        blockchain[-1]['uncle_blocks'] = []
    
    # Фильтруем orphan-блоки, которые могут быть uncle-блоками
    for orphan in orphan_blocks[:]:
        # Uncle-блок должен быть валидным и его высота должна быть близка к текущей
        if (orphan['height'] <= current_height and 
            current_height - orphan['height'] <= UNCLE_BLOCKS_MAX_HEIGHT_DIFF and
            len(blockchain[-1]['uncle_blocks']) < UNCLE_BLOCKS_LIMIT):
            
            # Добавляем uncle-блок к последнему блоку
            uncle_block = {
                'hash': orphan['hash'],
                'height': orphan['height'],
                'miner': orphan.get('miner', 'unknown'),
                'timestamp': orphan['timestamp']
            }
            
            blockchain[-1]['uncle_blocks'].append(uncle_block)
            logger.info(f"Добавлен uncle-блок {uncle_block['hash']} на высоте {uncle_block['height']}")
            
            # Удаляем добавленный orphan-блок из списка
            orphan_blocks.remove(orphan)
    
    return blockchain


def hybrid_consensus_score(block: Dict[str, Any], stake_data: Dict[str, float]) -> float:
    """
    Вычисляет гибридный рейтинг блока, учитывая PoW и PoS компоненты.
    
    Args:
        block: Блок для оценки
        stake_data: Словарь с данными о стейках (адрес -> стейк)
        
    Returns:
        Общий рейтинг блока
    """
    # Получаем адрес майнера из блока
    miner_address = block.get('miner', '')
    
    # PoW компонент - обратно пропорционален хешу блока (меньше хеш - лучше)
    # Преобразуем хеш блока в число и нормализуем
    pow_component = 1.0
    if 'hash' in block:
        hash_int = int(block['hash'], 16)
        max_hash = int('f' * len(block['hash']), 16)
        pow_component = 1 - (hash_int / max_hash)
    
    # PoS компонент - пропорционален стейку майнера
    pos_component = 0.0
    if miner_address in stake_data:
        miner_stake = stake_data[miner_address]
        # Нормализуем стейк относительно максимального
        total_stake = sum(stake_data.values())
        pos_component = miner_stake / max(1, total_stake)
    
    # Комбинируем компоненты с весовыми коэффициентами
    combined_score = (1 - STAKE_WEIGHT_FACTOR) * pow_component + STAKE_WEIGHT_FACTOR * pos_component
    
    return combined_score


def update_node_reputation(node_id: str, is_valid_block: bool, block_height: int) -> None:
    """
    Обновляет репутацию узла сети на основе валидности его блоков.
    
    Args:
        node_id: Идентификатор узла
        is_valid_block: Является ли предложенный блок валидным
        block_height: Высота блока
    """
    # Применяем временное "забывание" репутации
    node_reputation[node_id] *= NODE_REPUTATION_DECAY
    
    # Если блок валидный, повышаем репутацию
    if is_valid_block:
        # Награда за валидный блок зависит от высоты (более новые блоки важнее)
        reputation_reward = 1.0 + math.log10(max(1, block_height))
        node_reputation[node_id] += reputation_reward
    else:
        # Штраф за невалидный блок
        node_reputation[node_id] -= 10.0
    
    # Проверяем, не достигла ли репутация порога для блокировки
    if node_reputation[node_id] < REPUTATION_THRESHOLD:
        logger.warning(f"Узел {node_id} был заблокирован из-за низкой репутации: {node_reputation[node_id]}")
        banned_nodes.add(node_id)


def select_fork(forks: List[List[Dict[str, Any]]], stake_data: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Выбирает форк для продолжения блокчейна на основе выбранного алгоритма.
    
    Args:
        forks: Список возможных форков
        stake_data: Данные о стейках
        
    Returns:
        Выбранный форк
    """
    if not forks:
        return []
    
    if len(forks) == 1:
        return forks[0]
    
    # Применяем выбранный алгоритм
    if FORK_CHOICE_ALGORITHM == "GHOST":
        # GHOST (Greedy Heaviest Observed SubTree) - учитывает uncle-блоки
        scores = []
        
        for fork in forks:
            # Подсчитываем общее количество uncle-блоков
            uncle_count = sum(len(block.get('uncle_blocks', [])) for block in fork)
            # Основной вес - длина цепи
            weight = len(fork)
            # Добавляем вес от uncle-блоков
            weight += uncle_count * 0.1
            scores.append(weight)
        
    elif FORK_CHOICE_ALGORITHM == "GHST":
        # GHST (Greedy Heaviest Staked Tree) - гибридный консенсус
        scores = []
        
        for fork in forks:
            # Считаем гибридный рейтинг для последнего блока в форке
            score = hybrid_consensus_score(fork[-1], stake_data) if fork else 0
            # Умножаем на длину форка
            score *= len(fork)
            scores.append(score)
    
    else:  # LCR (Longest Chain Rule) - по умолчанию
        # Простой выбор самой длинной цепи
        scores = [len(fork) for fork in forks]
    
    # Выбираем форк с наибольшим рейтингом
    best_fork_index = scores.index(max(scores))
    
    logger.info(f"Выбран форк {best_fork_index} с рейтингом {scores[best_fork_index]} (алгоритм: {FORK_CHOICE_ALGORITHM})")
    return forks[best_fork_index]


def validate_mempool(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Проверяет транзакции в мемпуле, отфильтровывая невалидные.
    
    Args:
        transactions: Список транзакций в мемпуле
        
    Returns:
        Список валидных транзакций
    """
    valid_transactions = []
    seen_txids = set()
    
    for tx in transactions:
        if not tx.get('txid'):
            logger.warning("Транзакция без txid отклонена")
            continue
        
        # Проверяем уникальность ID транзакции
        if tx['txid'] in seen_txids:
            logger.warning(f"Дублирующаяся транзакция {tx['txid']} отклонена")
            continue
        
        # Проверяем подпись транзакции
        if not tx.get('signature') or not tx.get('from'):
            logger.warning(f"Транзакция {tx['txid']} без подписи или отправителя отклонена")
            continue
        
        # Тут должна быть проверка подписи и балансов, но для упрощения опустим
        
        # Добавляем в список валидных транзакций
        valid_transactions.append(tx)
        seen_txids.add(tx['txid'])
        
        # Ограничиваем размер мемпула
        if len(valid_transactions) >= MEMPOOL_MAX_SIZE:
            logger.warning(f"Достигнут максимальный размер мемпула ({MEMPOOL_MAX_SIZE})")
            break
    
    return valid_transactions


def detect_suspicious_activity(blockchain: List[Dict[str, Any]], new_block: Dict[str, Any], node_id: str) -> bool:
    """
    Обнаруживает подозрительную активность по характеристикам блоков.
    
    Args:
        blockchain: Текущий блокчейн
        new_block: Новый блок
        node_id: ID узла, предложившего блок
        
    Returns:
        True, если обнаружена подозрительная активность
    """
    if not blockchain:
        return False
    
    # Запоминаем историю форков для узла
    fork_histories[node_id].append(new_block)
    if len(fork_histories[node_id]) > 100:
        fork_histories[node_id] = fork_histories[node_id][-100:]
    
    # Проверка на временное зацикливание (Eclipse атака)
    if 'timestamp' in new_block and 'timestamp' in blockchain[-1]:
        if abs(new_block['timestamp'] - blockchain[-1]['timestamp']) > TARGET_BLOCK_TIME * 10:
            logger.warning(f"Подозрительный временной разрыв для блока от узла {node_id}")
            return True
    
    # Проверка на селективную отправку блоков (атака Селфиш-майнинга)
    if len(fork_histories[node_id]) > 3:
        # Ищем паттерны селективного раскрытия блоков
        heights = [b.get('height', 0) for b in fork_histories[node_id]]
        if len(heights) >= 3:
            height_diffs = [heights[i+1] - heights[i] for i in range(len(heights)-1)]
            if max(height_diffs) > 3:  # Скрытое майнение нескольких блоков
                logger.warning(f"Обнаружена подозрительная последовательность блоков от узла {node_id}")
                return True
    
    # Проверка на рывок сложности (атака сложности)
    if 'difficulty' in new_block and len(blockchain) > DIFFICULTY_ADJUSTMENT_INTERVAL:
        avg_difficulty = sum(b.get('difficulty', 4) for b in blockchain[-DIFFICULTY_ADJUSTMENT_INTERVAL:]) / DIFFICULTY_ADJUSTMENT_INTERVAL
        if new_block['difficulty'] < avg_difficulty * 0.5:
            logger.warning(f"Подозрительное снижение сложности в блоке от узла {node_id}")
            return True
    
    return False


def is_node_banned(node_id: str) -> bool:
    """
    Проверяет, заблокирован ли узел.
    
    Args:
        node_id: Идентификатор узла
        
    Returns:
        True, если узел заблокирован
    """
    return node_id in banned_nodes


# Пример использования
if __name__ == "__main__":
    # Создаем тестовый блок
    block_data = {
        'height': 1,
        'previous_hash': '0' * 64,
        'transactions': [],
        'timestamp': time.time(),
        'miner': 'GRS_TestMiner'
    }
    
    # Устанавливаем сложность
    difficulty = 4
    
    # Майним блок
    nonce, block_hash = mine_block(block_data, difficulty)
    
    if nonce >= 0:
        block_data['nonce'] = nonce
        block_data['hash'] = block_hash
        
        # Проверяем блок
        genesis_block = {
            'height': 0,
            'hash': '0' * 64,
            'timestamp': time.time() - 100
        }
        
        is_valid = verify_block(block_data, genesis_block, difficulty)
        print(f"Блок валиден: {is_valid}")
        
        # Применяем гибридный консенсус
        stake_data = {
            'GRS_TestMiner': 100.0,
            'GRS_AnotherMiner': 200.0
        }
        
        score = hybrid_consensus_score(block_data, stake_data)
        print(f"Гибридный рейтинг блока: {score}")
    else:
        print("Не удалось смайнить блок") 