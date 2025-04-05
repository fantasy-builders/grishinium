#!/bin/bash

# Проверяем наличие необходимых зависимостей
echo "Проверка зависимостей..."
pip3 install flask flask-cors cryptography requests > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Ошибка установки зависимостей. Убедитесь, что у вас установлен pip3."
    exit 1
fi

# Определяем директорию с данными
DATA_DIR="./data"
if [ ! -d "$DATA_DIR" ]; then
    echo "Создание директории для данных: $DATA_DIR"
    mkdir -p "$DATA_DIR"
fi

# Запускаем сервер кошелька
echo "Запуск сервера Grishinium Wallet..."
python3 wallet_server.py --data-dir="$DATA_DIR" --port=8080 