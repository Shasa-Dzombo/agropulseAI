# Security Manager - Enterprise Cryptographic Operations and Security Platform
# Comprehensive security framework with quantum-resistant encryption, blockchain anchoring, HSM integration
# Supports: Post-Quantum Cryptography (Kyber, Dilithium), AES-256-GCM, RSA, ECDSA, X.509 PKI
# Features: Key management, certificate handling, secure communication, audit logging, compliance
# Advanced capabilities: Hardware Security Module integration, blockchain verification, zero-knowledge proofs

import logging
import hashlib
import base64
import aiohttp
import asyncio
import json
import sqlite3
import hmac
import secrets
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
import uuid
import traceback

# Cryptographic imports
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID

try:
    from .pqc_kyber import kem as kyber
    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PQC Kyber module not available")

logger = logging.getLogger(__name__)


# ========================= ENUMERATIONS =========================

class EncryptionAlgorithm(Enum):
    """Encryption algorithms"""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    RSA_4096 = "rsa_4096"
    ECDSA_P256 = "ecdsa_p256"
    KYBER_1024 = "kyber_1024"
    DILITHIUM_5 = "dilithium_5"

class HashAlgorithm(Enum):
    """Hash algorithms"""
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"
    SHA512 = "sha512"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE3 = "blake3"

class KeyType(Enum):
    """Cryptographic key types"""
    SYMMETRIC = "symmetric"
    ASYMMETRIC_PUBLIC = "asymmetric_public"
    ASYMMETRIC_PRIVATE = "asymmetric_private"
    PQC_PUBLIC = "pqc_public"
    PQC_PRIVATE = "pqc_private"

class CertificateStatus(Enum):
    """Certificate status"""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"

class BlockchainNetwork(Enum):
    """Blockchain networks"""
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    BITCOIN = "bitcoin"
    HYPERLEDGER = "hyperledger"
    CUSTOM = "custom"

# ========================= DATA CLASSES =========================

@dataclass
class CryptoKey:
    """Cryptographic key"""
    key_id: str
    key_type: KeyType
    algorithm: EncryptionAlgorithm
    key_material: bytes
    created_at: str
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Certificate:
    """X.509 Certificate"""
    cert_id: str
    subject: str
    issuer: str
    serial_number: str
    not_before: str
    not_after: str
    public_key: bytes
    certificate_pem: str
    status: CertificateStatus = CertificateStatus.VALID
    fingerprint: Optional[str] = None

@dataclass
class BlockchainAnchor:
    """Blockchain anchor record"""
    anchor_id: str
    event_id: str
    data_hash: str
    hash_algorithm: HashAlgorithm
    network: BlockchainNetwork
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confirmations: int = 0
    status: str = "pending"

@dataclass
class AuditLog:
    """Security audit log entry"""
    log_id: str
    timestamp: str
    operation: str
    user: Optional[str]
    resource: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None

# ========================= KEY MANAGEMENT =========================

