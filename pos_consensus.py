"""
Grishinium Blockchain - Proof of Stake Consensus Implementation
"""

import time
import random
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumPoS')

# Константы для PoS
MIN_STAKE_AMOUNT = 100  # Минимальное количество монет для стейкинга
STAKE_MATURITY_TIME = 86400  # Время созревания стейка (24 часа)
STAKE_LOCK_TIME = 604800  # Время блокировки стейка (7 дней)
TARGET_BLOCK_TIME = 15  # Целевое время блока в секундах
VALIDATOR_SET_SIZE = 100  # Размер набора валидаторов
STAKE_REWARD_RATE = 0.05  # Годовая ставка награды за стейкинг (5%)

class ProofOfStake:
    """Класс реализующий механизм консенсуса Proof of Stake."""
    
    def __init__(self):
        self.stakes: Dict[str, float] = {}  # Адрес -> количество застейканных монет
        self.stake_timestamps: Dict[str, float] = {}  # Адрес -> время стейкинга
        self.validators: Set[str] = set()  # Множество активных валидаторов
        self.block_timestamps: List[float] = []  # Временные метки последних блоков
        
    def stake(self, address: str, amount: float) -> bool:
        """
        Застейкать монеты для участия в консенсусе.
        
        Args:
            address: Адрес стейкера
            amount: Количество монет для стейкинга
            
        Returns:
            bool: Успешность операции
        """
        if amount < MIN_STAKE_AMOUNT:
            logger.warning(f"Stake amount {amount} is less than minimum required {MIN_STAKE_AMOUNT}")
            return False
            
        self.stakes[address] = amount
        self.stake_timestamps[address] = time.time()
        self._update_validators()
        return True
        
    def unstake(self, address: str) -> bool:
        """
        Вывести монеты из стейкинга.
        
        Args:
            address: Адрес стейкера
            
        Returns:
            bool: Успешность операции
        """
        if address not in self.stakes:
            return False
            
        stake_time = time.time() - self.stake_timestamps[address]
        if stake_time < STAKE_LOCK_TIME:
            logger.warning(f"Cannot unstake before lock time expires. Time left: {STAKE_LOCK_TIME - stake_time}")
            return False
            
        del self.stakes[address]
        del self.stake_timestamps[address]
        self._update_validators()
        return True
        
    def _update_validators(self) -> None:
        """Обновляет список валидаторов на основе размера стейка."""
        # Сортируем стейкеров по размеру стейка
        sorted_stakes = sorted(self.stakes.items(), key=lambda x: x[1], reverse=True)
        # Выбираем топ VALIDATOR_SET_SIZE валидаторов
        self.validators = {address for address, _ in sorted_stakes[:VALIDATOR_SET_SIZE]}
        
    def select_validator(self, seed: str) -> str:
        """
        Выбирает валидатора для создания следующего блока.
        
        Args:
            seed: Случайное значение для выбора
            
        Returns:
            str: Адрес выбранного валидатора
        """
        if not self.validators:
            raise ValueError("No validators available")
            
        # Используем seed для детерминированного выбора
        seed_hash = hashlib.sha256(seed.encode()).hexdigest()
        seed_int = int(seed_hash, 16)
        
        # Выбираем валидатора с вероятностью, пропорциональной размеру стейка
        total_stake = sum(self.stakes.values())
        if total_stake == 0:
            return random.choice(list(self.validators))
            
        r = seed_int % total_stake
        cumsum = 0
        for validator, stake in self.stakes.items():
            cumsum += stake
            if r < cumsum:
                return validator
                
        return list(self.validators)[-1]  # Fallback
        
    def calculate_block_reward(self, validator: str) -> float:
        """
        Рассчитывает награду за создание блока.
        
        Args:
            validator: Адрес валидатора
            
        Returns:
            float: Размер награды
        """
        if validator not in self.stakes:
            return 0.0
            
        stake_amount = self.stakes[validator]
        # Награда пропорциональна размеру стейка и времени
        reward = stake_amount * (STAKE_REWARD_RATE / (365 * 24 * 3600)) * TARGET_BLOCK_TIME
        return reward
        
    def verify_block(self, block: Dict[str, Any], previous_block: Dict[str, Any]) -> bool:
        """
        Проверяет валидность блока.
        
        Args:
            block: Проверяемый блок
            previous_block: Предыдущий блок
            
        Returns:
            bool: Валидность блока
        """
        # Проверяем временную метку
        if block['timestamp'] <= previous_block['timestamp']:
            return False
            
        # Проверяем, что создатель блока является валидатором
        if block['validator'] not in self.validators:
            return False
            
        # Проверяем, что валидатор был выбран корректно
        seed = previous_block['hash']
        expected_validator = self.select_validator(seed)
        if block['validator'] != expected_validator:
            return False
            
        return True
        
    def get_stake_info(self, address: str) -> Dict[str, Any]:
        """
        Получает информацию о стейке адреса.
        
        Args:
            address: Адрес для проверки
            
        Returns:
            Dict[str, Any]: Информация о стейке
        """
        if address not in self.stakes:
            return {
                'staked_amount': 0,
                'stake_time': 0,
                'is_validator': False,
                'can_unstake': False
            }
            
        stake_time = time.time() - self.stake_timestamps[address]
        return {
            'staked_amount': self.stakes[address],
            'stake_time': stake_time,
            'is_validator': address in self.validators,
            'can_unstake': stake_time >= STAKE_LOCK_TIME
        } 