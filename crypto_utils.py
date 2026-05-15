import os
import base64
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


NONCE_SIZE = 12
AES_KEY_SIZE = 32


def generate_x25519_key_pair() -> Tuple[x25519.X25519PrivateKey, str]:
    """
    Generates an X25519 private/public key pair.

    Returns:
        private_key: local private key object
        public_key_b64: base64 encoded public key
    """
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    public_key_b64 = base64.b64encode(public_key_bytes).decode("utf-8")

    return private_key, public_key_b64


def load_public_key_from_b64(public_key_b64: str) -> x25519.X25519PublicKey:
    """
    Loads an X25519 public key from a base64 encoded string.
    """
    public_key_bytes = base64.b64decode(public_key_b64.encode("utf-8"))
    return x25519.X25519PublicKey.from_public_bytes(public_key_bytes)


def derive_shared_key(
    private_key: x25519.X25519PrivateKey,
    peer_public_key_b64: str,
    context_info: bytes = b"secure-e2ee-chat",
) -> bytes:
    """
    Performs X25519 Diffie-Hellman and derives a symmetric AES key using HKDF.

    Args:
        private_key: own X25519 private key
        peer_public_key_b64: peer's base64 encoded public key
        context_info: protocol-specific context string for domain separation

    Returns:
        32-byte AES key
    """
    peer_public_key = load_public_key_from_b64(peer_public_key_b64)

    shared_secret = private_key.exchange(peer_public_key)

    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=None,
        info=context_info,
    ).derive(shared_secret)

    return derived_key


def generate_nonce() -> bytes:
    """
    Generates a fresh random nonce for AES-GCM.

    AES-GCM requires nonce uniqueness under the same key.
    96-bit nonces are the standard recommendation.
    """
    return os.urandom(NONCE_SIZE)


def encrypt_message(key: bytes, plaintext: str, associated_data: bytes | None = None) -> tuple[str, str]:
    """
    Encrypts a plaintext message using AES-GCM.

    Args:
        key: 32-byte AES key
        plaintext: message to encrypt
        associated_data: optional authenticated but unencrypted data

    Returns:
        nonce_b64, ciphertext_b64
    """
    nonce = generate_nonce()
    aesgcm = AESGCM(key)

    ciphertext = aesgcm.encrypt(
        nonce,
        plaintext.encode("utf-8"),
        associated_data,
    )

    nonce_b64 = base64.b64encode(nonce).decode("utf-8")
    ciphertext_b64 = base64.b64encode(ciphertext).decode("utf-8")

    return nonce_b64, ciphertext_b64


def decrypt_message(
    key: bytes,
    nonce_b64: str,
    ciphertext_b64: str,
    associated_data: bytes | None = None,
) -> str:
    """
    Decrypts an AES-GCM encrypted message.

    If ciphertext, nonce, key, or associated data is modified,
    AES-GCM authentication fails and an exception is raised.
    """
    nonce = base64.b64decode(nonce_b64.encode("utf-8"))
    ciphertext = base64.b64decode(ciphertext_b64.encode("utf-8"))

    aesgcm = AESGCM(key)

    plaintext = aesgcm.decrypt(
        nonce,
        ciphertext,
        associated_data,
    )

    return plaintext.decode("utf-8")


if __name__ == "__main__":
    print("Crypto utilities test")
    print("---------------------")

    # Simulate two users: Ivan and Marko
    ivan_private_key, ivan_public_key = generate_x25519_key_pair()
    marko_private_key, marko_public_key = generate_x25519_key_pair()

    # Both users derive the same shared AES key
    ivan_shared_key = derive_shared_key(ivan_private_key, marko_public_key)
    marko_shared_key = derive_shared_key(marko_private_key, ivan_public_key)

    print("Ivan public key:", ivan_public_key)
    print("Marko public key:", marko_public_key)
    print("Shared keys match:", ivan_shared_key == marko_shared_key)

    # Ivan encrypts a message
    original_message = "Bok Marko, ovo je E2EE test poruka."
    nonce_b64, ciphertext_b64 = encrypt_message(ivan_shared_key, original_message)

    print("Original message:", original_message)
    print("Nonce:", nonce_b64)
    print("Ciphertext:", ciphertext_b64)

    # Marko decrypts the message
    decrypted_message = decrypt_message(marko_shared_key, nonce_b64, ciphertext_b64)

    print("Decrypted message:", decrypted_message)
    print("Decryption successful:", decrypted_message == original_message)

    # Tampering test
    try:
        tampered_ciphertext = ciphertext_b64[:-2] + "AA"
        decrypt_message(marko_shared_key, nonce_b64, tampered_ciphertext)
        print("Tampering test failed: modified ciphertext was accepted.")
    except Exception:
        print("Tampering test passed: modified ciphertext was rejected.")