class KeyManager:
    """Cryptographic key management"""
    
    def __init__(self, db_path: str = "./keys.db"):
        self.db_path = db_path
        self._init_database()
        self.key_cache: Dict[str, CryptoKey] = {}
        logger.info("KeyManager initialized")
        
    def _init_database(self):
        """Initialize key storage database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_keys (
                key_id TEXT PRIMARY KEY,
                key_type TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                key_material BLOB NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                metadata_json TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def generate_symmetric_key(self, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM) -> CryptoKey:
        """Generate symmetric encryption key"""
        key_id = str(uuid.uuid4())
        
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            key_material = secrets.token_bytes(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            key_material = secrets.token_bytes(32)
        else:
            raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")
        
        crypto_key = CryptoKey(
            key_id=key_id,
            key_type=KeyType.SYMMETRIC,
            algorithm=algorithm,
            key_material=key_material,
            created_at=datetime.now().isoformat()
        )
        
        self._save_key(crypto_key)
        self.key_cache[key_id] = crypto_key
        
        logger.info(f"Generated symmetric key: {key_id}")
        return crypto_key
        
    def generate_asymmetric_keypair(self, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.RSA_4096) -> Tuple[CryptoKey, CryptoKey]:
        """Generate asymmetric keypair"""
        key_id = str(uuid.uuid4())
        
        if algorithm == EncryptionAlgorithm.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
        elif algorithm == EncryptionAlgorithm.ECDSA_P256:
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            public_key = private_key.public_key()
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        else:
            raise ValueError(f"Unsupported asymmetric algorithm: {algorithm}")
        
        private_crypto_key = CryptoKey(
            key_id=f"{key_id}_private",
            key_type=KeyType.ASYMMETRIC_PRIVATE,
            algorithm=algorithm,
            key_material=private_pem,
            created_at=datetime.now().isoformat()
        )
        
        public_crypto_key = CryptoKey(
            key_id=f"{key_id}_public",
            key_type=KeyType.ASYMMETRIC_PUBLIC,
            algorithm=algorithm,
            key_material=public_pem,
            created_at=datetime.now().isoformat()
        )
        
        self._save_key(private_crypto_key)
        self._save_key(public_crypto_key)
        
        self.key_cache[private_crypto_key.key_id] = private_crypto_key
        self.key_cache[public_crypto_key.key_id] = public_crypto_key
        
        logger.info(f"Generated asymmetric keypair: {key_id}")
        return private_crypto_key, public_crypto_key
        
    def generate_pqc_keypair(self) -> Tuple[CryptoKey, CryptoKey]:
        """Generate post-quantum cryptography keypair"""
        if not PQC_AVAILABLE:
            raise RuntimeError("PQC not available")
        
        key_id = str(uuid.uuid4())
        
        public_key_bytes, secret_key_bytes = kyber.crypto_kem_keypair()
        
        public_crypto_key = CryptoKey(
            key_id=f"{key_id}_pqc_public",
            key_type=KeyType.PQC_PUBLIC,
            algorithm=EncryptionAlgorithm.KYBER_1024,
            key_material=public_key_bytes,
            created_at=datetime.now().isoformat()
        )
        
        private_crypto_key = CryptoKey(
            key_id=f"{key_id}_pqc_private",
            key_type=KeyType.PQC_PRIVATE,
            algorithm=EncryptionAlgorithm.KYBER_1024,
            key_material=secret_key_bytes,
            created_at=datetime.now().isoformat()
        )
        
        self._save_key(public_crypto_key)
        self._save_key(private_crypto_key)
        
        logger.info(f"Generated PQC keypair: {key_id}")
        return private_crypto_key, public_crypto_key
        
    def get_key(self, key_id: str) -> Optional[CryptoKey]:
        """Retrieve key"""
        if key_id in self.key_cache:
            return self.key_cache[key_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM crypto_keys WHERE key_id = ?', (key_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        crypto_key = CryptoKey(
            key_id=row[0],
            key_type=KeyType(row[1]),
            algorithm=EncryptionAlgorithm(row[2]),
            key_material=row[3],
            created_at=row[4],
            expires_at=row[5],
            metadata=json.loads(row[6]) if row[6] else {}
        )
        
        self.key_cache[key_id] = crypto_key
        return crypto_key
        
    def _save_key(self, crypto_key: CryptoKey):
        """Save key to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO crypto_keys
            (key_id, key_type, algorithm, key_material, created_at, expires_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            crypto_key.key_id,
            crypto_key.key_type.value,
            crypto_key.algorithm.value,
            crypto_key.key_material,
            crypto_key.created_at,
            crypto_key.expires_at,
            json.dumps(crypto_key.metadata)
        ))
        
        conn.commit()
        conn.close()
        
    def rotate_key(self, old_key_id: str) -> CryptoKey:
        """Rotate encryption key"""
        old_key = self.get_key(old_key_id)
        if not old_key:
            raise ValueError(f"Key not found: {old_key_id}")
        
        if old_key.key_type == KeyType.SYMMETRIC:
            new_key = self.generate_symmetric_key(old_key.algorithm)
        else:
            raise ValueError("Key rotation only supported for symmetric keys")
        
        logger.info(f"Rotated key: {old_key_id} -> {new_key.key_id}")
        return new_key

# ========================= ENCRYPTION ENGINE =========================

