#!/bin/bash
# Grishinium Blockchain - Скрипт запуска с проверкой директорий

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Grishinium Blockchain - Запуск системы ===${NC}"

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Ошибка: Python 3 не установлен${NC}"
    exit 1
fi

# Настройка директорий для кошельков
echo -e "${YELLOW}Проверка и создание директорий для кошельков...${NC}"
python3 setup_wallet_dirs.py

# Проверка результата
if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при настройке директорий для кошельков${NC}"
    exit 1
fi

echo -e "${GREEN}Директории для кошельков настроены успешно${NC}"

# Проверка наличия необходимых файлов
if [ ! -f "blockchain_server.py" ]; then
    echo -e "${RED}Ошибка: Файл blockchain_server.py не найден${NC}"
    exit 1
fi

if [ ! -f "wallet_server.py" ]; then
    echo -e "${RED}Ошибка: Файл wallet_server.py не найден${NC}"
    exit 1
fi

# Запуск компонентов блокчейна
echo -e "${YELLOW}Запуск блокчейн-сервера...${NC}"
python3 blockchain_server.py &
BLOCKCHAIN_PID=$!

echo -e "${YELLOW}Запуск сервера кошельков...${NC}"
python3 wallet_server.py &
WALLET_PID=$!

# Запуск веб-интерфейса, если он существует
if [ -f "web_interface.py" ]; then
    echo -e "${YELLOW}Запуск веб-интерфейса...${NC}"
    python3 web_interface.py &
    WEB_PID=$!
fi

# Функция для корректного завершения процессов
function cleanup {
    echo -e "${YELLOW}Завершение работы компонентов...${NC}"
    kill $BLOCKCHAIN_PID 2>/dev/null
    kill $WALLET_PID 2>/dev/null
    if [ ! -z "$WEB_PID" ]; then
        kill $WEB_PID 2>/dev/null
    fi
    echo -e "${GREEN}Завершение работы системы Grishinium Blockchain${NC}"
    exit 0
}

# Обработка сигналов завершения
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Система Grishinium Blockchain запущена${NC}"
echo -e "${YELLOW}Нажмите Ctrl+C для завершения работы${NC}"

# Ожидание завершения
wait 