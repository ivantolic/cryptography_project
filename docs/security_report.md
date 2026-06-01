# Security Report: Secure E2EE Chat Application

## 1. Introduction

In this project, a secure chat application was made using Python. The main goal of this project is to show how messages between two users can be protected using cryptographic methods. The application uses one server and two or more clients to make real-time communication possible. Users can register, log in, exchange keys, and send messages.

The main idea of this application is that the server should not be able to read chat messages. The server is used to connect clients and forward data from one client to another. Messages are encrypted on the sender’s side and decrypted on the receiver’s side, which is the basic idea of end-to-end encryption.

The project also uses TLS for client-server transport protection. This means that the connection between the client and the server is encrypted, so login data and normal protocol messages are not visible as plaintext in Wireshark. TLS protects the transport channel, while end-to-end encryption protects the actual chat message content from the server.

The application has three main security parts. The first part is user authentication. Users log in with a username and password. Passwords are not saved as plain text. They are saved as salted password hashes in a local SQLite database. The second part is key exchange. Two clients exchange public keys and use X25519 Diffie-Hellman to create a shared secret. This shared secret is then used with HKDF-SHA256 to create an AES session key. The third part is secure messaging. After the key exchange is finished, messages are encrypted with AES-GCM before they are sent through the server.

The project also has protection against message modification and replay attacks. AES-GCM checks if the encrypted message or related data was changed. If someone changes the ciphertext or message data, decryption fails. Replay protection is done with counters, where every encrypted message has a counter value.

This application is still a student project. It does not have all features of a real production chat application. For example, it does not support offline messages, automatic identity verification, or a full public key infrastructure. Public key verification is done manually with fingerprints. The main purpose of this project is to show the basic security mechanisms used in a secure chat system, such as authentication, TLS transport protection, key exchange, encryption, nonce usage, replay protection, and security reasoning.

## 2. Security Goals

The main security goal of this chat application is to protect communication between two users. A user should be able to send a message to another user, and only that receiver should be able to read it. The server is needed for forwarding messages, but it should not be able to read their plaintext content.

The first goal is message privacy. This means that messages should not be readable by the server, another user, or someone watching the network traffic. In this project, this is handled in two layers. TLS protects the client-server transport channel, while AES-GCM end-to-end encryption protects chat message content from the server itself.

The second goal is message integrity. The receiver should be able to detect if a message was changed during transmission. If an attacker changes the encrypted message, the application should reject it instead of showing a modified message to the user.

The third goal is authentication. Users should not be able to use the chat application without registering and logging in. The application also avoids storing original passwords directly, because that would be unsafe if the local database was compromised.

The fourth goal is secure session setup. Before private messages can be sent, two clients need to agree on a shared session key. This key should not be sent directly over the network, and the server should not know it.

The fifth goal is replay protection. The application should not accept the same old encrypted message again as if it was a new message. This is important because an attacker may not understand the message, but could still try to send the same encrypted data again.

Another goal added during testing was transport protection. Before TLS was added, Wireshark could show login data because the client-server socket used plain TCP. After TLS was added, Wireshark no longer shows the login JSON or password in plaintext. This improves the security of the prototype.

These goals define what the application tries to protect. The later sections explain how the project implements these goals using authentication, TLS, X25519 key exchange, HKDF-SHA256, AES-GCM encryption, nonces, and message counters.

## 3. Threat Model

The threat model explains what kind of attacks this chat application tries to protect against. The main focus is on protecting chat messages while they are being sent between two clients through the server. The server is needed for communication, but it should not be trusted with plaintext message content.

One possible threat is passive network monitoring. This means that an attacker can observe network traffic between the client and the server. After adding TLS, the attacker should not be able to read login requests or protocol messages directly from the network capture. In Wireshark, the traffic appears as encrypted TLS data instead of readable JSON.

Another possible threat is the server seeing chat content. TLS alone is not enough to solve this, because TLS ends at the server. For that reason, the project also uses end-to-end encryption. The server can forward encrypted chat messages, but it does not have the AES session key. Because of this, the server should not be able to read the original chat message.

In this project, the server can still see some basic application metadata after TLS is terminated on the server side. For example, it can process who is sending a message, who should receive it, the nonce, the counter, and the ciphertext. However, the server should not be able to read the original message text because the chat message is encrypted on the client side.

Another threat is message modification. An attacker could try to change parts of the encrypted message, such as the ciphertext, nonce, counter, sender, or receiver information. The application uses AES-GCM with associated data, so these changes should be detected during decryption. If the message data was changed, the receiver rejects the message.

