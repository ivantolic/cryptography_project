# Secure E2EE Chat Application

This is a Python project for the Applied Cryptography course.

The project is a secure real-time chat application with:
- user registration and login
- end-to-end encrypted chat messages
- X25519 Diffie-Hellman key exchange
- manual public key fingerprint verification
- AES-GCM encryption
- replay protection with message counters

The server is used only to connect clients and forward data. It cannot read encrypted chat messages because it does not have the session keys.

---

## Project Structure

```text
cryptography_project/
├── server.py
├── client.py
├── crypto_utils.py
├── auth_utils.py
├── protocol.py
├── requirements.txt
├── README.md
└── docs/
    └── security_report.md
```

| File | Description |
|---|---|
| `server.py` | Server that accepts clients and forwards public keys and encrypted messages |
| `client.py` | Terminal chat client used by users |
| `crypto_utils.py` | Cryptographic functions for key exchange, key derivation, encryption, and decryption |
| `auth_utils.py` | User registration, login, password hashing, and SQLite database |
| `protocol.py` | JSON socket communication with message length headers |

---

## Requirements

Python 3.10 or newer is recommended.

Main dependency:

```text
cryptography
```

Install all dependencies with:

```powershell
pip install -r requirements.txt
```

The SQLite database `chat.db` is created automatically when the server starts. It is used for local user accounts.

---

## Setup

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

## How to Run the Application

Use three separate terminals.

### Terminal 1: Start the server

```powershell
python server.py
```

Expected output:

```text
[SERVER STARTED]
Listening on 127.0.0.1:5000
```

Leave the server running.

---

### Terminal 2: Start the first client

```powershell
python client.py
```

Register or login as the first user, for example:

```text
pero
```

---

### Terminal 3: Start the second client

```powershell
python client.py
```

Register or login as the second user, for example:

```text
marko
```

Both users must be online at the same time for real-time messaging.

---

## Basic Test Flow

This is the recommended flow for testing the application.

### 1. Select a chat partner

On Pero's client:

```text
/to marko
```

Expected output:

```text
Now chatting with marko.
```

---

### 2. Start key exchange

On Pero's client:

```text
/keyx marko
```

Marko should receive a key exchange request with a public key fingerprint.

---

### 3. Accept key exchange on Marko's client

On Marko's client:

```text
/accept pero
```

Marko should establish a session key with Pero and send his public key back.

---

### 4. Accept key exchange on Pero's client

On Pero's client:

```text
/accept marko
```

Now both clients should have the same shared session key.

---

### 5. Check established session keys

On both clients, run:

```text
/keys
```

Expected output on Pero's client:

```text
Established session keys with: marko
```

Expected output on Marko's client:

```text
Established session keys with: pero
```

---

### 6. Send encrypted messages

On Pero's client:

```text
bok marko
```

Marko should see:

```text
[pero] bok marko
```

On the server, the plaintext message should not be shown. The server should show only encrypted forwarding information, for example:

```text
[CHAT] Encrypted message #1 forwarded from pero to marko.
```

This shows that the server forwards the message but does not read the message content.

---

## Commands

| Command | Purpose |
|---|---|
| `/to username` | Choose who to send messages to |
| `/keyx username` | Start X25519 key exchange with a user |
| `/pending` | Show pending key exchange requests |
| `/accept username` | Accept a pending key exchange after checking the fingerprint |
| `/keys` | Show users with established session keys |
| `/who` | Show current chat partner |
| `/quit` | Exit the chat |

---

## Security Design

### Authentication

Users register with a username and password.

Passwords are not stored as plain text. The application stores:
- username
- random salt
- PBKDF2-HMAC-SHA256 password hash

User data is stored in a local SQLite database called `chat.db`.

---

### Key Exchange

The application uses X25519 Diffie-Hellman for key exchange.

Each client creates a private and public key pair. Public keys are sent through the server, but private keys stay only on the clients.

After public keys are exchanged and accepted, both clients calculate the same shared secret. HKDF-SHA256 is then used to derive a 256-bit AES session key.

The session key is stored only in memory. If the client is restarted, users need to perform key exchange again.

---

### Fingerprint Verification

When a public key is received, the client shows a public key fingerprint.

Example:

```text
A1B2-C3D4-E5F6-7788
```

The user must manually accept the key exchange:

```text
/accept username
```

This helps reduce the risk of public key substitution or man-in-the-middle attacks during key exchange. It is still manual verification and does not replace certificates or a full PKI system.

---

### End-to-End Encryption

Messages are encrypted on the sender's client and decrypted only on the receiver's client.

The encrypted message that goes through the server contains:

```text
sender
receiver
nonce
counter
ciphertext
```

The server does not have the AES session key, so it cannot decrypt chat messages.

---

### Message Protection

The application uses AES-GCM for encrypted messages.

AES-GCM provides:
- confidentiality
- integrity
- authentication

If an attacker changes the ciphertext, nonce, counter, sender, or receiver data, decryption fails and the message is rejected.

---

### Replay Protection

Every encrypted message has a counter.

Example encrypted message format:

```json
{
  "type": "chat",
  "from": "pero",
  "to": "marko",
  "nonce": "...",
  "counter": 1,
  "ciphertext": "..."
}
```

The receiver remembers the last accepted counter from each sender. If the same old counter or a lower counter appears again, the message is rejected as a possible replay attack.

---

## Limitations

This application is a student prototype and is designed for local testing.

Limitations:
- no offline messages
- both users must be online at the same time
- session keys are stored only in memory
- after restart, users must perform key exchange again
- no certificates or public key infrastructure
- fingerprint verification is manual
- no multi-factor authentication
- no password reset or account lockout
- designed for local testing on `127.0.0.1`

---

## Git Notes

Do not commit local or generated files such as:

```text
.venv/
chat.db
__pycache__/
.env
*.key
*.pem
*.db
```

These files are ignored in `.gitignore`.

---

## Security Report

The written security analysis document is located in:

```text
docs/security_report.md
```

The report explains:
- security goals and threat model
- design choices
- cryptographic primitives
- protocol flow
- key management
- security assumptions and limitations