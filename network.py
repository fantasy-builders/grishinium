"""
Grishinium Blockchain - Network Communication Module
"""

import json
import socket
import threading
import time
import logging
import requests
from typing import List, Dict, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GrishiniumNetwork')


class NodeServer(BaseHTTPRequestHandler):
    """HTTP сервер для обработки запросов от других узлов сети."""
    
    # Ссылка на экземпляр блокчейна будет установлена при инициализации
    blockchain = None
    
    # Обработчики сообщений
    message_handlers = {}
    
    def _set_response(self, status_code=200, content_type='application/json'):
        """Устанавливает заголовки ответа."""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('X-Node-ID', NodeNetwork.node_id)
        self.end_headers()
    
    def _get_sender_node_id(self):
        """Получает идентификатор узла из заголовков запроса."""
        return self.headers.get('X-Node-ID', 'unknown')
    
    def _get_content_length(self):
        """Получает длину тела запроса."""
        try:
            return int(self.headers.get('Content-Length', 0))
        except (ValueError, TypeError):
            return 0
    
    def _read_json_body(self):
        """Читает и парсит JSON из тела запроса."""
        try:
            content_length = self._get_content_length()
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                return json.loads(post_data.decode())
            return {}
        except json.JSONDecodeError:
            logger.error("Ошибка декодирования JSON")
            return {}
        except Exception as e:
            logger.error(f"Ошибка чтения тела запроса: {str(e)}")
            return {}
    
    def do_GET(self):
        """Обрабатывает GET запросы."""
        # Получаем идентификатор отправителя
        sender_node_id = self._get_sender_node_id()
        
        if self.path == '/ping':
            # Простой пинг для проверки доступности узла
            self._set_response()
            response = {
                'status': 'ok', 
                'timestamp': time.time(),
                'node_id': NodeNetwork.node_id
            }
            self.wfile.write(json.dumps(response).encode())
            logger.debug(f"Получен пинг от {sender_node_id}")
        elif self.path == '/blocks':
            # Возвращает все блоки
            self._set_response()
            blocks = [block.to_dict() for block in NodeServer.blockchain.chain]
            self.wfile.write(json.dumps({'blocks': blocks}).encode())
            logger.debug(f"Отправлен список блоков узлу {sender_node_id}")
        elif self.path == '/pending':
            # Возвращает ожидающие транзакции
            self._set_response()
            self.wfile.write(json.dumps({'transactions': NodeServer.blockchain.pending_transactions}).encode())
            logger.debug(f"Отправлен список ожидающих транзакций узлу {sender_node_id}")
        elif self.path.startswith('/block/'):
            # Возвращает конкретный блок по хешу
            block_hash = self.path.split('/')[-1]
            found = False
            
            for block in NodeServer.blockchain.chain:
                if block.hash == block_hash:
                    self._set_response()
                    self.wfile.write(json.dumps({'block': block.to_dict()}).encode())
                    found = True
                    logger.debug(f"Отправлен блок {block_hash} узлу {sender_node_id}")
                    break
            
            if not found:
                self._set_response(404)
                self.wfile.write(json.dumps({'error': 'Block not found'}).encode())
                logger.warning(f"Запрошенный блок {block_hash} не найден (запрос от {sender_node_id})")
        else:
            # Неизвестный путь
            self._set_response(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
            logger.warning(f"Неизвестный GET запрос: {self.path} от {sender_node_id}")
    
    def do_POST(self):
        """Обрабатывает POST запросы."""
        # Получаем идентификатор отправителя
        sender_node_id = self._get_sender_node_id()
        
        # Читаем тело запроса
        post_data = self._read_json_body()
        
        if self.path == '/transaction':
            # Добавляет новую транзакцию
            if 'transaction' in post_data:
                transaction = post_data['transaction']
                # Здесь должна быть валидация транзакции
                
                # Добавляем транзакцию в список ожидающих
                NodeServer.blockchain.pending_transactions.append(transaction)
                
                self._set_response()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                logger.info(f"Получена новая транзакция от {sender_node_id}")
            else:
                self._set_response(400)
                self.wfile.write(json.dumps({'error': 'Missing transaction data'}).encode())
                logger.warning(f"Получен POST /transaction без данных от {sender_node_id}")
        elif self.path == '/block':
            # Получает новый блок
            if 'block' in post_data:
                block_data = post_data['block']
                
                # Здесь должна быть валидация блока
                
                # Обновляем базу данных
                # В реальной системе здесь нужно проверять блок и решать, добавлять его в цепь или нет
                
                self._set_response()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                logger.info(f"Получен новый блок от {sender_node_id}")
            else:
                self._set_response(400)
                self.wfile.write(json.dumps({'error': 'Missing block data'}).encode())
                logger.warning(f"Получен POST /block без данных от {sender_node_id}")
        elif self.path == '/message':
            # Обработка произвольных сообщений
            if 'type' in post_data and 'data' in post_data:
                message_type = post_data['type']
                message_data = post_data['data']
                
                # Проверяем, есть ли обработчик для этого типа сообщений
                if message_type in NodeServer.message_handlers:
                    try:
                        # Вызываем обработчик
                        response = NodeServer.message_handlers[message_type](message_data)
                        
                        # Отправляем ответ
                        self._set_response()
                        self.wfile.write(json.dumps(response).encode())
                        logger.debug(f"Обработано сообщение типа {message_type} от {sender_node_id}")
                    except Exception as e:
                        self._set_response(500)
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                        logger.error(f"Ошибка при обработке сообщения {message_type}: {str(e)}")
                else:
                    self._set_response(400)
                    self.wfile.write(json.dumps({'error': f'Unknown message type: {message_type}'}).encode())
                    logger.warning(f"Получено сообщение неизвестного типа {message_type} от {sender_node_id}")
            else:
                self._set_response(400)
                self.wfile.write(json.dumps({'error': 'Invalid message format'}).encode())
                logger.warning(f"Получено сообщение в неверном формате от {sender_node_id}")
        else:
            # Неизвестный путь
            self._set_response(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
            logger.warning(f"Неизвестный POST запрос: {self.path} от {sender_node_id}")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Многопоточный HTTP сервер"""
    allow_reuse_address = True


class NodeNetwork:
    """Управляет сетевым взаимодействием между узлами блокчейна."""
    
    # Список известных узлов сети
    nodes = set()
    
    # Ссылка на экземпляр блокчейна
    blockchain = None
    
    # HTTP сервер
    server = None
    
    # Флаг работы сервера
    running = False
    
    # Идентификатор этого узла
    node_id = None
    
    # Информация о других узлах: node_url -> {node_id, last_seen, version, ...}
    node_info = {}
    
    @classmethod
    def initialize(cls, blockchain, port: int = 5000, node_id: str = None) -> None:
        """
        Инициализирует сетевой модуль.
        
        Args:
            blockchain: Экземпляр блокчейна
            port: Порт для HTTP сервера
            node_id: Уникальный идентификатор узла
        """
        cls.blockchain = blockchain
        cls.running = True
        cls.node_id = node_id or "unknown"
        
        # Устанавливаем ссылку на блокчейн для HTTP сервера
        NodeServer.blockchain = blockchain
        
        # Запускаем HTTP сервер
        cls.server = ThreadedHTTPServer(('0.0.0.0', port), NodeServer)
        
        server_thread = threading.Thread(target=cls.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        logger.info(f"Сетевой модуль инициализирован, HTTP сервер запущен на порту {port}")
        
        # Запускаем фоновую задачу для синхронизации
        sync_thread = threading.Thread(target=cls._sync_loop)
        sync_thread.daemon = True
        sync_thread.start()
        
        # Регистрируем обработчик для пинга
        cls.register_message_handler("ping", cls.handle_ping)
        
        logger.info("Фоновая синхронизация запущена")
    
    @classmethod
    def shutdown(cls) -> None:
        """Останавливает сетевой модуль."""
        cls.running = False
        if cls.server:
            cls.server.shutdown()
            logger.info("Сервер остановлен")
    
    @classmethod
    def register_node(cls, node_url: str) -> None:
        """
        Добавляет узел в список известных узлов.
        
        Args:
            node_url: URL узла в формате http://hostname:port
        """
        if node_url not in cls.nodes:
            cls.nodes.add(node_url)
            logger.info(f"Узел {node_url} добавлен в список известных узлов")
            
            # Отправляем пинг для получения информации об узле
            cls.send_message(node_url, "ping", {"node_id": cls.node_id})
    
    @classmethod
    def broadcast_transaction(cls, transaction: Dict[str, Any]) -> int:
        """
        Рассылает транзакцию всем известным узлам.
        
        Args:
            transaction: Транзакция
            
        Returns:
            Количество узлов, получивших транзакцию
        """
        successful_nodes = 0
        
        for node in cls.nodes:
            try:
                response = requests.post(
                    f"{node}/transaction",
                    json={"transaction": transaction},
                    headers={"X-Node-ID": cls.node_id},
                    timeout=5
                )
                
                if response.status_code == 200:
                    successful_nodes += 1
                    logger.debug(f"Транзакция успешно отправлена узлу {node}")
                else:
                    logger.warning(f"Ошибка при отправке транзакции узлу {node}: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при отправке транзакции узлу {node}: {str(e)}")
        
        logger.info(f"Транзакция разослана {successful_nodes} из {len(cls.nodes)} узлов")
        return successful_nodes
    
    @classmethod
    def broadcast_block(cls, block: Dict[str, Any]) -> int:
        """
        Рассылает блок всем известным узлам.
        
        Args:
            block: Блок
            
        Returns:
            Количество узлов, получивших блок
        """
        successful_nodes = 0
        
        for node in cls.nodes:
            try:
                response = requests.post(
                    f"{node}/block",
                    json={"block": block},
                    headers={"X-Node-ID": cls.node_id},
                    timeout=5
                )
                
                if response.status_code == 200:
                    successful_nodes += 1
                    logger.debug(f"Блок успешно отправлен узлу {node}")
                else:
                    logger.warning(f"Ошибка при отправке блока узлу {node}: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при отправке блока узлу {node}: {str(e)}")
        
        logger.info(f"Блок разослан {successful_nodes} из {len(cls.nodes)} узлов")
        return successful_nodes
    
    @classmethod
    def consensus(cls) -> bool:
        """
        Реализует алгоритм консенсуса.
        Запрашивает цепочки блоков у всех узлов и заменяет локальную цепь, 
        если найдена более длинная валидная цепь.
        
        Returns:
            True, если наша цепь была заменена, иначе False
        """
        longest_chain = None
        max_length = len(cls.blockchain.chain)
        
        # Опрашиваем все узлы
        for node in cls.nodes:
            try:
                response = requests.get(f"{node}/blocks", timeout=5)
                if response.status_code == 200:
                    node_data = response.json()
                    if 'blocks' in node_data:
                        node_chain = node_data['blocks']
                        node_length = len(node_chain)
                        
                        # Проверяем, является ли цепь длиннее и валидной
                        # Здесь должна быть полноценная проверка валидности цепи
                        # В данном примере это упрощено
                        if node_length > max_length:
                            max_length = node_length
                            longest_chain = node_chain
            except requests.RequestException as e:
                logger.warning(f"Error connecting to node {node}: {str(e)}")
        
        # Заменяем нашу цепь, если найдена более длинная валидная цепь
        if longest_chain:
            # Здесь должно быть преобразование dict -> Block
            # Упрощено для примера
            logger.info(f"Chain replaced, new length: {max_length}")
            return True
        
        logger.info("Our chain is authoritative")
        return False
    
    @classmethod
    def _sync_loop(cls) -> None:
        """Периодически синхронизирует блокчейн с другими узлами."""
        while cls.running:
            cls.consensus()
            # Ждем перед следующей синхронизацией
            time.sleep(60)  # Синхронизация каждую минуту
    
    @classmethod
    def register_message_handler(cls, message_type: str, handler: Callable) -> None:
        """
        Регистрирует обработчик для определенного типа сообщений.
        
        Args:
            message_type: Тип сообщения
            handler: Функция-обработчик
        """
        NodeServer.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    @classmethod
    def send_message(cls, node_url: str, message_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение конкретному узлу.
        
        Args:
            node_url: URL узла
            message_type: Тип сообщения
            data: Данные сообщения
            
        Returns:
            Ответ от узла или None в случае ошибки
        """
        try:
            message = {"type": message_type, **data}
            response = requests.post(
                f"{node_url}/message",
                json=message,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            logger.warning(f"Failed to send message to {node_url}: {str(e)}")
        return None
    
    @classmethod
    def broadcast_message(cls, message_type: str, data: Dict[str, Any]) -> int:
        """
        Рассылает сообщение всем известным узлам.
        
        Args:
            message_type: Тип сообщения
            data: Данные сообщения
            
        Returns:
            Количество узлов, которым успешно отправлено сообщение
        """
        success_count = 0
        
        for node in cls.nodes:
            if cls.send_message(node, message_type, data):
                success_count += 1
        
        logger.info(f"Message broadcast to {success_count} of {len(cls.nodes)} nodes")
        return success_count

    @classmethod
    def handle_ping(cls, data):
        """
        Обрабатывает пинг-сообщения от других узлов.
        
        Args:
            data: Данные сообщения
            
        Returns:
            Ответ на пинг
        """
        # Если в сообщении есть идентификатор узла, сохраняем его
        if 'node_id' in data:
            remote_node_id = data['node_id']
            # Обновляем информацию об узле в базе данных
            cls.node_info[remote_node_id] = {
                'last_seen': time.time(),
                'node_id': remote_node_id
            }
            logger.debug(f"Обновлена информация об узле {remote_node_id}")
        
        # Отправляем ответ
        return {
            'status': 'ok',
            'timestamp': time.time(),
            'node_id': cls.node_id,
            'version': '1.0.0',
            'chain_length': len(cls.blockchain.chain) if cls.blockchain else 0
        }


# Пример использования
if __name__ == "__main__":
    # Для тестирования нужен импорт блокчейна
    from blockchain import Blockchain
    
    # Создаем блокчейн
    blockchain = Blockchain()
    
    # Инициализируем сетевой модуль
    NodeNetwork.initialize(blockchain, port=5000)
    
    # Регистрируем несколько тестовых узлов
    NodeNetwork.register_node("http://localhost:5001")
    NodeNetwork.register_node("http://localhost:5002")
    
    # Пример обработчика сообщений
    def handle_ping(data):
        return {"status": "pong", "received_at": time.time()}
    
    # Регистрируем обработчик
    NodeNetwork.register_message_handler("ping", handle_ping)
    
    try:
        # Держим сервер запущенным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Останавливаем сервер при нажатии Ctrl+C
        NodeNetwork.shutdown() 