The application also considers replay attacks. In a replay attack, an attacker sends an old encrypted message again. The attacker does not need to understand the message to do this. To reduce this risk, every encrypted message has a counter. The receiver stores the last accepted counter for each sender and rejects messages with old or already used counter values.

There is also a security risk during key exchange. An attacker or malicious server could try to replace a public key and make the users create a session key with the wrong party. To reduce this risk, the application shows a public key fingerprint and manual acceptance is required with the `/accept username` command. This is not the same as a full certificate or PKI system for user identity, but it gives users a way to manually check the key.

Some attacks are outside the scope of this project. The application does not protect against malware on the client device, stolen passwords, weak passwords, or a malicious user who is already part of the conversation. It also does not support offline messages or long-term identity management.

Because of these assumptions, the project mainly protects against attacks during message transmission. It focuses on TLS transport protection, message confidentiality, message integrity, replay protection, and basic protection against public key substitution during key exchange.

## 4. System Architecture

The application is made as a simple client-server system. The server is used so that clients can connect and exchange data. Clients connect to the server using sockets, but the socket connection is wrapped with TLS. This means that the transport between client and server is encrypted.

The project is separated into a few Python files, which makes the code easier to follow because every file has its own purpose and function.

The `server.py` file contains the main server code. It accepts new client connections, wraps them with TLS, handles registration and login requests, and keeps track of users who are currently connected. During key exchange, the server forwards public keys between clients. During chat communication, it forwards encrypted messages. The server does not decrypt chat messages because it does not have the end-to-end session keys.

The `client.py` file contains the client code. The client connects to the server using TLS. After starting the client, the user can register, log in, choose a chat partner, start key exchange, accept a public key fingerprint, and send messages. The client does encryption and decryption locally, so plaintext chat messages stay on the client side.

The `auth_utils.py` file is used for authentication. It creates and uses a local SQLite database for user accounts. Passwords are not stored directly. Instead, this file creates salts, hashes passwords, registers new users, and verifies login attempts.

The `crypto_utils.py` file contains the cryptographic functions. It is used for generating X25519 key pairs, loading public keys, creating public key fingerprints, deriving session keys with HKDF-SHA256, generating nonces, and encrypting or decrypting messages with AES-GCM.

The `protocol.py` file defines how messages are sent over sockets. Messages are sent as JSON objects. Before every JSON message, the application sends a small fixed-size header with the message length. This is used so the receiver knows how many bytes it needs to read.

The `generate_tls_cert.py` file is used to generate a local self-signed TLS certificate for testing. It creates `cert.pem` and `key.pem`. These files are used by the server and client for TLS transport protection. They are local generated files and should not be committed to GitHub.

The communication is split into three main phases. First, the user registers or logs in over the TLS-protected connection. After that, two clients perform key exchange by sending public keys through the server and accepting the fingerprint manually. When the session key is created, users can send end-to-end encrypted messages.

The server is important because it connects users, but it should not be trusted with chat message content. TLS protects the transport to the server, while end-to-end encryption protects the message content from the server. Private keys, session keys, encryption, and decryption stay on the client side.

## 5. Authentication Design

The application has a basic authentication system with registration and login. First, a user creates an account with a username and password. After that, the user can log in and enter the chat. This step is needed because the server has to know which username belongs to which active socket connection. For example, if `pero` sends a message to `marko`, the server must know whether `marko` is currently online and where to forward the message.

User accounts are stored in a local SQLite database called `chat.db`. The database stores three main values for each user: the username, a salt, and a password hash. The original password is not stored directly in the database, which is important because the database should not contain readable passwords.

When a new user registers, the application creates a random salt for that account. The password and the salt are then used to create a hash with PBKDF2-HMAC-SHA256. The salt makes the stored hash different even if two users choose the same password.

During login, the application looks up the user in the database. If the username exists, it takes the stored salt and hashes the password that the user entered. The new hash is then compared with the stored hash. If they match, the server accepts the login and stores that user as connected. If they do not match, the login is rejected.

The hash comparison is done with `hmac.compare_digest()`. This is used instead of a normal comparison because it is safer for comparing secret values.

The database is used only for authentication. It does not store plaintext passwords, chat messages, private keys, or AES session keys. The `username` is unique because it is used as the primary key. The `salt` and `password_hash` are stored as BLOB values, which means they are binary values and not normal readable text.

TLS is also used during registration and login. This protects the password while it is being sent from the client to the server. Before TLS was added, Wireshark could show the login JSON and password. After TLS was added, the password is not visible in Wireshark as plaintext.

