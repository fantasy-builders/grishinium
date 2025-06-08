#!/usr/bin/env python3
"""
Grishinium Blockchain - Скрипт для настройки директорий кошельков
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('setup_wallet_dirs')

def create_directory(path):
    """Создает директорию, если она не существует"""
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            logger.info(f"Создана директория: {path}")
        except Exception as e:
            logger.error(f"Ошибка при создании директории {path}: {str(e)}")
            return False
    else:
        logger.info(f"Директория уже существует: {path}")
    return True

def setup_wallet_directories():
    """Настраивает все необходимые директории для кошельков"""
    
    # Список всех директорий для кошельков
    wallet_dirs = [
        # Обычные кошельки
        "data/wallets",
        
        # Административные кошельки
        "admin/data",
        "admin/data/wallets",
        
        # Тестовые кошельки
        "testnet/wallets",
        
        # Токеновые кошельки (в домашней директории пользователя)
        os.path.expanduser("~/.grishinium/wallets")
    ]
    
    # Создаем каждую директорию
    success = True
    for directory in wallet_dirs:
        if not create_directory(directory):
            success = False
    
    return success

if __name__ == "__main__":
    logger.info("Начало настройки директорий для кошельков Grishinium Blockchain")
    
    if setup_wallet_directories():
        logger.info("Настройка директорий успешно завершена")
    else:
        logger.error("Произошли ошибки при настройке директорий")
        sys.exit(1) 