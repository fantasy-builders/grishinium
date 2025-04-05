"""
Grishinium Blockchain - Голографическое разделение данных (HoloShard)

Этот модуль реализует инновационную систему хранения данных, где блоки 
разбиваются на "голограммы" - фрагменты, каждый из которых содержит
частичную информацию о всей цепочке. Для восстановления данных требуется
собрать критическое количество фрагментов с 90% или более узлов.
"""

import hashlib
import numpy as np
import json
import base64
import zlib
import random
import logging
import time
from typing import List, Dict, Any, Tuple, Set, Optional, Union
import crypto
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
from scipy.fft import fft, ifft

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumHoloShard')

# Константы для настройки HoloShard
SHARD_COUNT = 100  # Количество фрагментов, на которые разбивается блок
RECOVERY_THRESHOLD = 90  # Минимальный процент фрагментов для восстановления (90%)
MAX_SHARD_SIZE_BYTES = 1024 * 256  # Максимальный размер одного фрагмента (256 KB)
ENTROPY_FACTOR = 0.15  # Фактор энтропии для добавления "шума" (15%)
FFT_DATA_SIZE = 1024  # Размер данных для преобразования Фурье
HASH_ROUNDS = 3  # Количество раундов хеширования для повышения безопасности
RECONSTRUCTION_MAX_ATTEMPTS = 5  # Максимальное количество попыток реконструкции
VERIFICATION_REDUNDANCY = 3  # Избыточность проверки для снижения вероятности ложных восстановлений

# Ключи для шифрования, в реальной системе должны генерироваться для каждого узла
NODE_SECRET_SEEDS = {}  # node_id -> seed