This authentication design is still simple, but it fits the goal of this project. It avoids storing plain text passwords, protects login transport with TLS, and gives the server a clear way to know which users are logged in and available for chat.

## 6. Key Exchange Design

Before encrypted messages can be sent, the two clients first need to create a shared session key. This key is later used for AES-GCM encryption and decryption. The session key is not sent through the network. Instead, both clients calculate it on their own side.

For this part, the application uses X25519 Diffie-Hellman. When a user logs in, the client creates a new private and public key pair for that session. The private key stays on that client and is never sent to the server or to another user. Only the public key is sent through the server.

The public keys are sent over the TLS-protected connection. This protects the transport channel. However, the server still forwards the public keys, so the application also uses public key fingerprints for manual verification.

The server only has the role of forwarding public keys. For example, if `pero` wants to start secure communication with `marko`, Pero’s client sends his public key to Marko through the server. Marko then gets a key exchange request and sees the fingerprint of Pero’s public key. If Marko accepts it, Marko’s public key is sent back to Pero.

The key exchange is not accepted completely automatically. When a client receives a public key, it shows a fingerprint of that key. The user then accepts it manually with the `/accept username` command. This is added because someone could try to replace a public key during key exchange. Manual fingerprint checking helps reduce that risk.

After both users accept the public keys, both clients use X25519 to calculate the same shared secret. That shared secret is not used directly as the AES key. The application first passes it through HKDF-SHA256 and creates a 256-bit AES session key. That final session key is stored only in memory and is used for encrypted messages between those two users.

The key exchange flow in this project looks like this:

```text
Client (user: Pero):
  creates private key + public key
  sends public key to Marko

Client (user: Marko):
  receives Pero's public key
  shows fingerprint
  user accepts with /accept pero
  creates shared secret
  sends Marko's public key back to Pero

Client (user: Pero):
  receives Marko's public key
  shows fingerprint
  user accepts with /accept marko
  creates the same shared secret

Both clients:
  use HKDF-SHA256 to derive the AES session key
```

## 7. TLS Transport Protection

TLS was added to protect the transport between the client and the server. Before this was added, the application used plain TCP sockets. Because of that, Wireshark could show the login JSON and password in plaintext. This was not good, even though the password was stored securely in the database.

After TLS was added, the client and server still communicate over port `5000`, but the socket is wrapped with TLS. The server uses `cert.pem` and `key.pem`, and the client loads `cert.pem` when creating the TLS connection. The certificate is self-signed and generated locally for this prototype.

TLS protects data while it travels between the client and the server. This means that login data, register data, public key exchange messages, and protocol JSON messages are not visible as plaintext in Wireshark. In Wireshark, the traffic appears as encrypted TLS data.

TLS does not replace end-to-end encryption. This is important. TLS protects the connection from client to server. After TLS is processed on the server side, the server can still see the application-level data that clients send to it. Because of this, E2EE is still needed for chat messages. E2EE makes sure that even the server receives only ciphertext for chat content.

The difference can be explained like this:

```text
TLS:
  protects client-server transport
  stops Wireshark from seeing login data and JSON messages as plaintext

E2EE:
  protects chat message content from the server
  server forwards ciphertext but cannot decrypt the real message
```

For this student prototype, the TLS certificate is self-signed. This is acceptable for local testing, but it is not the same as a production certificate from a trusted certificate authority. In a production system, proper certificate validation and trusted certificates should be used.

## 8. Secure Message Transmission

After the key exchange is finished, the clients can start sending encrypted messages. At this point, both clients have the same AES session key in memory. This key is used only for communication between those two users.

When a user writes a message, the message is not sent to the server as plaintext. The client first encrypts the message locally with AES-GCM. After that, only encrypted chat data is sent through the server.

The chat message contains the sender, receiver, nonce, counter, and ciphertext. It looks like this:

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

With TLS enabled, this JSON is also protected during transport between the client and the server. However, the important part is that the `ciphertext` field contains the end-to-end encrypted chat message. This means that the server does not get the plaintext chat message.

The nonce is created for each encrypted message. The ciphertext is the encrypted message content. The counter is used to track message order and help detect replayed messages.

The server receives this data and forwards it to the correct receiver. It does not need the AES session key because it does not decrypt the chat message. Its role is only to forward encrypted chat data between clients.

## 9. Replay and Tampering Protection

The application also needs to handle two basic problems: message tampering and replay attacks. Message tampering means that someone tries to change a message while it is being sent. A replay attack means that someone sends the same old encrypted message again and tries to make it look like a new message.

