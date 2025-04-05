"""
Grishinium Blockchain - Main Entry Point
"""

import os
import sys
import time
import argparse
import logging
import signal
from typing import Dict, Any, List, Optional

# Импортируем модули блокчейна
from blockchain import Blockchain, Block
from crypto import generate_key_pair, get_address_from_public_key
from network import NodeNetwork
from pos_consensus import ProofOfStake
from storage import BlockchainStorage
import utils

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grishinium.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GrishiniumMain')


class GrishiniumNode:
    """Основной класс для управления узлом Grishinium."""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """
        Инициализация узла Grishinium.
        
        Args:
            config: Конфигурация узла
        """
        # Загружаем конфигурацию или используем значения по умолчанию
        self.config = config or {
            "data_dir": "data",
            "port": 5000,
            "min_stake_amount": 100,
            "stake_reward_rate": 0.05,
            "is_testnet": False
        }
        
        # Создаем директорию для данных, если она не существует
        os.makedirs(self.config["data_dir"], exist_ok=True)
        
        # Генерируем ключевую пару для узла
        self.private_key, self.public_key = generate_key_pair()
        self.address = get_address_from_public_key(self.public_key)
        
        # Инициализируем компоненты
        self.blockchain = Blockchain()
        self.storage = BlockchainStorage(self.config["data_dir"])
        
        # Загружаем состояние из хранилища
        self._load_state()
        
        # Инициализируем сетевой компонент
        NodeNetwork.initialize(
            blockchain=self.blockchain,
            port=self.config["port"],
            node_id=self.address
        )
        
        logger.info(f"Узел Grishinium инициализирован с адресом {self.address}")
        if self.config["is_testnet"]:
            logger.info("Узел работает в тестовой сети")
        
    def _load_state(self) -> None:
        """Загружает состояние блокчейна из хранилища."""
        try:
            saved_state = self.storage.load_state()
            if saved_state:
                self.blockchain = saved_state
                logger.info("Состояние блокчейна загружено из хранилища")
        except Exception as e:
            logger.error(f"Ошибка при загрузке состояния: {e}")
            
    def _save_state(self) -> None:
        """Сохраняет текущее состояние блокчейна."""
        try:
            self.storage.save_state(self.blockchain)
            logger.debug("Состояние блокчейна сохранено")
        except Exception as e:
            logger.error(f"Ошибка при сохранении состояния: {e}")
            
    def stake(self, amount: float) -> bool:
        """
        Застейкать монеты для участия в консенсусе.
        
        Args:
            amount: Количество монет для стейкинга
            
        Returns:
            bool: Успешность операции
        """
        if amount < self.config["min_stake_amount"]:
            logger.warning(f"Сумма стейкинга {amount} меньше минимальной {self.config['min_stake_amount']}")
            return False
            
        # Проверяем баланс
        balance = self.blockchain.get_balance(self.address)
        if balance < amount:
            logger.warning(f"Недостаточно средств для стейкинга. Баланс: {balance}, Требуется: {amount}")
            return False
            
        # Создаем транзакцию стейкинга
        stake_tx = {
            "from": self.address,
            "to": "staking_pool",
            "amount": amount,
            "timestamp": time.time(),
            "type": "stake"
        }
        
        # Добавляем транзакцию в новый блок
        new_block = Block(
            index=len(self.blockchain.chain),
            previous_hash=self.blockchain.get_latest_block().hash,
            timestamp=time.time(),
            transactions=[stake_tx],
            validator=self.address
        )
        
        if self.blockchain.add_block([stake_tx], self.address):
            self._save_state()
            logger.info(f"Успешно застейкано {amount} монет")
            return True
            
        return False
        
    def unstake(self) -> bool:
        """
        Вывести монеты из стейкинга.
        
        Returns:
            bool: Успешность операции
        """
        # Получаем информацию о стейке
        stake_info = self.blockchain.consensus.get_stake_info(self.address)
        if not stake_info["staked_amount"]:
            logger.warning("Нет активного стейка")
            return False
            
        if not stake_info["can_unstake"]:
            logger.warning("Стейк еще не созрел")
            return False
            
        # Создаем транзакцию анстейкинга
        unstake_tx = {
            "from": "staking_pool",
            "to": self.address,
            "amount": stake_info["staked_amount"],
            "timestamp": time.time(),
            "type": "unstake"
        }
        
        if self.blockchain.add_block([unstake_tx], self.address):
            self._save_state()
            logger.info(f"Успешно выведено {stake_info['staked_amount']} монет из стейкинга")
            return True
            
        return False
        
    def get_stake_info(self) -> Dict[str, Any]:
        """
        Получает информацию о текущем стейке.
        
        Returns:
            Dict[str, Any]: Информация о стейке
        """
        return self.blockchain.consensus.get_stake_info(self.address)
        
    def start(self) -> None:
        """Запускает узел."""
        try:
            # Основной цикл узла
            while True:
                # Проверяем, является ли узел валидатором
                if self.address in self.blockchain.consensus.validators:
                    # Собираем транзакции из сети
                    transactions = self.blockchain.pending_transactions
                    
                    # Создаем новый блок
                    if transactions:
                        if self.blockchain.add_block(transactions, self.address):
                            self._save_state()
                            # Отправляем новый блок в сеть
                            NodeNetwork.broadcast_block(self.blockchain.get_latest_block().to_dict())
                            
                time.sleep(1)  # Небольшая задержка для снижения нагрузки
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения работы")
        finally:
            self._save_state()
            NodeNetwork.shutdown()
            
    def stop(self) -> None:
        """Останавливает узел."""
        self._save_state()
        NodeNetwork.shutdown()
        logger.info("Узел остановлен")


def main():
    """Точка входа в программу."""
    parser = argparse.ArgumentParser(description="Grishinium Blockchain Node")
    parser.add_argument("--port", type=int, default=5000, help="Порт для сетевого взаимодействия")
    parser.add_argument("--data-dir", type=str, default="data", help="Директория для хранения данных")
    parser.add_argument("--testnet", action="store_true", help="Запуск в тестовой сети")
    args = parser.parse_args()
    
    config = {
        "port": args.port,
        "data_dir": args.data_dir,
        "is_testnet": args.testnet
    }
    
    # Если это тестнет, используем специальные параметры
    if args.testnet:
        config.update({
            "min_stake_amount": 10,
            "stake_reward_rate": 0.1
        })
    
    node = GrishiniumNode(config)
    
    def signal_handler(signum, frame):
        logger.info("Получен сигнал завершения работы")
        node.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        node.start()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        node.stop()
        sys.exit(1)


if __name__ == "__main__":
    main() 