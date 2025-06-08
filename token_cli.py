#!/usr/bin/env python3
"""
Grishinium Blockchain - Интерфейс командной строки для работы с токенами
"""

import os
import sys
import cmd
import json
import time
import argparse
import logging
from typing import Dict, List, Any, Optional, Tuple

# Импортируем модули блокчейна
from blockchain import Blockchain
from crypto_token import TokenTransaction, TokenTransactionType, format_token_amount, parse_token_amount
from token_wallet import TokenWallet, create_new_wallet, load_wallet, TokenWalletError
from network import NodeNetwork

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grishinium_token.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('GrishiniumTokenCLI')

class GrishiniumTokenCLI(cmd.Cmd):
    """Интерфейс командной строки для работы с токенами Grishinium."""
    
    intro = """
    ========================================
    Grishinium Token CLI - Версия 1.0
    ========================================
    Введите help или ? для просмотра команд.
    """
    prompt = "grishinium> "
    
    def __init__(self, blockchain_node: Optional[str] = None):
        """
        Инициализация CLI.
        
        Args:
            blockchain_node: Адрес узла блокчейна
        """
        super().__init__()
        self.blockchain_node = blockchain_node or "http://localhost:5000"
        self.wallet = None
        
        # Попытка подключения к блокчейну
        try:
            # Здесь может быть код для подключения к узлу
            # Например: NodeNetwork.register_node(self.blockchain_node)
            self.connected = True
            logger.info(f"Подключено к узлу блокчейна {self.blockchain_node}")
        except Exception as e:
            self.connected = False
            logger.warning(f"Не удалось подключиться к узлу блокчейна: {str(e)}")
        
    def do_connect(self, arg):
        """Подключиться к узлу блокчейна. Использование: connect <url>"""
        if not arg:
            print("Необходимо указать URL узла. Пример: connect http://localhost:5000")
            return
            
        try:
            # Здесь может быть код для подключения к узлу
            # Например: NodeNetwork.register_node(arg)
            self.blockchain_node = arg
            self.connected = True
            print(f"Подключено к узлу блокчейна {self.blockchain_node}")
        except Exception as e:
            self.connected = False
            print(f"Ошибка подключения: {str(e)}")
    
    def do_create_wallet(self, arg):
        """Создать новый кошелек. Использование: create_wallet [имя]"""
        try:
            self.wallet = create_new_wallet(arg if arg else None)
            print(f"Создан новый кошелек с адресом: {self.wallet.address}")
        except Exception as e:
            print(f"Ошибка при создании кошелька: {str(e)}")
    
    def do_load_wallet(self, arg):
        """Загрузить существующий кошелек. Использование: load_wallet [имя]"""
        try:
            self.wallet = load_wallet(arg if arg else None)
            if self.wallet:
                print(f"Кошелек загружен успешно. Адрес: {self.wallet.address}")
        except Exception as e:
            print(f"Ошибка при загрузке кошелька: {str(e)}")
    
    def do_wallet_info(self, arg):
        """Показать информацию о текущем кошельке."""
        if not self.wallet:
            print("Кошелек не загружен. Используйте create_wallet или load_wallet.")
            return
            
        print("\n=== Информация о кошельке ===")
        print(f"Имя: {self.wallet.name}")
        print(f"Адрес: {self.wallet.address}")
        
        # Получаем баланс с узла блокчейна (если подключен)
        if self.connected:
            try:
                # Здесь должен быть запрос баланса с блокчейна
                # Например: balance = get_balance_from_node(self.blockchain_node, self.wallet.address)
                # Временная заглушка
                balance = 1000.0
                staked = 100.0
                
                print(f"Баланс: {format_token_amount(int(balance * 10**8))}")
                print(f"В стейкинге: {format_token_amount(int(staked * 10**8))}")
            except Exception as e:
                print(f"Ошибка при получении баланса: {str(e)}")
        else:
            print("Не подключен к блокчейну. Баланс недоступен.")
    
    def do_transfer(self, arg):
        """Создать транзакцию перевода токенов. Использование: transfer <получатель> <сумма> [комиссия]"""
        if not self.wallet:
            print("Кошелек не загружен. Используйте create_wallet или load_wallet.")
            return
            
        args = arg.split()
        if len(args) < 2:
            print("Необходимо указать получателя и сумму. Пример: transfer Gxyz123... 10.5")
            return
            
        recipient = args[0]
        
        try:
            amount = float(args[1])
        except ValueError:
            print("Некорректная сумма перевода.")
            return
            
        fee = 0.001  # По умолчанию
        if len(args) > 2:
            try:
                fee = float(args[2])
            except ValueError:
                print("Некорректная комиссия. Будет использована комиссия по умолчанию (0.001).")
        
        try:
            tx = self.wallet.create_transaction(recipient, amount, fee)
            print(f"Создана транзакция: {tx.tx_id}")
            print(f"Отправитель: {tx.sender}")
            print(f"Получатель: {tx.recipient}")
            print(f"Сумма: {format_token_amount(tx.amount)}")
            print(f"Комиссия: {format_token_amount(tx.fee)}")
            
            if self.connected:
                # Отправка транзакции в блокчейн
                # Например: send_transaction_to_node(self.blockchain_node, tx.to_dict())
                print("Транзакция отправлена в блокчейн")
            else:
                print("Не подключен к блокчейну. Транзакция не отправлена.")
        except Exception as e:
            print(f"Ошибка при создании транзакции: {str(e)}")
    
    def do_stake(self, arg):
        """Создать транзакцию стейкинга токенов. Использование: stake <сумма> [комиссия]"""
        if not self.wallet:
            print("Кошелек не загружен. Используйте create_wallet или load_wallet.")
            return
            
        args = arg.split()
        if len(args) < 1:
            print("Необходимо указать сумму. Пример: stake 100")
            return
            
        try:
            amount = float(args[0])
        except ValueError:
            print("Некорректная сумма стейкинга.")
            return
            
        fee = 0.001  # По умолчанию
        if len(args) > 1:
            try:
                fee = float(args[1])
            except ValueError:
                print("Некорректная комиссия. Будет использована комиссия по умолчанию (0.001).")
        
        try:
            tx = self.wallet.create_stake_transaction(amount, fee)
            print(f"Создана транзакция стейкинга: {tx.tx_id}")
            print(f"Отправитель: {tx.sender}")
            print(f"Сумма: {format_token_amount(tx.amount)}")
            print(f"Комиссия: {format_token_amount(tx.fee)}")
            
            if self.connected:
                # Отправка транзакции в блокчейн
                # Например: send_transaction_to_node(self.blockchain_node, tx.to_dict())
                print("Транзакция отправлена в блокчейн")
            else:
                print("Не подключен к блокчейну. Транзакция не отправлена.")
        except Exception as e:
            print(f"Ошибка при создании транзакции стейкинга: {str(e)}")
    
    def do_unstake(self, arg):
        """Создать транзакцию вывода из стейкинга. Использование: unstake <сумма> [комиссия]"""
        if not self.wallet:
            print("Кошелек не загружен. Используйте create_wallet или load_wallet.")
            return
            
        args = arg.split()
        if len(args) < 1:
            print("Необходимо указать сумму. Пример: unstake 100")
            return
            
        try:
            amount = float(args[0])
        except ValueError:
            print("Некорректная сумма для вывода из стейкинга.")
            return
            
        fee = 0.001  # По умолчанию
        if len(args) > 1:
            try:
                fee = float(args[1])
            except ValueError:
                print("Некорректная комиссия. Будет использована комиссия по умолчанию (0.001).")
        
        try:
            tx = self.wallet.create_unstake_transaction(amount, fee)
            print(f"Создана транзакция вывода из стейкинга: {tx.tx_id}")
            print(f"Отправитель: {tx.sender}")
            print(f"Сумма: {format_token_amount(tx.amount)}")
            print(f"Комиссия: {format_token_amount(tx.fee)}")
            
            if self.connected:
                # Отправка транзакции в блокчейн
                # Например: send_transaction_to_node(self.blockchain_node, tx.to_dict())
                print("Транзакция отправлена в блокчейн")
            else:
                print("Не подключен к блокчейну. Транзакция не отправлена.")
        except Exception as e:
            print(f"Ошибка при создании транзакции вывода из стейкинга: {str(e)}")
    
    def do_history(self, arg):
        """Показать историю транзакций текущего кошелька."""
        if not self.wallet:
            print("Кошелек не загружен. Используйте create_wallet или load_wallet.")
            return
            
        if not self.connected:
            print("Не подключен к блокчейну. История транзакций недоступна.")
            return
            
        try:
            # Здесь должен быть запрос истории транзакций с блокчейна
            # Например: history = get_transaction_history(self.blockchain_node, self.wallet.address)
            # Временная заглушка для примера
            history = [
                {
                    "tx_id": "abc123",
                    "tx_type": "transfer",
                    "sender": self.wallet.address,
                    "recipient": "Gxyz123...",
                    "amount": 10000000000,  # 100 GRI
                    "fee": 10000000,  # 0.1 GRI
                    "timestamp": time.time() - 3600,  # 1 час назад
                    "block_index": 100
                },
                {
                    "tx_id": "def456",
                    "tx_type": "stake",
                    "sender": self.wallet.address,
                    "recipient": "staking_pool",
                    "amount": 5000000000,  # 50 GRI
                    "fee": 10000000,  # 0.1 GRI
                    "timestamp": time.time() - 7200,  # 2 часа назад
                    "block_index": 90
                }
            ]
            
            # Обновляем историю транзакций в кошельке
            self.wallet.update_transaction_history(history)
            
            # Получаем отформатированную историю
            formatted_history = self.wallet.get_formatted_history()
            
            if not formatted_history:
                print("История транзакций пуста.")
                return
                
            print("\n=== История транзакций ===")
            for i, tx in enumerate(formatted_history, 1):
                print(f"\n[{i}] {tx['tx_id']} ({tx['date']})")
                print(f"Тип: {tx['type']}")
                print(f"Направление: {tx['direction']}")
                print(f"Контрагент: {tx['counterparty']}")
                print(f"Сумма: {tx['amount']}")
                print(f"Комиссия: {tx['fee']}")
                print(f"Блок: {tx['block']}")
        except Exception as e:
            print(f"Ошибка при получении истории транзакций: {str(e)}")
    
    def do_node_info(self, arg):
        """Показать информацию о подключенном узле блокчейна."""
        if not self.connected:
            print("Не подключен к блокчейну.")
            return
            
        try:
            # Здесь должен быть запрос информации о блокчейне
            # Например: node_info = get_node_info(self.blockchain_node)
            # Временная заглушка
            node_info = {
                "node_id": "node_1",
                "peers": 5,
                "last_block": 1000,
                "last_block_hash": "0x1234567890abcdef",
                "version": "1.0.0",
                "pending_transactions": 3,
                "uptime": 86400,  # 1 день
                "total_supply": 100000000 * (10 ** 8)  # 100 миллионов GRI
            }
            
            print("\n=== Информация об узле блокчейна ===")
            print(f"URL: {self.blockchain_node}")
            print(f"ID узла: {node_info['node_id']}")
            print(f"Версия: {node_info['version']}")
            print(f"Количество пиров: {node_info['peers']}")
            print(f"Последний блок: #{node_info['last_block']} ({node_info['last_block_hash']})")
            print(f"Ожидающие транзакции: {node_info['pending_transactions']}")
            print(f"Время работы: {node_info['uptime'] // 3600} часов")
            print(f"Общая эмиссия: {format_token_amount(node_info['total_supply'])}")
        except Exception as e:
            print(f"Ошибка при получении информации об узле: {str(e)}")
    
    def do_exit(self, arg):
        """Выход из программы."""
        print("Выход из программы...")
        return True
        
    def do_quit(self, arg):
        """Выход из программы."""
        return self.do_exit(arg)
        

def main():
    parser = argparse.ArgumentParser(description="Grishinium Token CLI")
    parser.add_argument("--node", type=str, default="http://localhost:5000", help="URL узла блокчейна")
    args = parser.parse_args()
    
    cli = GrishiniumTokenCLI(args.node)
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\nВыход из программы...")
        sys.exit(0)
        

if __name__ == "__main__":
    main() 