class HoloShard:
    """Класс для работы с голографическими фрагментами блокчейна."""
    
    def __init__(self, blockchain_id: str, genesis_seed: str) -> None:
        """
        Инициализация с идентификатором блокчейна и начальным сидом.
        
        Args:
            blockchain_id: Уникальный идентификатор блокчейна
            genesis_seed: Начальное значение для генерации ключей шифрования
        """
        self.blockchain_id = blockchain_id
        self.genesis_seed = genesis_seed
        # Кэш для ускорения операций
        self._shard_cache = {}  # block_hash -> list of shards
        self._node_shard_mapping = {}  # node_id -> list of shard_ids
        self._current_epoch = int(time.time())  # Эпоха для генерации ключей
        
        logger.info(f"HoloShard инициализирован для блокчейна {blockchain_id}")

    def _generate_node_key(self, node_id: str, epoch: int = None) -> bytes:
        """
        Генерирует ключ шифрования для конкретного узла и эпохи.
        
        Args:
            node_id: Идентификатор узла
            epoch: Временная эпоха (если None, используется текущая)
            
        Returns:
            Ключ шифрования
        """
        if epoch is None:
            epoch = self._current_epoch
            
        # Получаем секретный сид узла или создаем новый
        if node_id not in NODE_SECRET_SEEDS:
            # В реальной системе сид должен быть согласован между узлами заранее
            # через безопасный канал, например, через PKI
            node_seed = f"{self.genesis_seed}_{node_id}_{random.randint(1, 1000000)}"
            NODE_SECRET_SEEDS[node_id] = node_seed
        else:
            node_seed = NODE_SECRET_SEEDS[node_id]
        
        # Создаем соль на основе эпохи и блокчейна
        salt = f"{self.blockchain_id}_{epoch}".encode()
        
        # Генерируем ключ из сида узла
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(node_seed.encode()))
        
        return key
    
    def _apply_holographic_transform(self, data: bytes) -> np.ndarray:
        """
        Применяет голографическое преобразование (FFT) к данным.
        
        Args:
            data: Исходные данные
            
        Returns:
            Преобразованные данные в виде массива numpy
        """
        # Преобразуем данные в массив чисел
        data_array = np.frombuffer(data, dtype=np.uint8)
        
        # Дополняем данные до нужной длины
        pad_size = (data_array.size // FFT_DATA_SIZE + 1) * FFT_DATA_SIZE - data_array.size
        padded_data = np.pad(data_array, (0, pad_size), 'constant')
        
        # Разбиваем на блоки по FFT_DATA_SIZE
        blocks = padded_data.reshape(-1, FFT_DATA_SIZE)
        
        # Применяем FFT к каждому блоку
        transformed_blocks = []
        for block in blocks:
            # Преобразуем в комплексные числа и применяем FFT
            complex_block = block.astype(np.complex128)
            transformed = fft(complex_block)
            transformed_blocks.append(transformed)
        
        # Объединяем блоки
        return np.concatenate(transformed_blocks)
    
    def _inverse_holographic_transform(self, transformed_data: np.ndarray, original_size: int) -> bytes:
        """
        Применяет обратное голографическое преобразование.
        
        Args:
            transformed_data: Преобразованные данные
            original_size: Исходный размер данных
            
        Returns:
            Восстановленные данные
        """
        # Разбиваем на блоки
        transformed_data = transformed_data.reshape(-1, FFT_DATA_SIZE)
        
        # Применяем обратное FFT
        inverse_blocks = []
        for block in transformed_data:
            inverse_transformed = ifft(block)
            # Преобразуем обратно в целые числа
            inverse_block = np.round(np.abs(inverse_transformed)).astype(np.uint8)
            inverse_blocks.append(inverse_block)
        
        # Объединяем блоки и восстанавливаем исходный размер
        restored_data = np.concatenate(inverse_blocks)[:original_size]
        
        return bytes(restored_data.astype(np.uint8))
    
    def _add_entropy_noise(self, data: np.ndarray) -> np.ndarray:
        """
        Добавляет энтропийный шум к данным для дополнительной защиты.
        
        Args:
            data: Исходные данные
            
        Returns:
            Данные с добавленным шумом
        """
        # Генерируем случайный шум
        noise = np.random.normal(0, ENTROPY_FACTOR * np.std(np.abs(data)), data.shape)
        # Применяем шум только к определенным компонентам (не к низкочастотным)
        mask = np.random.random(data.shape) > 0.7  # 30% компонентов получают шум
        noise_addition = noise * mask
        
        # Добавляем шум к данным
        return data + noise_addition * 1j if np.iscomplexobj(data) else data + noise_addition
    
    def _create_holographic_shards(self, block_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Создает голографические фрагменты из данных блока.
        
        Args:
            block_data: Данные блока
            
        Returns:
            Список голографических фрагментов
        """
        # Преобразуем блок в JSON строку
        serialized_data = json.dumps(block_data, sort_keys=True).encode()
        original_size = len(serialized_data)
        
        # Сжимаем данные
        compressed_data = zlib.compress(serialized_data)
        
        # Применяем голографическое преобразование
        holographic_data = self._apply_holographic_transform(compressed_data)
        
        # Создаем фрагменты
        shards = []
        shard_size = len(holographic_data) // SHARD_COUNT
        
        # Основные метаданные, общие для всех фрагментов
        metadata = {
            "block_hash": block_data.get("hash", ""),
            "block_height": block_data.get("height", 0),
            "timestamp": time.time(),
            "original_size": original_size,
            "compressed_size": len(compressed_data),
            "transform_type": "fft",
            "shard_count": SHARD_COUNT,
            "recovery_threshold": RECOVERY_THRESHOLD,
            "blockchain_id": self.blockchain_id,
            "epoch": self._current_epoch
        }
        
        for i in range(SHARD_COUNT):
            # Определяем индексы начала и конца фрагмента
            start_idx = i * shard_size
            end_idx = (i + 1) * shard_size if i < SHARD_COUNT - 1 else len(holographic_data)
            
            # Выделяем фрагмент данных
            shard_data = holographic_data[start_idx:end_idx].copy()
            
            # Добавляем энтропийный шум для дополнительной защиты
            shard_data_with_noise = self._add_entropy_noise(shard_data)
            
            # Сериализуем данные фрагмента
            real_part = shard_data_with_noise.real.tobytes()
            imag_part = shard_data_with_noise.imag.tobytes() if np.iscomplexobj(shard_data_with_noise) else b""
            
            # Создаем идентификатор фрагмента
            shard_id = hashlib.sha256(
                f"{metadata['block_hash']}_{i}_{metadata['timestamp']}".encode()
            ).hexdigest()
            
            # Формируем фрагмент
            shard = {
                "shard_id": shard_id,
                "index": i,
                "real_data": base64.b64encode(real_part).decode(),
                "imag_data": base64.b64encode(imag_part).decode() if imag_part else "",
                "metadata": metadata.copy(),
                "checksum": ""  # Будет заполнено далее
            }
            
            # Добавляем контрольную сумму
            shard_json = json.dumps(shard, sort_keys=True).encode()
            shard["checksum"] = hashlib.sha3_256(shard_json).hexdigest()
            
            shards.append(shard)
        
        # Кэшируем фрагменты
        self._shard_cache[metadata["block_hash"]] = shards
        
        logger.info(f"Создано {len(shards)} голографических фрагментов для блока {metadata['block_hash']}")
        return shards
    
    def distribute_shards(self, block_data: Dict[str, Any], nodes: List[str]) -> Dict[str, List[str]]:
        """
        Распределяет фрагменты по узлам сети.
        
        Args:
            block_data: Данные блока
            nodes: Список доступных узлов
            
        Returns:
            Словарь маппинга узлов к идентификаторам назначенных им фрагментов
        """
        if not nodes:
            logger.error("Нет доступных узлов для распределения фрагментов")
            return {}
        
        # Создаем голографические фрагменты
        shards = self._create_holographic_shards(block_data)
        
        # Распределяем фрагменты по узлам
        node_to_shards = {node_id: [] for node_id in nodes}
        
        # Обеспечиваем избыточность - каждый фрагмент должен быть как минимум на нескольких узлах
        redundancy_factor = max(3, len(nodes) // 10)  # Минимум 3 копии или 10% от узлов
        
        for shard in shards:
            # Выбираем случайные узлы для этого фрагмента
            selected_nodes = random.sample(nodes, min(redundancy_factor, len(nodes)))
            
            # Шифруем фрагмент для каждого узла его ключом
            for node_id in selected_nodes:
                # Получаем ключ узла
                node_key = self._generate_node_key(node_id)
                fernet = Fernet(node_key)
                
                # Шифруем данные фрагмента
                shard_json = json.dumps(shard, sort_keys=True).encode()
                encrypted_shard = fernet.encrypt(shard_json)
                
                # Сохраняем идентификатор фрагмента для этого узла
                node_to_shards[node_id].append(shard["shard_id"])
                
                # В реальной системе здесь бы происходила отправка зашифрованного фрагмента узлу
                logger.debug(f"Фрагмент {shard['shard_id']} назначен узлу {node_id}")
        
        # Обновляем маппинг узлов к фрагментам
        for node_id, shard_ids in node_to_shards.items():
            if node_id not in self._node_shard_mapping:
                self._node_shard_mapping[node_id] = set()
            self._node_shard_mapping[node_id].update(shard_ids)
        
        logger.info(f"Фрагменты блока {block_data.get('hash', '')} распределены между {len(nodes)} узлами")
        return {node_id: list(shards) for node_id, shards in node_to_shards.items()}
    
    def request_shards_from_nodes(self, block_hash: str, node_shards: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Запрашивает фрагменты от узлов для восстановления блока.
        
        Args:
            block_hash: Хеш блока
            node_shards: Словарь {node_id: [shard_ids]}
            
        Returns:
            Список расшифрованных фрагментов
        """
        # В реальной системе здесь бы происходил сетевой запрос к узлам
        # Для демонстрации используем кэшированные фрагменты
        
        if block_hash not in self._shard_cache:
            logger.error(f"Фрагменты для блока {block_hash} не найдены в кэше")
            return []
        
        all_shards = self._shard_cache[block_hash]
        recovered_shards = []
        
        for node_id, shard_ids in node_shards.items():
            # Получаем ключ узла
            node_key = self._generate_node_key(node_id)
            fernet = Fernet(node_key)
            
            for shard_id in shard_ids:
                # Находим фрагмент в кэше
                shard = next((s for s in all_shards if s["shard_id"] == shard_id), None)
                if not shard:
                    continue
                
                try:
                    # В реальной системе здесь бы происходила расшифровка полученного от узла фрагмента
                    # Для демонстрации просто используем оригинальный фрагмент
                    recovered_shards.append(shard)
                except Exception as e:
                    logger.warning(f"Не удалось расшифровать фрагмент {shard_id} от узла {node_id}: {str(e)}")
        
        # Проверяем, достаточно ли собрано фрагментов
        required_shards = (RECOVERY_THRESHOLD * SHARD_COUNT) // 100
        
        if len(recovered_shards) < required_shards:
            logger.error(f"Недостаточно фрагментов для восстановления блока {block_hash}. "
                         f"Получено {len(recovered_shards)}, требуется {required_shards}")
            return []
        
        logger.info(f"Получено {len(recovered_shards)} фрагментов для восстановления блока {block_hash}")
        return recovered_shards
    
    def _sort_and_validate_shards(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Сортирует и проверяет целостность фрагментов.
        
        Args:
            shards: Список фрагментов
            
        Returns:
            Отсортированный и проверенный список фрагментов
        """
        valid_shards = []
        
        for shard in shards:
            # Проверяем контрольную сумму
            shard_copy = shard.copy()
            checksum = shard_copy.pop("checksum")
            shard_json = json.dumps(shard_copy, sort_keys=True).encode()
            calculated_checksum = hashlib.sha3_256(shard_json).hexdigest()
            
            if calculated_checksum != checksum:
                logger.warning(f"Фрагмент {shard['shard_id']} не прошел проверку контрольной суммы")
                continue
            
            valid_shards.append(shard)
        
        # Сортируем по индексу
        valid_shards.sort(key=lambda x: x["index"])
        
        return valid_shards
    
    def reconstruct_block(self, shards: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Восстанавливает блок из голографических фрагментов.
        
        Args:
            shards: Список фрагментов
            
        Returns:
            Восстановленный блок или None, если восстановление не удалось
        """
        if not shards:
            logger.error("Нет фрагментов для восстановления блока")
            return None
        
        # Сортируем и проверяем фрагменты
        valid_shards = self._sort_and_validate_shards(shards)
        
        if not valid_shards:
            logger.error("Нет валидных фрагментов для восстановления")
            return None
        
        # Проверяем, что все фрагменты относятся к одному блоку
        block_hash = valid_shards[0]["metadata"]["block_hash"]
        if not all(shard["metadata"]["block_hash"] == block_hash for shard in valid_shards):
            logger.error("Фрагменты относятся к разным блокам")
            return None
        
        # Извлекаем метаданные
        metadata = valid_shards[0]["metadata"]
        
        # Проверяем, достаточно ли фрагментов
        required_shards = (metadata["recovery_threshold"] * metadata["shard_count"]) // 100
        if len(valid_shards) < required_shards:
            logger.error(f"Недостаточно фрагментов для восстановления. "
                         f"Есть {len(valid_shards)}, нужно {required_shards}")
            return None
        
        # Готовим массив для объединения данных
        combined_data_size = 0
        for shard in valid_shards:
            real_data = base64.b64decode(shard["real_data"])
            combined_data_size += len(real_data) // 8  # размер в комплексных числах
        
        combined_data = np.zeros(combined_data_size, dtype=np.complex128)
        
        # Объединяем данные фрагментов
        position = 0
        for shard in valid_shards:
            real_data = np.frombuffer(base64.b64decode(shard["real_data"]), dtype=np.float64)
            imag_data = np.frombuffer(base64.b64decode(shard["imag_data"]), dtype=np.float64) if shard["imag_data"] else np.zeros_like(real_data)
            
            # Преобразуем в комплексные числа
            complex_data = real_data + 1j * imag_data
            shard_size = len(complex_data)
            
            # Добавляем данные в общий массив
            if position + shard_size <= len(combined_data):
                combined_data[position:position+shard_size] = complex_data
            else:
                # Обрезаем, если выходим за границы
                overflow = (position + shard_size) - len(combined_data)
                combined_data[position:] = complex_data[:-overflow]
            
            position += shard_size
            # Если достигли конца, прерываем
            if position >= len(combined_data):
                break
        
        # Применяем обратное голографическое преобразование
        try:
            restored_data = self._inverse_holographic_transform(combined_data, metadata["compressed_size"])
            # Распаковываем данные
            decompressed_data = zlib.decompress(restored_data)
            # Десериализуем в словарь
            block_data = json.loads(decompressed_data)
            
            logger.info(f"Блок {block_hash} успешно восстановлен из {len(valid_shards)} фрагментов")
            return block_data
            
        except Exception as e:
            logger.error(f"Ошибка при восстановлении блока: {str(e)}")
            return None
    
    def recover_block(self, block_hash: str, nodes: List[str]) -> Optional[Dict[str, Any]]:
        """
        Полный процесс восстановления блока.
        
        Args:
            block_hash: Хеш блока
            nodes: Список доступных узлов
            
        Returns:
            Восстановленный блок или None
        """
        # Определяем, у каких узлов есть фрагменты для этого блока
        node_has_shards = {}
        for node_id in nodes:
            if node_id in self._node_shard_mapping:
                node_shards = [sid for sid in self._node_shard_mapping[node_id] 
                               if sid.startswith(block_hash[:8])]
                if node_shards:
                    node_has_shards[node_id] = node_shards
        
        # Если не нашли узлов с фрагментами, пробуем запросить у всех
        if not node_has_shards:
            logger.warning(f"Нет информации о том, у каких узлов есть фрагменты для блока {block_hash}")
            # В реальной системе здесь бы происходил broadcast запрос ко всем узлам
            # Для демонстрации просто берем случайные узлы
            selected_nodes = random.sample(nodes, min(len(nodes), SHARD_COUNT // 2))
            node_has_shards = {node_id: [] for node_id in selected_nodes}
        
        # Запрашиваем фрагменты
        shards = self.request_shards_from_nodes(block_hash, node_has_shards)
        
        # Восстанавливаем блок
        for attempt in range(RECONSTRUCTION_MAX_ATTEMPTS):
            # Если у нас достаточно фрагментов, пробуем восстановить
            if len(shards) >= (RECOVERY_THRESHOLD * SHARD_COUNT) // 100:
                block = self.reconstruct_block(shards)
                if block:
                    return block
            
            # Если не удалось, запрашиваем больше фрагментов
            logger.warning(f"Попытка {attempt+1} восстановления не удалась, запрашиваем больше фрагментов")
            
            # Добавляем случайные узлы к запросу
            additional_nodes = [n for n in nodes if n not in node_has_shards]
            if additional_nodes:
                selected_nodes = random.sample(additional_nodes, min(len(additional_nodes), 5))
                for node_id in selected_nodes:
                    node_has_shards[node_id] = []
            
            # Запрашиваем больше фрагментов
            new_shards = self.request_shards_from_nodes(block_hash, {n: [] for n in node_has_shards if n not in node_has_shards})
            shards.extend(new_shards)
        
        logger.error(f"Не удалось восстановить блок {block_hash} после {RECONSTRUCTION_MAX_ATTEMPTS} попыток")
        return None
    
    def verify_block_authenticity(self, block_data: Dict[str, Any]) -> bool:
        """
        Проверяет аутентичность восстановленного блока.
        
        Args:
            block_data: Данные блока
            
        Returns:
            True, если блок аутентичный
        """
        # В реальной системе здесь бы происходила проверка подписей, Merkle-доказательств и т.д.
        # Для демонстрации просто проверяем хеш блока
        
        if "hash" not in block_data:
            logger.error("Блок не содержит хеш")
            return False
        
        # Вычисляем хеш блока
        block_copy = block_data.copy()
        block_hash = block_copy.pop("hash")
        
        # Проверяем несколько алгоритмов хеширования для надежности
        for algorithm in ["sha3_256", "blake2b", "sha256"]:
            calculated_hash = crypto.hash_data(block_copy, algorithm)
            if calculated_hash == block_hash:
                logger.info(f"Блок {block_hash} прошел проверку аутентичности")
                return True
        
        logger.warning(f"Блок {block_hash} не прошел проверку аутентичности")
        return False
    
    def rebalance_shards(self, nodes: List[str]) -> Dict[str, Set[str]]:
        """
        Перераспределяет фрагменты между узлами для обеспечения оптимального распределения.
        
        Args:
            nodes: Список активных узлов
            
        Returns:
            Словарь с назначениями фрагментов узлам
        """
        # Собираем все уникальные фрагменты
        all_shards = set()
        for shards in self._node_shard_mapping.values():
            all_shards.update(shards)
        
        # Проверяем текущее распределение
        shard_distribution = {shard_id: set() for shard_id in all_shards}
        for node_id, shards in self._node_shard_mapping.items():
            if node_id in nodes:  # Учитываем только активные узлы
                for shard_id in shards:
                    shard_distribution[shard_id].add(node_id)
        
        # Определяем минимальное количество копий для каждого фрагмента
        target_redundancy = max(3, len(nodes) // 10)
        
        # Репликация недостаточно распределенных фрагментов
        shards_to_replicate = {}
        for shard_id, current_nodes in shard_distribution.items():
            if len(current_nodes) < target_redundancy:
                # Находим узлы, на которых нет этого фрагмента
                available_nodes = [n for n in nodes if n not in current_nodes]
                
                if available_nodes:
                    # Выбираем случайные узлы для репликации
                    nodes_to_add = random.sample(available_nodes, 
                                                min(target_redundancy - len(current_nodes), 
                                                    len(available_nodes)))
                    
                    for node_id in nodes_to_add:
                        if node_id not in shards_to_replicate:
                            shards_to_replicate[node_id] = set()
                        shards_to_replicate[node_id].add(shard_id)
        
        # Применяем изменения к маппингу
        for node_id, shards in shards_to_replicate.items():
            if node_id not in self._node_shard_mapping:
                self._node_shard_mapping[node_id] = set()
            self._node_shard_mapping[node_id].update(shards)
        
        logger.info(f"Перераспределено {sum(len(s) for s in shards_to_replicate.values())} фрагментов между {len(shards_to_replicate)} узлами")
        return shards_to_replicate


# Пример использования
if __name__ == "__main__":
    # Создаем экземпляр HoloShard
    holoshard = HoloShard("grishinium_mainnet", "initial_security_seed_v1")
    
    # Тестовый блок
    test_block = {
        "hash": "7a1f8b5c4d2e9f3a6b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2",
        "height": 1000,
        "previous_hash": "0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
        "timestamp": time.time(),
        "transactions": [
            {
                "txid": "tx1",
                "from": "GRS_WalletA",
                "to": "GRS_WalletB",
                "amount": 10.5
            },
            {
                "txid": "tx2",
                "from": "GRS_WalletC",
                "to": "GRS_WalletD",
                "amount": 25.0
            }
        ],
        "nonce": 12345,
        "difficulty": 5
    }
    
    # Список тестовых узлов
    test_nodes = [f"node_{i}" for i in range(20)]
    
    # Распределяем фрагменты
    print("Распределение фрагментов по узлам...")
    node_shard_mapping = holoshard.distribute_shards(test_block, test_nodes)
    
    # Восстанавливаем блок
    print("\nВосстановление блока из фрагментов...")
    # Предположим, что нам доступны только 15 из 20 узлов
    available_nodes = test_nodes[:15]
    reconstructed_block = holoshard.recover_block(test_block["hash"], available_nodes)
    
    if reconstructed_block:
        print(f"Блок успешно восстановлен! Высота: {reconstructed_block['height']}")
        print(f"Транзакции: {len(reconstructed_block['transactions'])}")
        
        # Проверяем аутентичность
        is_authentic = holoshard.verify_block_authenticity(reconstructed_block)
        print(f"Блок аутентичен: {is_authentic}")
    else:
        print("Не удалось восстановить блок")
    
    # Перераспределение фрагментов
    print("\nПерераспределение фрагментов для оптимизации...")
    # Предположим, что некоторые узлы вышли из строя
    active_nodes = test_nodes[5:] + [f"new_node_{i}" for i in range(3)]
    rebalanced = holoshard.rebalance_shards(active_nodes)
    print(f"Перераспределено {sum(len(s) for s in rebalanced.values())} фрагментов") 