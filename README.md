# Secure E2EE Chat Application

This is a Python project for the Applied Cryptography course.

The project is a secure real-time chat application with:

* user registration and login
* TLS-protected client-server transport
* end-to-end encrypted chat messages
* X25519 Diffie-Hellman key exchange
* manual public key fingerprint verification
* HKDF-SHA256 key derivation
* AES-GCM encryption
* replay protection with message counters

The server is used to connect clients and forward data. It cannot read encrypted chat messages because it does not have the AES session keys.

TLS is used to protect the transport between clients and the server. This prevents login data and protocol messages from being visible as plaintext in Wireshark.

---

## Project Structure

```text
cryptography_project/
├── server.py
├── client.py
├── crypto_utils.py
├── auth_utils.py
├── protocol.py
├── generate_tls_cert.py
├── requirements.txt
├── README.md
├── security_report.md
└── .gitignore
```

| File                   | Description                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------- |
| `server.py`            | TLS-enabled server that accepts clients and forwards public keys and encrypted messages |
| `client.py`            | Terminal chat client used by users                                                      |
| `crypto_utils.py`      | Cryptographic functions for X25519, HKDF-SHA256, AES-GCM, nonces, and fingerprints      |
| `auth_utils.py`        | User registration, login, password hashing, and SQLite database                         |
| `protocol.py`          | JSON socket communication with message length headers                                   |
| `generate_tls_cert.py` | Generates local self-signed TLS certificate files for testing                           |
| `security_report.md`   | Written security analysis document                                                      |

---

## Requirements

Python 3.10 or newer is recommended.

Install all dependencies with:

```powershell
pip install -r requirements.txt
```

The `requirements.txt` file contains:

```text
cffi==2.0.0
cryptography==48.0.0
pycparser==3.0
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

Generate local TLS certificate files:

```powershell
python generate_tls_cert.py
```

This creates:

```text
cert.pem
key.pem
```

These files are required for running the TLS-enabled server and client.

Do not commit `cert.pem` and `key.pem` to GitHub. They are local generated files and are ignored in `.gitignore`.

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
[TLS] TLS transport protection is enabled.
```

Leave the server running.

---

### Terminal 2: Start the first client

```powershell
python client.py
```

Expected output:

```text
[CONNECTED] Connected to server using TLS.
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

Expected output:

```text
[CONNECTED] Connected to server using TLS.
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

This shows that the server forwards the encrypted message but does not read the message content.

---

## Commands

| Command            | Purpose                                                      |
| ------------------ | ------------------------------------------------------------ |
| `/to username`     | Choose who to send messages to                               |
| `/keyx username`   | Start X25519 key exchange with a user                        |
| `/pending`         | Show pending key exchange requests                           |
| `/accept username` | Accept a pending key exchange after checking the fingerprint |
| `/keys`            | Show users with established session keys                     |
| `/who`             | Show current chat partner                                    |
| `/quit`            | Exit the chat                                                |

---

## Security Design

### Authentication

Users register with a username and password.

Passwords are not stored as plain text. The application stores:

* username
* random salt
* PBKDF2-HMAC-SHA256 password hash

User data is stored in a local SQLite database called `chat.db`.

The database does not store:

* plaintext passwords
* chat messages
* private keys
* AES session keys

The `username` is unique because it is used as the primary key. The `salt` and `password_hash` are stored as BLOB values.

---

### TLS Transport Protection

The application uses TLS for client-server transport protection.

The server uses local TLS files:

```text
cert.pem
key.pem
```

These files are generated with:

```powershell
python generate_tls_cert.py
```

The client loads `cert.pem` when connecting to the server.

TLS protects login data, registration data, public key exchange messages, and protocol JSON messages from being visible as plaintext in Wireshark.

TLS does not replace end-to-end encryption. TLS protects the connection between the client and the server, while E2EE protects chat message content from the server itself.

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

This helps reduce the risk of public key substitution or man-in-the-middle attacks during key exchange. It is still manual verification and does not replace a full PKI system for user identity.

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

* confidentiality
* integrity
* authentication

If an attacker changes the ciphertext, nonce, counter, sender, or receiver data, decryption fails and the message is rejected.

The sender, receiver, and counter are used as associated data. This means they are not hidden, but they are protected from modification.

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

* no offline messages
* both users must be online at the same time
* session keys are stored only in memory
* after restart, users must perform key exchange again
* uses a self-signed TLS certificate for local testing
* no full public key infrastructure for user identity
* fingerprint verification is manual
* no multi-factor authentication
* no password reset or account lockout
* no password strength rules
* does not protect against a compromised client device
* designed for local testing on `127.0.0.1`

---

## Git Notes

Do not commit local or generated files such as:

```text
.venv/
chat.db
cert.pem
key.pem
__pycache__/
.env
*.key
*.pem
*.db
```

These files are ignored in `.gitignore`.

The file `generate_tls_cert.py` can be committed because it is only a script for generating local TLS files. It does not contain secret keys.

---

## Security Report

The written security analysis document is located in:

```text
security_report.md
```

The report explains:

* security goals and threat model
* design choices
* cryptographic primitives
* protocol flow
* TLS transport protection
* key management
* security assumptions and limitations
