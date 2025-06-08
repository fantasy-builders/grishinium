#!/usr/bin/env python3
"""
Grishinium Testnet Runner
"""

import os
import sys
import time
import subprocess
import signal
import logging
from typing import List, Dict
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("testnet.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GrishiniumTestnet')

class TestnetRunner:
    def __init__(self, num_nodes: int = 3):
        """
        Инициализация тестнета.
        
        Args:
            num_nodes: Количество нод в тестнете
        """
        self.num_nodes = num_nodes
        self.nodes: List[subprocess.Popen] = []
        self.base_port = 6000
        self.data_dir = os.path.join(os.path.dirname(__file__), "nodes")
        
        # Создаем директории для нод
        os.makedirs(self.data_dir, exist_ok=True)
        
    def start_nodes(self) -> None:
        """Запускает все ноды тестнета."""
        logger.info(f"Запуск {self.num_nodes} нод тестнета...")
        
        for i in range(self.num_nodes):
            node_dir = os.path.join(self.data_dir, f"node_{i}")
            os.makedirs(node_dir, exist_ok=True)
            
            port = self.base_port + i
            config = {
                "data_dir": node_dir,
                "port": port,
                "min_stake_amount": 10,  # Уменьшаем для тестнета
                "stake_reward_rate": 0.1  # Увеличиваем для тестнета
            }
            
            # Сохраняем конфигурацию
            config_file = os.path.join(node_dir, "config.json")
            with open(config_file, "w") as f:
                json.dump(config, f, indent=4)
            
            # Создаем файл для логов ноды
            log_file = os.path.join(node_dir, "node.log")
            node_log = open(log_file, "w")
            
            # Запускаем ноду
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py"),
                "--port", str(port),
                "--data-dir", node_dir,
                "--testnet"
            ]
            
            # Запускаем процесс ноды с перехватом вывода
            process = subprocess.Popen(
                cmd,
                stdout=node_log,
                stderr=node_log,
                universal_newlines=True
            )
            
            self.nodes.append({
                "process": process,
                "log_file": node_log,
                "port": port,
                "dir": node_dir
            })
            logger.info(f"Запущена нода {i} на порту {port}")
            
            # Небольшая задержка между запусками
            time.sleep(2)
            
    def stop_nodes(self) -> None:
        """Останавливает все ноды тестнета."""
        logger.info("Остановка нод тестнета...")
        
        for i, node in enumerate(self.nodes):
            try:
                node["process"].send_signal(signal.SIGINT)
                node["process"].wait(timeout=5)
                node["log_file"].close()
                logger.info(f"Нода {i} остановлена")
            except subprocess.TimeoutExpired:
                node["process"].kill()
                node["log_file"].close()
                logger.warning(f"Нода {i} принудительно остановлена")
                
    def monitor_nodes(self) -> None:
        """Мониторит состояние нод."""
        try:
            while True:
                for i, node in enumerate(self.nodes):
                    if node["process"].poll() is not None:
                        logger.error(f"Нода {i} завершилась с кодом {node['process'].returncode}")
                        # Читаем последние строки лога
                        with open(os.path.join(node["dir"], "node.log"), "r") as f:
                            log_tail = f.readlines()[-10:]
                            logger.error(f"Последние строки лога ноды {i}:")
                            for line in log_tail:
                                logger.error(line.strip())
                        # Перезапускаем упавшую ноду
                        self.restart_node(i)
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения работы")
            self.stop_nodes()
            
    def restart_node(self, node_index: int) -> None:
        """
        Перезапускает упавшую ноду.
        
        Args:
            node_index: Индекс ноды для перезапуска
        """
        node = self.nodes[node_index]
        node_dir = node["dir"]
        port = node["port"]
        
        # Закрываем старый файл лога
        node["log_file"].close()
        
        # Создаем новый файл для логов
        log_file = open(os.path.join(node_dir, "node.log"), "w")
        
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py"),
            "--port", str(port),
            "--data-dir", node_dir,
            "--testnet"
        ]
        
        # Запускаем процесс ноды с перехватом вывода
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            universal_newlines=True
        )
        
        self.nodes[node_index] = {
            "process": process,
            "log_file": log_file,
            "port": port,
            "dir": node_dir
        }
        logger.info(f"Нода {node_index} перезапущена на порту {port}")

def main():
    """Основная функция для запуска тестнета."""
    # Создаем экземпляр тестнета с 3 нодами
    testnet = TestnetRunner(num_nodes=3)
    
    def signal_handler(signum, frame):
        logger.info("Получен сигнал завершения работы")
        testnet.stop_nodes()
        sys.exit(0)
        
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запускаем ноды
        testnet.start_nodes()
        
        # Запускаем мониторинг
        testnet.monitor_nodes()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        testnet.stop_nodes()
        sys.exit(1)

if __name__ == "__main__":
    main() 