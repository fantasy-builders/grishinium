"""
Grishinium Blockchain Package
"""

__version__ = '0.1.0'
__author__ = 'Grishinium Team'

# Экспортируем основные классы для упрощения импорта
from .blockchain import Blockchain, Block
from .crypto import generate_key_pair, get_address_from_public_key, sign_transaction, verify_signature
from .network import NodeNetwork
from .consensus import ProofOfWork, MiningRewardsCalculator
from .storage import BlockchainStorage
from .utils import calculate_hash, calculate_merkle_root, validate_address, validate_transaction

# Версия блокчейна
VERSION = {
    'major': 0,
    'minor': 1,
    'patch': 0,
    'codename': 'Genesis'
}


def get_version_string() -> str:
    """
    Возвращает строку с версией блокчейна.
    
    Returns:
        Строка с версией
    """
    v = VERSION
    return f"{v['major']}.{v['minor']}.{v['patch']} ({v['codename']})" 