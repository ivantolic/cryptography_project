# Secure E2EE Chat Application

This is a Python project for the Applied Cryptography course.

The application is a real-time chat system with:
- user registration and login
- end-to-end encrypted messages
- X25519 Diffie-Hellman key exchange
- manual public key fingerprint verification
- AES-GCM encryption
- replay protection with message counters

The server only forwards messages. It cannot read encrypted chat messages because it does not have the session keys.

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
| `server.py` | Server that handles users and forwards encrypted messages |
| `client.py` | Terminal chat client |
| `crypto_utils.py` | Cryptographic functions |
| `auth_utils.py` | User authentication and SQLite database |
| `protocol.py` | JSON socket communication |

---

## Requirements

Python 3.10 or newer is recommended.

Install dependencies:

```powershell
pip install -r requirements.txt
```

The SQLite database `chat.db` is created automatically when the server starts.

Main dependency:

```text
cryptography
```

---

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

## How to Run

Use three terminals.

### Terminal 1: start server

```powershell
python server.py
```

Expected output:

```text
[SERVER STARTED]
Listening on 127.0.0.1:5000
```

### Terminal 2: start first client

```powershell
python client.py
```

Register or login as the first user, for example:

```text
pero
```

### Terminal 3: start second client

```powershell
python client.py
```

Register or login as the second user, for example:

```text
marko
```

---

## Basic Usage

After login, the client shows available commands.

### Select chat partner

On Pero's client:

```text
/to marko
```

### Start key exchange

On Pero's client:

```text
/keyx marko
```

Marko will receive a key exchange request with a public key fingerprint.

### Accept key exchange

On Marko's client:

```text
/accept pero
```

Then Pero receives Marko's public key and accepts it:

```text
/accept marko
```

Now both clients have a shared session key.

Check session keys:

```text
/keys
```

Expected result:

```text
Established session keys with: marko
```

or:

```text
Established session keys with: pero
```

---

## Sending Messages

After key exchange is complete, users can send encrypted messages.

Example on Pero's client:

```text
bok marko
```

Marko sees:

```text
[pero] bok marko
```

The server does not see the plaintext message. It only shows:

```text
[CHAT] Encrypted message #1 forwarded from pero to marko.
```

---

## Commands

| Command | Purpose |
|---|---|
| `/to username` | Choose chat partner |
| `/keyx username` | Start key exchange |
| `/pending` | Show pending key exchange requests |
| `/accept username` | Accept key exchange |
| `/keys` | Show users with session keys |
| `/who` | Show current chat partner |
| `/quit` | Exit chat |

---

## Security Design

### Authentication

Users register with a username and password.

Passwords are not stored as plain text. The application stores:
- username
- random salt
- PBKDF2-HMAC-SHA256 password hash

User data is stored in local SQLite database `chat.db`.

---

### Key Exchange

The application uses X25519 Diffie-Hellman.

Each client creates a private/public key pair. Public keys are sent through the server, but private keys stay only on the clients.

After key exchange, both clients calculate the same shared secret. HKDF-SHA256 is then used to create an AES session key.

---

### Fingerprint Verification

When a public key is received, the client shows a fingerprint.

Example:

```text
A1B2-C3D4-E5F6-7788
```

The user must manually accept the key exchange:

```text
/accept username
```

This helps reduce the risk of man-in-the-middle attacks.

---

### End-to-End Encryption

Messages are encrypted on the sender's client and decrypted only on the receiver's client.

The server only sees:

```text
sender
receiver
nonce
counter
ciphertext
```

The server does not have the session key, so it cannot decrypt messages.

---

### Message Protection

The application uses AES-GCM.

AES-GCM provides:
- confidentiality
- integrity
- authentication

If an attacker changes the ciphertext, nonce, counter, sender, or receiver data, decryption fails.

---

### Replay Protection

Every encrypted message has a counter.

Example:

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

The receiver remembers the last counter from each sender. If an old counter appears again, the message is rejected.

---

## Limitations

This is an educational prototype.

Limitations:
- no offline messages
- session keys are only stored in memory
- after restart, users must do key exchange again
- no PKI or certificates
- fingerprint verification is manual
- designed for local testing on `127.0.0.1`

---

## Git Notes

Do not commit these files:

```text
.venv/
chat.db
__pycache__/
.env
*.key
*.pem
```

These files are ignored in `.gitignore`.