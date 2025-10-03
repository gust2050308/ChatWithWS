"""
Sistema de cifrado AES-256-GCM para WebSockets
Compatible con Web Crypto API del navegador
"""
import secrets
import base64
import time
from typing import Dict, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoManager:
    def __init__(self, key_lifetime: int = 3600):
        """
        Gestor de cifrado con rotación automática de claves

        Args:
            key_lifetime: Tiempo de vida de cada clave en segundos (default: 1 hora)
        """
        self.key_lifetime = key_lifetime
        self.keys: Dict[str, Tuple[bytes, float]] = {}  # {key_id: (key_bytes, timestamp)}
        self.current_key_id: str = None
        self._generate_new_key()

    def _generate_new_key(self) -> str:
        """Genera una nueva clave AES-256 y la marca como actual"""
        key_bytes = AESGCM.generate_key(bit_length=256)
        key_id = f"key_{int(time.time())}_{secrets.token_hex(4)}"
        timestamp = time.time()

        self.keys[key_id] = (key_bytes, timestamp)
        self.current_key_id = key_id

        print(f"Nueva clave generada: {key_id}")
        return key_id

    def get_current_key_base64(self) -> Tuple[str, str]:
        """Retorna la clave actual en base64 para enviar al cliente"""
        if not self.current_key_id:
            self._generate_new_key()

        key_bytes, _ = self.keys[self.current_key_id]
        key_base64 = base64.b64encode(key_bytes).decode('utf-8')
        return self.current_key_id, key_base64

    def encrypt_message(self, message: str, key_id: str = None) -> dict:
        """
        Cifra un mensaje usando AES-256-GCM

        Args:
            message: Texto a cifrar
            key_id: ID de la clave a usar (usa la actual si no se especifica)

        Returns:
            dict con encrypted, nonce, key_id, timestamp
        """
        if key_id is None:
            key_id = self.current_key_id

        if key_id not in self.keys:
            raise ValueError(f"Clave {key_id} no encontrada")

        key_bytes, _ = self.keys[key_id]
        aesgcm = AESGCM(key_bytes)

        # Generar nonce de 12 bytes (96 bits) - estándar para GCM
        nonce = secrets.token_bytes(12)

        # Cifrar mensaje
        message_bytes = message.encode('utf-8')
        encrypted_bytes = aesgcm.encrypt(nonce, message_bytes, None)

        return {
            'encrypted': base64.b64encode(encrypted_bytes).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'key_id': key_id,
            'timestamp': int(time.time() * 1000)
        }

    def decrypt_message(self, encrypted_b64: str, nonce_b64: str, key_id: str) -> str:
        """
        Descifra un mensaje usando AES-256-GCM

        Args:
            encrypted_b64: Mensaje cifrado en base64
            nonce_b64: Nonce en base64
            key_id: ID de la clave usada

        Returns:
            Mensaje descifrado como string
        """
        if key_id not in self.keys:
            available = list(self.keys.keys())
            raise ValueError(f"Clave {key_id} no disponible. Claves disponibles: {available}")

        key_bytes, _ = self.keys[key_id]
        aesgcm = AESGCM(key_bytes)

        # Decodificar base64
        encrypted_bytes = base64.b64decode(encrypted_b64)
        nonce = base64.b64decode(nonce_b64)

        # Descifrar
        decrypted_bytes = aesgcm.decrypt(nonce, encrypted_bytes, None)
        return decrypted_bytes.decode('utf-8')

    def rotate_key_if_needed(self) -> bool:
        """Rota la clave si ha expirado. Retorna True si rotó"""
        if not self.current_key_id:
            return False

        _, timestamp = self.keys[self.current_key_id]
        age = time.time() - timestamp

        if age >= self.key_lifetime:
            self._generate_new_key()
            return True
        return False

    def _clean_old_keys(self):
        """Elimina claves que tienen más del doble del lifetime (mantiene histórico)"""
        current_time = time.time()
        max_age = self.key_lifetime * 2

        keys_to_remove = [
            key_id for key_id, (_, timestamp) in self.keys.items()
            if current_time - timestamp > max_age and key_id != self.current_key_id
        ]

        for key_id in keys_to_remove:
            del self.keys[key_id]
            print(f"Clave antigua eliminada: {key_id}")

    def get_key_info(self) -> dict:
        """Retorna información sobre las claves activas"""
        return {
            'total_keys': len(self.keys),
            'current_key_id': self.current_key_id,
            'key_ages': {
                key_id: int(time.time() - timestamp)
                for key_id, (_, timestamp) in self.keys.items()
            }
        }


# Instancia global del gestor de cifrado
crypto_manager = CryptoManager(key_lifetime=3600)  # Rotar cada hora