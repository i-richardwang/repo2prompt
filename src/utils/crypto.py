from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import os
import logging

logger = logging.getLogger(__name__)

class AESCipher:
    """AES encryption/decryption utility."""
    
    def __init__(self, key: str = None):
        """Initialize AES cipher with encryption key.
        
        Args:
            key: Optional encryption key. If not provided, uses ENCRYPTION_SECRET env var.
            
        Raises:
            ValueError: If no encryption key is available.
        """
        self.key = key or os.getenv('ENCRYPTION_SECRET', '').encode('utf-8')
        if not self.key:
            raise ValueError("ENCRYPTION_SECRET environment variable is required")
            
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt AES encrypted text.
        
        Args:
            encrypted_text: Base64 encoded encrypted text
            
        Returns:
            Decrypted text
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_text)
            
            # Extract IV and ciphertext
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]
            
            # Create cipher and decrypt
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
            
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError(f"Decryption failed: {str(e)}") 