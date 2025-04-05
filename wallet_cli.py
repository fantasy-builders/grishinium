#!/usr/bin/env python3
"""
Grishinium Wallet CLI - Интерфейс командной строки для работы с кошельками Grishinium
"""

import os
import sys
import json
import getpass
import argparse
import requests
from typing import Optional, Dict, Any

# Импортируем модуль кошелька
from wallet import GrishiniumWallet, create_new_wallet, load_existing_wallet
from wallet import InvalidSeedError, InvalidPasswordError, WalletExistsError, WalletNotFoundError

class GrishiniumWalletCLI:
    """Интерфейс командной строки для работы с кошельками Grishinium."""
    
    def __init__(self):
        """Инициализация CLI."""
        self.wallet = None
        self.node_url = "http://localhost:5000"  # URL ноды по умолчанию
    
    def set_node_url(self, url: str) -> None:
        """Устанавливает URL для взаимодействия с нодой."""
        self.node_url = url
    
    def get_balance(self, address: str) -> float:
        """
        Получает баланс адреса с ноды.
        
        Args:
            address: Адрес кошелька.
            
        Returns:
            float: Баланс адреса.
        """
        try:
            response = requests.get(f"{self.node_url}/api/balance/{address}", timeout=5)
            if response.status_code == 200:
                return response.json().get("balance", 0)
            else:
                print(f"Ошибка при получении баланса: {response.text}")
                return 0
        except Exception as e:
            print(f"Ошибка при подключении к ноде: {str(e)}")
            return 0
    
    def send_transaction(self, transaction: Dict[str, Any]) -> bool:
        """
        Отправляет транзакцию на ноду.
        
        Args:
            transaction: Данные транзакции.
            
        Returns:
            bool: True, если транзакция успешно отправлена.
        """
        try:
            response = requests.post(
                f"{self.node_url}/api/transaction",
                json=transaction,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                print("Транзакция успешно отправлена!")
                print(f"ID транзакции: {response.json().get('transaction_id')}")
                return True
            else:
                print(f"Ошибка при отправке транзакции: {response.text}")
                return False
        except Exception as e:
            print(f"Ошибка при подключении к ноде: {str(e)}")
            return False
    
    def get_pending_transactions(self, address: Optional[str] = None) -> list:
        """
        Получает список ожидающих транзакций.
        
        Args:
            address: Фильтр по адресу (опционально).
            
        Returns:
            list: Список ожидающих транзакций.
        """
        try:
            url = f"{self.node_url}/api/pending-transactions"
            if address:
                url += f"?address={address}"
                
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json().get("transactions", [])
            else:
                print(f"Ошибка при получении списка транзакций: {response.text}")
                return []
        except Exception as e:
            print(f"Ошибка при подключении к ноде: {str(e)}")
            return []
    
    def get_transaction_history(self, address: str) -> list:
        """
        Получает историю транзакций для адреса.
        
        Args:
            address: Адрес кошелька.
            
        Returns:
            list: История транзакций.
        """
        try:
            response = requests.get(f"{self.node_url}/api/transactions/{address}", timeout=5)
            
            if response.status_code == 200:
                return response.json().get("transactions", [])
            else:
                print(f"Ошибка при получении истории транзакций: {response.text}")
                return []
        except Exception as e:
            print(f"Ошибка при подключении к ноде: {str(e)}")
            return []
    
    def create_wallet(self, wallet_name: Optional[str] = None) -> None:
        """
        Создает новый кошелек.
        
        Args:
            wallet_name: Имя кошелька.
        """
        password = getpass.getpass("Введите пароль для нового кошелька: ")
        password_confirm = getpass.getpass("Подтвердите пароль: ")
        
        if password != password_confirm:
            print("Пароли не совпадают!")
            return
        
        try:
            address, seed_phrase = create_new_wallet(password, wallet_name)
            
            if address:
                self.wallet = load_existing_wallet(seed_phrase, password, wallet_name)
                print("\nДля доступа к кошельку в будущем, используйте seed-фразу и пароль.")
        except WalletExistsError:
            print(f"Кошелек с именем {wallet_name or 'default_wallet'} уже существует!")
    
    def load_wallet(self, wallet_name: Optional[str] = None) -> None:
        """
        Загружает существующий кошелек.
        
        Args:
            wallet_name: Имя кошелька.
        """
        seed_phrase = input("Введите вашу seed-фразу (12 слов): ")
        password = getpass.getpass("Введите пароль от кошелька: ")
        
        try:
            self.wallet = load_existing_wallet(seed_phrase, password, wallet_name)
        except (InvalidSeedError, InvalidPasswordError, WalletNotFoundError) as e:
            print(f"Ошибка при загрузке кошелька: {str(e)}")
    
    def display_wallet_info(self) -> None:
        """Отображает информацию о текущем кошельке."""
        if not self.wallet:
            print("Кошелек не загружен!")
            return
        
        address = self.wallet.get_address()
        balance = self.get_balance(address)
        
        print("\n===== Информация о кошельке =====")
        print(f"Адрес: {address}")
        print(f"Баланс: {balance} GRS")
        print("================================\n")
    
    def display_transaction_history(self) -> None:
        """Отображает историю транзакций текущего кошелька."""
        if not self.wallet:
            print("Кошелек не загружен!")
            return
        
        address = self.wallet.get_address()
        transactions = self.get_transaction_history(address)
        
        if not transactions:
            print("История транзакций пуста.")
            return
        
        print("\n===== История транзакций =====")
        for i, tx in enumerate(transactions, 1):
            print(f"Транзакция #{i}:")
            print(f"  ID: {tx.get('id', 'Неизвестно')}")
            print(f"  Блок: {tx.get('block_index', 'Ожидает')}")
            print(f"  От: {tx.get('sender')}")
            print(f"  Кому: {tx.get('recipient')}")
            print(f"  Сумма: {tx.get('amount')} GRS")
            print(f"  Комиссия: {tx.get('fee')} GRS")
            print(f"  Статус: {'Подтверждена' if tx.get('confirmed', False) else 'Не подтверждена'}")
            print("-----------------------------")
        print("===============================\n")
    
    def send_coins(self) -> None:
        """Отправляет монеты с текущего кошелька."""
        if not self.wallet:
            print("Кошелек не загружен!")
            return
        
        recipient = input("Введите адрес получателя: ")
        
        # Проверка формата адреса
        if not recipient.startswith("GRS_"):
            print("Неверный формат адреса получателя! Адрес должен начинаться с 'GRS_'")
            return
        
        try:
            amount = float(input("Введите сумму для отправки: "))
            if amount <= 0:
                print("Сумма должна быть положительной!")
                return
                
            fee = float(input("Введите комиссию (по умолчанию 0.001): ") or "0.001")
            if fee < 0:
                print("Комиссия не может быть отрицательной!")
                return
        except ValueError:
            print("Введите корректное значение суммы!")
            return
        
        # Проверка баланса
        balance = self.get_balance(self.wallet.get_address())
        if balance < amount + fee:
            print(f"Недостаточно средств! Баланс: {balance} GRS, Требуется: {amount + fee} GRS")
            return
        
        # Создаем и отправляем транзакцию
        transaction = self.wallet.create_transaction(recipient, amount, fee)
        self.send_transaction(transaction)
    
    def stake_coins(self) -> None:
        """Интерактивный процесс стейкинга монет."""
        if not self.wallet:
            print("Сначала загрузите или создайте кошелек")
            return
            
        try:
            # Получаем текущий баланс
            balance = self.get_balance(self.wallet.get_address())
            print(f"\nТекущий баланс: {balance} GRS")
            
            # Запрашиваем сумму для стейкинга
            while True:
                try:
                    amount = float(input("\nВведите сумму для стейкинга: "))
                    if amount <= 0:
                        print("Сумма должна быть положительной")
                        continue
                    if amount < 100:
                        print("Минимальная сумма для стейкинга: 100 GRS")
                        continue
                    if amount > balance:
                        print("Недостаточно средств")
                        continue
                    break
                except ValueError:
                    print("Пожалуйста, введите корректное число")
                    
            # Запрашиваем комиссию
            while True:
                try:
                    fee = float(input("Введите комиссию за транзакцию (по умолчанию 0.001): ") or "0.001")
                    if fee <= 0:
                        print("Комиссия должна быть положительной")
                        continue
                    break
                except ValueError:
                    print("Пожалуйста, введите корректное число")
                    
            # Создаем транзакцию стейкинга
            transaction = self.wallet.create_stake_transaction(amount, fee)
            
            # Отправляем транзакцию
            if self.send_transaction(transaction):
                print(f"\nУспешно застейкано {amount} GRS")
            else:
                print("\nОшибка при отправке транзакции стейкинга")
                
        except Exception as e:
            print(f"\nОшибка при стейкинге: {str(e)}")
            
    def unstake_coins(self) -> None:
        """Интерактивный процесс вывода монет из стейкинга."""
        if not self.wallet:
            print("Сначала загрузите или создайте кошелек")
            return
            
        try:
            # Получаем информацию о стейке
            stake_info = self.wallet.get_stake_info()
            
            if not stake_info["staked_amount"]:
                print("\nУ вас нет активного стейка")
                return
                
            print(f"\nТекущий стейк: {stake_info['staked_amount']} GRS")
            print(f"Время в стейке: {stake_info['stake_time'] / 3600:.2f} часов")
            
            if not stake_info["can_unstake"]:
                print("\nСтейк еще не созрел. Необходимо подождать 7 дней.")
                return
                
            # Запрашиваем подтверждение
            confirm = input("\nВы уверены, что хотите вывести монеты из стейкинга? (y/n): ")
            if confirm.lower() != 'y':
                print("Операция отменена")
                return
                
            # Запрашиваем комиссию
            while True:
                try:
                    fee = float(input("Введите комиссию за транзакцию (по умолчанию 0.001): ") or "0.001")
                    if fee <= 0:
                        print("Комиссия должна быть положительной")
                        continue
                    break
                except ValueError:
                    print("Пожалуйста, введите корректное число")
                    
            # Создаем транзакцию анстейкинга
            transaction = self.wallet.create_unstake_transaction(fee)
            
            # Отправляем транзакцию
            if self.send_transaction(transaction):
                print(f"\nУспешно выведено {stake_info['staked_amount']} GRS из стейкинга")
            else:
                print("\nОшибка при отправке транзакции анстейкинга")
                
        except Exception as e:
            print(f"\nОшибка при выводе из стейкинга: {str(e)}")
            
    def display_stake_info(self) -> None:
        """Отображает информацию о текущем стейке."""
        if not self.wallet:
            print("Сначала загрузите или создайте кошелек")
            return
            
        try:
            stake_info = self.wallet.get_stake_info()
            validator_status = self.wallet.get_validator_status()
            rewards = self.wallet.get_stake_rewards()
            
            print("\n=== Информация о стейке ===")
            print(f"Застейкано: {stake_info['staked_amount']} GRS")
            print(f"Время в стейке: {stake_info['stake_time'] / 3600:.2f} часов")
            print(f"Статус валидатора: {'Да' if validator_status['is_validator'] else 'Нет'}")
            print(f"Можно вывести: {'Да' if stake_info['can_unstake'] else 'Нет'}")
            print(f"Накопленные награды: {rewards} GRS")
            
        except Exception as e:
            print(f"\nОшибка при получении информации о стейке: {str(e)}")
            
    def claim_stake_rewards(self) -> None:
        """Интерактивный процесс получения наград за стейкинг."""
        if not self.wallet:
            print("Сначала загрузите или создайте кошелек")
            return
            
        try:
            rewards = self.wallet.get_stake_rewards()
            
            if rewards <= 0:
                print("\nНет доступных наград для получения")
                return
                
            print(f"\nДоступные награды: {rewards} GRS")
            
            # Запрашиваем подтверждение
            confirm = input("\nПолучить награды? (y/n): ")
            if confirm.lower() != 'y':
                print("Операция отменена")
                return
                
            # Запрашиваем комиссию
            while True:
                try:
                    fee = float(input("Введите комиссию за транзакцию (по умолчанию 0.001): ") or "0.001")
                    if fee <= 0:
                        print("Комиссия должна быть положительной")
                        continue
                    break
                except ValueError:
                    print("Пожалуйста, введите корректное число")
                    
            # Создаем транзакцию получения наград
            transaction = self.wallet.claim_stake_rewards(fee)
            
            # Отправляем транзакцию
            if self.send_transaction(transaction):
                print(f"\nУспешно получено {rewards} GRS наград")
            else:
                print("\nОшибка при отправке транзакции получения наград")
                
        except Exception as e:
            print(f"\nОшибка при получении наград: {str(e)}")
            
    def run_interactive(self) -> None:
        """Запускает интерактивный режим CLI."""
        while True:
            print("\n=== Grishinium Wallet CLI ===")
            print("1. Создать новый кошелек")
            print("2. Загрузить существующий кошелек")
            print("3. Показать информацию о кошельке")
            print("4. Показать историю транзакций")
            print("5. Отправить монеты")
            print("6. Застейкать монеты")
            print("7. Вывести монеты из стейкинга")
            print("8. Показать информацию о стейке")
            print("9. Получить награды за стейкинг")
            print("0. Выход")
            
            choice = input("\nВыберите действие: ")
            
            if choice == "1":
                self.create_wallet()
            elif choice == "2":
                self.load_wallet()
            elif choice == "3":
                self.display_wallet_info()
            elif choice == "4":
                self.display_transaction_history()
            elif choice == "5":
                self.send_coins()
            elif choice == "6":
                self.stake_coins()
            elif choice == "7":
                self.unstake_coins()
            elif choice == "8":
                self.display_stake_info()
            elif choice == "9":
                self.claim_stake_rewards()
            elif choice == "0":
                print("\nЗавершение работы...")
                break
            else:
                print("\nНеверный выбор. Попробуйте снова.")

def main():
    """Основная функция для запуска CLI."""
    parser = argparse.ArgumentParser(description='Grishinium Wallet CLI')
    
    # Общие аргументы
    parser.add_argument('--node', type=str, default='http://localhost:5000',
                      help='URL ноды Grishinium (по умолчанию: http://localhost:5000)')
    
    # Подкоманды
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    # Команда create (создать кошелек)
    create_parser = subparsers.add_parser('create', help='Создать новый кошелек')
    create_parser.add_argument('--name', type=str, help='Имя кошелька')
    
    # Команда load (загрузить кошелек)
    load_parser = subparsers.add_parser('load', help='Загрузить существующий кошелек')
    load_parser.add_argument('--name', type=str, help='Имя кошелька')
    load_parser.add_argument('--seed', type=str, help='Seed-фраза (если не указана, будет запрошена интерактивно)')
    
    # Команда info (информация о кошельке)
    info_parser = subparsers.add_parser('info', help='Показать информацию о кошельке')
    info_parser.add_argument('--address', type=str, help='Адрес кошелька (если не загружен кошелек)')
    
    # Команда send (отправить монеты)
    send_parser = subparsers.add_parser('send', help='Отправить монеты')
    send_parser.add_argument('--to', type=str, required=True, help='Адрес получателя')
    send_parser.add_argument('--amount', type=float, required=True, help='Сумма для отправки')
    send_parser.add_argument('--fee', type=float, default=0.001, help='Комиссия за транзакцию (по умолчанию: 0.001)')
    
    # Команда history (история транзакций)
    history_parser = subparsers.add_parser('history', help='Показать историю транзакций')
    history_parser.add_argument('--address', type=str, help='Адрес кошелька (если не загружен кошелек)')
    
    args = parser.parse_args()
    
    # Создаем экземпляр CLI
    cli = GrishiniumWalletCLI()
    cli.set_node_url(args.node)
    
    # Если команда не указана, запускаем интерактивный режим
    if not args.command:
        cli.run_interactive()
        return
    
    # Обрабатываем команды
    if args.command == 'create':
        cli.create_wallet(args.name)
    
    elif args.command == 'load':
        if args.seed:
            password = getpass.getpass("Введите пароль от кошелька: ")
            cli.wallet = load_existing_wallet(args.seed, password, args.name)
        else:
            cli.load_wallet(args.name)
    
    elif args.command == 'info':
        if args.address:
            balance = cli.get_balance(args.address)
            print(f"Адрес: {args.address}")
            print(f"Баланс: {balance} GRS")
        elif cli.wallet:
            cli.display_wallet_info()
        else:
            print("Ошибка: Кошелек не загружен и адрес не указан!")
    
    elif args.command == 'send':
        if not cli.wallet:
            print("Ошибка: Кошелек не загружен!")
            return
        
        try:
            transaction = cli.wallet.create_transaction(args.to, args.amount, args.fee)
            cli.send_transaction(transaction)
        except Exception as e:
            print(f"Ошибка при создании транзакции: {str(e)}")
    
    elif args.command == 'history':
        if args.address:
            transactions = cli.get_transaction_history(args.address)
            if not transactions:
                print(f"История транзакций для адреса {args.address} пуста.")
            else:
                print(f"\nИстория транзакций для адреса {args.address}:")
                for i, tx in enumerate(transactions, 1):
                    print(f"{i}. {tx.get('id', 'ID неизвестен')} | Сумма: {tx.get('amount')} GRS | Статус: {'Подтверждена' if tx.get('confirmed', False) else 'Не подтверждена'}")
        elif cli.wallet:
            cli.display_transaction_history()
        else:
            print("Ошибка: Кошелек не загружен и адрес не указан!")

if __name__ == "__main__":
    main() 