Tampering protection is mostly handled by AES-GCM. When the sender encrypts a message, AES-GCM also protects the encrypted data from changes. Because of that, the receiver can detect if something was changed before the message arrived. If the ciphertext, nonce, counter, sender, or receiver information is changed, decryption should fail.

This is important because the server is only supposed to forward messages. It should not be able to change the message and still make it look valid. The same applies to an attacker who can modify network traffic. If the encrypted message is changed, the receiver does not show a wrong plaintext message. Instead, the message is rejected.

Replay protection is done with message counters. Every encrypted message has a counter value. The sender increases this value for every new message sent to the same receiver. For example, the first message from `pero` to `marko` has counter `1`, the next one has counter `2`, and so on.

The receiver remembers the last accepted counter from each sender. If a message arrives with a counter that is smaller than or equal to the last accepted value, the client rejects it. For example, if Marko already accepted counter `3` from Pero, then another message from Pero with counter `2` or `3` should not be accepted.

The counter is also used as part of the AES-GCM associated data. This means that the counter itself is not hidden, but it is still protected from changes. If someone changes the counter, decryption should fail because the authenticated data no longer matches.

This is a simple form of replay protection, but it fits this project. It shows that encrypted messages should not only be private, but also protected from modification and from being accepted more than once.

## 10. Key Management Strategy

Key management is an important part of this project because the security of encrypted messages depends on how keys are created, used, and stored. In this application, chat encryption keys are not hardcoded in the source code. They are created when the client is running.

When a user logs in, the client creates a new X25519 private and public key pair for that session. The private key stays only on the client. It is not sent to the server and it is not saved in the database. The public key can be sent through the server because it is not secret.

After two users exchange and accept public keys, both clients calculate the same shared secret. This shared secret is then passed through HKDF-SHA256 to create a 256-bit AES session key. The session key is used for AES-GCM encryption and decryption between those two users.

The session key is stored only in memory while the client is running. It is not written to a file or stored in the SQLite database. This means that if the client is closed or restarted, the session key is lost. After that, users need to perform the key exchange again before they can send encrypted messages.

This design keeps the project simple and avoids storing long-term chat encryption keys on disk. It also reduces the risk of exposing session keys through project files or the database. The database is only used for user authentication data, not for encryption keys.

The application also uses fresh nonces for encrypted messages. A new nonce is generated for every AES-GCM message. This is important because reusing the same nonce with the same AES key would be unsafe.

TLS also uses certificate and key files for the local server transport. These are `cert.pem` and `key.pem`. They are generated locally with `generate_tls_cert.py` and are not committed to GitHub. They are only used for local TLS testing and transport protection.

Overall, the key management strategy is simple but clear. Private keys and session keys stay on the client side, public keys are only used for key exchange, and chat encryption keys are not hardcoded or stored permanently. This fits the goal of the project as a small secure chat prototype.

## 11. Security Analysis

This section explains how secure the application is based on the design that was implemented. The project is not a complete production chat system, but it covers the main security requirements for this prototype.

The main protection for chat content is end-to-end encryption. Messages are encrypted on the sender’s client before they are sent to the server. The server only receives encrypted chat data, together with metadata like sender, receiver, nonce, counter, and ciphertext. Since the server does not have the AES session key, it should not be able to read the plaintext chat message.

TLS adds another security layer. It protects the transport between client and server. This means that network monitoring tools like Wireshark should not see login data, passwords, or JSON protocol messages as plaintext. This is useful because registration and login require sending credentials to the server.

Message confidentiality depends on the AES session key staying secret. In this project, the session key is created only on the two clients after the X25519 key exchange. The key is not sent directly through the server. Because of this, the server can help with communication, but it should not learn the final key used for chat message encryption.

Message integrity is handled with AES-GCM. If someone changes the ciphertext, nonce, counter, sender, or receiver information, the receiver should detect that during decryption. In that case, the message is rejected. This is important because an attacker could try to modify encrypted data while it is being forwarded.

The project also includes replay protection with counters. Every encrypted message has a counter value. The receiver stores the last accepted counter for each sender. If an old message is sent again with the same or lower counter, the client rejects it. This helps prevent simple replay attacks.

The key exchange design also has some protection against public key substitution. When a client receives a public key, it shows a fingerprint. The user must manually accept the key with the `/accept username` command. This does not give the same level of trust as certificates or a full identity system, but it gives the user a way to check if the key is expected.

There are still some limitations. If the user does not actually check the fingerprint, then a man-in-the-middle attack during key exchange is still possible. The application also does not use a full PKI or certificate system for user identity. Because of that, identity verification is manual and depends on the user.