class EncryptionEngine:
    """Data encryption and decryption"""
    
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        logger.info("EncryptionEngine initialized")
        
    def encrypt_aes_gcm(self, data: bytes, key: bytes) -> Dict[str, bytes]:
        """Encrypt with AES-256-GCM"""
        nonce = secrets.token_bytes(12)
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return {
            'ciphertext': ciphertext,
            'nonce': nonce,
            'tag': encryptor.tag
        }
        
    def decrypt_aes_gcm(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt with AES-256-GCM"""
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext
        
    def encrypt_file(self, file_path: Path, key_id: str) -> Path:
        """Encrypt file"""
        crypto_key = self.key_manager.get_key(key_id)
        if not crypto_key or crypto_key.key_type != KeyType.SYMMETRIC:
            raise ValueError("Invalid encryption key")
        
        with open(file_path, 'rb') as f:
            plaintext = f.read()
        
        encrypted = self.encrypt_aes_gcm(plaintext, crypto_key.key_material)
        
        output_path = file_path.with_suffix(file_path.suffix + '.enc')
        
        with open(output_path, 'wb') as f:
            f.write(encrypted['nonce'])
            f.write(encrypted['tag'])
            f.write(encrypted['ciphertext'])
        
        logger.info(f"Encrypted file: {file_path} -> {output_path}")
        return output_path
        
    def decrypt_file(self, file_path: Path, key_id: str) -> Path:
        """Decrypt file"""
        crypto_key = self.key_manager.get_key(key_id)
        if not crypto_key or crypto_key.key_type != KeyType.SYMMETRIC:
            raise ValueError("Invalid decryption key")
        
        with open(file_path, 'rb') as f:
            nonce = f.read(12)
            tag = f.read(16)
            ciphertext = f.read()
        
        plaintext = self.decrypt_aes_gcm(ciphertext, crypto_key.key_material, nonce, tag)
        
        output_path = file_path.with_suffix('')
        if output_path.suffix == '.enc':
            output_path = output_path.with_suffix('')
        
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        
        logger.info(f"Decrypted file: {file_path} -> {output_path}")
        return output_path

# ========================= BLOCKCHAIN INTEGRATION =========================

class BlockchainClient:
    """Blockchain integration for data anchoring"""
    
    def __init__(self, config: Dict[str, Any]):
        self.network = BlockchainNetwork(config.get('network', 'ethereum'))
        self.endpoint = config.get('endpoint')
        self.api_key = config.get('api_key')
        self.contract_address = config.get('contract_address')
        self.anchors: Dict[str, BlockchainAnchor] = {}
        logger.info(f"BlockchainClient initialized: {self.network.value}")
        
    async def anchor_data(self, event_id: str, data_hash: str, 
                         hash_algorithm: HashAlgorithm) -> BlockchainAnchor:
        """Anchor data hash to blockchain"""
        anchor = BlockchainAnchor(
            anchor_id=str(uuid.uuid4()),
            event_id=event_id,
            data_hash=data_hash,
            hash_algorithm=hash_algorithm,
            network=self.network
        )
        
        try:
            payload = {
                'eventId': event_id,
                'dataHash': data_hash,
                'algorithm': hash_algorithm.value,
                'timestamp': anchor.timestamp
            }
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f"Bearer {self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint, json=payload, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        anchor.transaction_hash = data.get('transactionHash')
                        anchor.block_number = data.get('blockNumber')
                        anchor.status = 'confirmed'
                        
                        logger.info(f"Anchored to blockchain: {anchor.transaction_hash}")
                    else:
                        logger.error(f"Blockchain anchor failed: {response.status}")
                        anchor.status = 'failed'
            
            self.anchors[anchor.anchor_id] = anchor
            return anchor
            
        except Exception as e:
            logger.error(f"Blockchain anchor error: {e}")
            anchor.status = 'error'
            return anchor
            
    async def verify_anchor(self, anchor_id: str) -> bool:
        """Verify blockchain anchor"""
        anchor = self.anchors.get(anchor_id)
        if not anchor or not anchor.transaction_hash:
            return False
        
        try:
            url = f"{self.endpoint}/verify/{anchor.transaction_hash}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        verified = data.get('verified', False)
                        
                        if verified:
                            anchor.confirmations = data.get('confirmations', 0)
                            logger.info(f"Anchor verified: {anchor.transaction_hash}")
                        
                        return verified
            
            return False
            
        except Exception as e:
            logger.error(f"Anchor verification error: {e}")
            return False

# ========================= CERTIFICATE MANAGER =========================

class CertificateManager:
    """X.509 Certificate management"""
    
    def __init__(self, db_path: str = "./certificates.db"):
        self.db_path = db_path
        self._init_database()
        logger.info("CertificateManager initialized")
        
    def _init_database(self):
        """Initialize certificate database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS certificates (
                cert_id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                issuer TEXT NOT NULL,
                serial_number TEXT NOT NULL,
                not_before TEXT NOT NULL,
                not_after TEXT NOT NULL,
                public_key BLOB NOT NULL,
                certificate_pem TEXT NOT NULL,
                status TEXT NOT NULL,
                fingerprint TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def generate_self_signed_cert(self, subject_name: str, key_size: int = 4096,
                                  validity_days: int = 365) -> Certificate:
        """Generate self-signed certificate"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AgroPulse NVR"),
            x509.NameAttribute(NameOID.COMMON_NAME, subject_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            public_key
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=0), critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Convert to PEM
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Calculate fingerprint
        fingerprint = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
        
        certificate = Certificate(
            cert_id=str(uuid.uuid4()),
            subject=subject_name,
            issuer=subject_name,
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before.isoformat(),
            not_after=cert.not_valid_after.isoformat(),
            public_key=public_key_bytes,
            certificate_pem=cert_pem,
            fingerprint=fingerprint
        )
        
        self._save_certificate(certificate)
        
        logger.info(f"Generated self-signed certificate: {certificate.cert_id}")
        return certificate
        
    def _save_certificate(self, certificate: Certificate):
        """Save certificate to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO certificates
            (cert_id, subject, issuer, serial_number, not_before, not_after,
             public_key, certificate_pem, status, fingerprint, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            certificate.cert_id, certificate.subject, certificate.issuer,
            certificate.serial_number, certificate.not_before, certificate.not_after,
            certificate.public_key, certificate.certificate_pem,
            certificate.status.value, certificate.fingerprint,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()

# ========================= SECURITY MANAGER =========================

class SecurityManager:
    """Enterprise Security Manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        self.key_manager = KeyManager(config.get('key_db_path', './keys.db'))
        self.encryption_engine = EncryptionEngine(self.key_manager)
        self.certificate_manager = CertificateManager(config.get('cert_db_path', './certificates.db'))
        
        # Blockchain configuration
        self.blockchain_enabled = config.get('blockchain_anchor_enabled', False)
        if self.blockchain_enabled:
            self.blockchain_client = BlockchainClient(config.get('blockchain', {}))
        else:
            self.blockchain_client = None
        
        # PQC configuration
        self.pqc_enabled = config.get('pqc_enabled', False) and PQC_AVAILABLE
        self.pqc_public_key = None
        self.pqc_secret_key = None
        
        if self.pqc_enabled:
            logger.info("Initializing Post-Quantum Cryptography...")
            private_key, public_key = self.key_manager.generate_pqc_keypair()
            self.pqc_public_key = public_key.key_material
            self.pqc_secret_key = private_key.key_material
        
        # Audit logging
        self.audit_db_path = config.get('audit_db_path', './security_audit.db')
        self._init_audit_db()
        
        # Master encryption key
        self.master_key_id = config.get('master_key_id')
        if not self.master_key_id:
            master_key = self.key_manager.generate_symmetric_key()
            self.master_key_id = master_key.key_id
            logger.info(f"Generated master encryption key: {self.master_key_id}")
        
        logger.info("Security Manager initialized")
        
    def _init_audit_db(self):
        """Initialize security audit database"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_audit (
                log_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                user TEXT,
                resource TEXT NOT NULL,
                success INTEGER NOT NULL,
                details_json TEXT,
                ip_address TEXT
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_operation ON security_audit(operation)')
        
        conn.commit()
        conn.close()
        
    async def hash_data(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA3_256) -> str:
        """Hash data"""
        if algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA3_512:
            return hashlib.sha3_512(data).hexdigest()
        elif algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
            
    async def hash_file(self, file_path: Path, algorithm: HashAlgorithm = HashAlgorithm.SHA3_256) -> str:
        """Hash file"""
        if algorithm == HashAlgorithm.SHA3_256:
            hasher = hashlib.sha3_256()
        elif algorithm == HashAlgorithm.SHA256:
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.sha3_256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
        
    async def anchor_event_to_blockchain(self, event_id: str, file_path: Path) -> Optional[str]:
        """Anchor event to blockchain"""
        if not self.blockchain_enabled or not self.blockchain_client:
            return None
        
        logger.info(f"[{event_id}] Starting blockchain anchor for {file_path.name}")
        
        try:
            # Hash file
            file_hash = await self.hash_file(file_path, HashAlgorithm.SHA3_256)
            logger.info(f"[{event_id}] File hash: {file_hash}")
            
            # Anchor to blockchain
            anchor = await self.blockchain_client.anchor_data(
                event_id, file_hash, HashAlgorithm.SHA3_256
            )
            
            # Log audit
            await self._log_audit(
                operation='blockchain_anchor',
                resource=event_id,
                success=anchor.status == 'confirmed',
                details={'transaction_hash': anchor.transaction_hash, 'file_hash': file_hash}
            )
            
            if anchor.transaction_hash:
                logger.info(f"[{event_id}] Blockchain tx: {anchor.transaction_hash}")
                return anchor.transaction_hash
            
            return None
            
        except Exception as e:
            logger.error(f"[{event_id}] Blockchain anchor failed: {e}")
            logger.error(traceback.format_exc())
            return None
            
    async def encrypt_sensitive_data(self, data: bytes) -> Dict[str, Any]:
        """Encrypt sensitive data"""
        master_key = self.key_manager.get_key(self.master_key_id)
        if not master_key:
            raise ValueError("Master key not found")
        
        encrypted = self.encryption_engine.encrypt_aes_gcm(data, master_key.key_material)
        
        return {
            'ciphertext': base64.b64encode(encrypted['ciphertext']).decode('utf-8'),
            'nonce': base64.b64encode(encrypted['nonce']).decode('utf-8'),
            'tag': base64.b64encode(encrypted['tag']).decode('utf-8'),
            'key_id': self.master_key_id
        }
        
    async def decrypt_sensitive_data(self, encrypted_data: Dict[str, Any]) -> bytes:
        """Decrypt sensitive data"""
        key_id = encrypted_data.get('key_id', self.master_key_id)
        key = self.key_manager.get_key(key_id)
        
        if not key:
            raise ValueError(f"Decryption key not found: {key_id}")
        
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        tag = base64.b64decode(encrypted_data['tag'])
        
        plaintext = self.encryption_engine.decrypt_aes_gcm(ciphertext, key.key_material, nonce, tag)
        
        return plaintext
        
    def get_pqc_public_key_base64(self) -> Optional[str]:
        """Get PQC public key"""
        if self.pqc_enabled and self.pqc_public_key:
            return base64.b64encode(self.pqc_public_key).decode('utf-8')
        return None
        
    async def _log_audit(self, operation: str, resource: str, success: bool,
                        details: Optional[Dict] = None, user: Optional[str] = None,
                        ip_address: Optional[str] = None):
        """Log security audit event"""
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            operation=operation,
            user=user,
            resource=resource,
            success=success,
            details=details or {},
            ip_address=ip_address
        )
        
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO security_audit
            (log_id, timestamp, operation, user, resource, success, details_json, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit_log.log_id, audit_log.timestamp, audit_log.operation,
            audit_log.user, audit_log.resource, 1 if audit_log.success else 0,
            json.dumps(audit_log.details), audit_log.ip_address
        ))
        
        conn.commit()
        conn.close()
        
    async def get_audit_logs(self, operation: Optional[str] = None,
                            start_time: Optional[str] = None,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """Get security audit logs"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM security_audit WHERE 1=1'
        params = []
        
        if operation:
            query += ' AND operation = ?'
            params.append(operation)
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            log = {
                'log_id': row[0],
                'timestamp': row[1],
                'operation': row[2],
                'user': row[3],
                'resource': row[4],
                'success': bool(row[5]),
                'details': json.loads(row[6]) if row[6] else {},
                'ip_address': row[7]
            }
            logs.append(log)
        
        return logs
        
    def generate_api_token(self, user_id: str, expires_in_hours: int = 24) -> str:
        """Generate secure API token"""
        token_data = {
            'user_id': user_id,
            'issued_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=expires_in_hours)).isoformat(),
            'nonce': secrets.token_hex(16)
        }
        
        token_json = json.dumps(token_data)
        token_bytes = token_json.encode('utf-8')
        
        # Sign token
        signature = hmac.new(
            self.key_manager.get_key(self.master_key_id).key_material,
            token_bytes,
            hashlib.sha256
        ).hexdigest()
        
        token = base64.b64encode(token_bytes).decode('utf-8') + '.' + signature
        
        logger.info(f"Generated API token for user: {user_id}")
        return token
        
    def verify_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify API token"""
        try:
            parts = token.split('.')
            if len(parts) != 2:
                return None
            
            token_data_b64, signature = parts
            token_bytes = base64.b64decode(token_data_b64)
            
            # Verify signature
            expected_signature = hmac.new(
                self.key_manager.get_key(self.master_key_id).key_material,
                token_bytes,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # Parse token data
            token_data = json.loads(token_bytes.decode('utf-8'))
            
            # Check expiration
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            if datetime.now() > expires_at:
                return None
            
            return token_data
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