The application also does not protect the client device itself. If malware is running on the user’s computer, it could read messages before they are encrypted or after they are decrypted. This is outside the scope of this project, because the project focuses on protecting messages during transmission.

Another limitation is that session keys are stored only in memory. This is good because keys are not stored on disk, but it also means that users need to repeat the key exchange after restarting the client. The project also does not support offline messages, so both users need to be online for message delivery.

The TLS certificate used in this project is self-signed and generated locally. This is acceptable for a local prototype, but a production system should use trusted certificates and proper certificate validation.

Overall, the design provides a reasonable level of security for a student prototype. It protects transport with TLS, protects chat message content from the server with E2EE, detects message modification, uses secure key exchange, avoids hardcoded chat keys, uses fresh nonces, and rejects old message counters. The main remaining weakness is identity verification, because fingerprint checking is manual and there is no full certificate or PKI system for user identity.

## 12. Limitations

This project is made as a small secure chat prototype. It covers the main cryptographic parts, but it is still much simpler than a real chat application used in production. The goal was not to build a complete messaging platform, but to show how authentication, TLS transport protection, key exchange, encrypted messages, and replay protection can work together.

One limitation is that the application does not support offline messages. Both users need to be online at the same time. For example, if `pero` sends a message to `marko` while Marko is not connected, the server will not save that message for later. The server only forwards messages to users who are currently online.

Another limitation is how session keys are stored. In this project, session keys are kept only in memory while the client is running. They are not saved to a file or to the SQLite database. This is good because encryption keys are not stored permanently, but it also means that the key is lost when the client is closed. After restarting the client, users need to do the key exchange again.

The application also does not have a full public key infrastructure for user identity. Because of that, the application cannot automatically prove that a public key really belongs to a specific user. Instead, it shows a public key fingerprint and the user has to manually accept it. This helps against public key substitution, but it still depends on the user checking the fingerprint properly.

The TLS certificate is self-signed and generated locally. This is fine for local testing, but it is not the same as a trusted production certificate. In a production system, the server certificate should be properly validated and issued by a trusted certificate authority or internal CA.

The project also assumes that the client device is safe. If an attacker already controls the user’s computer, then encryption cannot fully help. The attacker could read messages before they are encrypted or after they are decrypted. This kind of attack is outside the scope of this project, because the focus is on protecting messages while they travel through the server.

The authentication system is also basic. Passwords are stored as salted hashes and sent over TLS, which is safer than plaintext storage and plaintext transport. However, the application does not include features like password reset, account lockout, multi-factor authentication, or password strength rules.

Replay protection is also simple. The application uses increasing counters and rejects old counter values. This works for this local real-time prototype, but a larger real-world system would need a more complete protocol for different network conditions, message ordering, and offline delivery.

Overall, these limitations are acceptable for this project because the application is made to demonstrate the main ideas of secure communication. It shows authentication, TLS transport protection, key exchange, encrypted messaging, nonce usage, integrity protection, and basic replay protection, but it is not a full production-ready chat system.

## 13. Conclusion

This project shows how a simple chat application can use cryptographic methods to protect communication between two users. The application supports user registration, login, TLS-protected client-server transport, key exchange, encrypted messages, and basic replay protection. Even though the server is needed for forwarding data between clients, it does not have access to the plaintext chat messages.

The most important part of the project is end-to-end encryption. Messages are encrypted on the sender’s client and decrypted only on the receiver’s client. The server only forwards encrypted chat data, such as nonce, counter, and ciphertext. Because the AES session key is created and stored only on the clients, the server should not be able to read the chat message content.

TLS was added to protect the communication channel between clients and the server. This prevents tools like Wireshark from showing login data or protocol messages as readable plaintext. However, TLS is not a replacement for end-to-end encryption, because TLS protects transport only up to the server. E2EE is still needed to keep chat message content hidden from the server.

The project also shows how different security mechanisms work together. Authentication is used so the server can identify logged-in users. X25519 Diffie-Hellman is used for key exchange, and HKDF-SHA256 is used to derive the AES session key. AES-GCM is used for encrypted message transmission, while counters are used to reduce the risk of replay attacks.

The application is still only a prototype, so it has some limitations. It does not support offline messages or automatic identity verification. Public key verification is done manually with fingerprints, session keys are stored only in memory, and the TLS certificate is self-signed for local testing. Because of that, the application is not meant to be a full production chat system.

Overall, the project meets its main goal. It demonstrates the basic design of a secure chat system and shows how authentication, TLS transport protection, key exchange, encryption, integrity protection, nonce usage, and replay protection can be implemented in Python.
