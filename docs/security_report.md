# Security Report: Secure E2EE Chat Application

## 1. Introduction

In this project a secure chat application was made using Python. The main goal of this project is to show how to protect messages between two users using cryptographic methods. The application uses one server and two or more clients to make communication between two users possible. Users can register, log in, exchange keys, and send messages in real time.

The main idea of this application is that the server should not be able to read the messages. The server is just used to forward data from one client to another. Messages are encrypted on the sender’s side and decrypted on the receiver’s side which is the basic idea of end-to-end encryption.

The application has three main parts. The first part is user authentication. Users log in with a username and password. Passwords are not saved as plain text, they are saved as salted password hashes in a local SQLite database. The second part is key exchange. Two clients exchange public keys and use X25519 Diffie-Hellman to create a shared secret. This shared secret is then used to create an AES session key. The third part is secure messaging. After the key exchange is finished, messages are encrypted with AES-GCM before they are sent through the server.

The project also has simple protection against message modification and replay attacks. AES-GCM checks if the encrypted message was changed. If someone changes the ciphertext or data of the message, decryption will fail. Replay protection is solved with help of counters where every message has a counter.

This application is only a student project. It does not have all features of a real chat application. For example, the application does not support offline messages, certificates, or full automatic identity verification. Because of that, users must manually check the public key fingerprint. The main purpose of this project is to show the basic security mechanisms used in a secure chat system, such as authentication, key exchange, encryption, nonce usage, and replay protection.

## 2. Security Goals

The main security goal of this chat application is to protect communication between two users. A user should be able to send a message to another user, and only that receiver should be able to read that message. Server in this context is just needed for forwarding of those messages, but it should not be able to see their content.

The first goal is message privacy. This means that messages should not be readable by the server or by another user who is not part of the specific conversation. Even if the server forwards the message, it should only see encrypted data.

The second goal is message integrity. The receiver should be able to see if a message was changed during transmission. If an attacker changes the encrypted message, the application should reject it instead of showing a modified message to the user.

The third goal is authentication. Users should not be able to use chat application without registering and logging in. The application should also avoid storing original passwords directly, because that would be unsafe if the local database was compromised.

The fourth goal is secure session setup. Before private messages can be sent, two clients need to agree on a shared session key. This key should not be sent directly over the network, and the server should not know it.

The fifth goal is replay protection. The application should not accept the same old encrypted message again as if it was a new message. This is important because an attacker may not understand the message, but could still try to send the same encrypted data again.

These goals define what the application tries to protect. The later sections explain how the project implements these goals using authentication, key exchange, AES-GCM encryption, nonces, and message counters.

## 3. Threat Model

The threat model explains what kind of attacks this chat application tries to protect against. The main focus is on protecting chat messages while they are being sent between two clients through the server. The server is needed for communication, but it should not be trusted with the plaintext message content.

In this project, the server can see basic message information. For example, it can see who is the sender of the message, who is receiver, the nonce, the counter, and the ciphertext. However, the server should not be able to read the original message because the message is encrypted on the client side. The session key is created and stored only on the clients.

One possible threat is passive network monitoring. This means that an attacker can observe the traffic between the client and the server. In that case, the attacker may see encrypted messages and public keys, but should not be able to read the plaintext chat messages without the session key.

Another threat is message modification. An attacker could try to change parts of the encrypted message, such as the ciphertext, nonce, counter, sender or receiver information. The application uses AES-GCM with associated data, so these changes should be detected during decryption. If the message data was changed, the receiver rejects the message.

The application also considers replay attacks. In a replay attack, an attacker sends an old encrypted message again. The attacker does not need to understand the message to do this. To reduce this risk, every encrypted message has a counter. The receiver stores the last accepted counter for each sender and rejects messages with old or already used counter values.

There is also a security risk during key exchange. An attacker could try to replace a public key and make the users create a session key with the wrong party. To reduce this risk, the application shows a public key fingerprint and manual acceptance is required with the `/accept username` command. This is not the same as a full certificate system, but it gives users a way to manually check the key.

Some attacks are outside the scope of this project. The application does not protect against malware on the client device, stolen passwords, weak passwords, or a malicious user who is already part of the conversation. It also does not support offline messages, certificates, or long-term identity management.

Because of these assumptions, the project mainly protects against attacks during message transmission. It focuses on message confidentiality, message integrity, replay protection, and basic protection against public key substitution during key exchange.

## 4. System Architecture

The application is made as a simple client-server system. The server is used so that clients can connect and exchange data. Clients connect to the server using TCP sockets. When one client sends something to another client, the data first goes to the server, and then the server forwards it to the correct user.

The project is separated into a few Python files which makes the code easier to follow, because every file has its own purpose and function.

The `server.py` file contains the main server code. It accepts new client connections and handles registration and login requests. It also keeps track of users who are currently connected. During key exchange, the server forwards public keys between clients. During chat communication, it forwards encrypted messages. The server does not decrypt those messages because it does not have the session keys.

The `client.py` file contains the client code. The client is used from the terminal. After starting the client, the user can register, log in, choose a chat partner, start key exchange, accept a public key fingerprint, and send messages. The client does the encryption and decryption locally, so plaintext messages stay on the client side.

The `auth_utils.py` file is used for authentication. It creates and uses a local SQLite database for user accounts. Passwords are not stored directly. Instead, this file creates salts, hashes passwords, registers new users, and verifies login attempts.

The `crypto_utils.py` file contains the cryptographic functions. It is used for generating X25519 key pairs, loading public keys, creating public key fingerprints, deriving session keys with HKDF, and encrypting or decrypting messages with AES-GCM.

The `protocol.py` file defines how messages are sent over sockets. Messages are sent as JSON objects. Before every JSON message, the application sends a small fixed-size header with the message length. This is used so the receiver knows how many bytes it needs to read.

The communication is split into three main phases. First, the user registers or logs in. After that, two clients perform key exchange by sending public keys through the server and accepting the fingerprint manually. When the session key is created, users can send encrypted messages.

The server is important because it connects users, but it should not be trusted with message content. It only forwards public keys and encrypted messages. Private keys, session keys, encryption, and decryption stay on the client side.

## 5. Authentication Design

The application has a basic authentication system with registration and login. First, a user creates an account with a username and password. After that, the user can log in and enter the chat. This step is needed because the server has to know which username belongs to which active socket connection. For example, if `pero` sends a message to `marko`, the server must know whether `marko` is currently online and where to forward the message.

User accounts are stored in a local SQLite database called `chat.db`. The database stores three main values for each user: the username, a salt, and a password hash. Original password is not stored directly in the database, which is important because the database should not contain readable passwords.

When a new user registers, the application creates a random salt for that account. The password and the salt are then used to create a hash with PBKDF2-HMAC-SHA256. The salt makes the stored hash more unique. For example, if two users choose the same password, their hashes should still be different because their salts are different.

During login, the application looks up the user in the database. If the username exists, it takes the stored salt and hashes the password that the user entered. The new hash is then compared with the stored hash. If they match, the server accepts the login and stores that user as connected. If they do not match, the login is rejected.

The hash comparison is done with `hmac.compare_digest()`. This is used instead of a normal comparison because it is safer for comparing secret values.

This authentication design is still simple, but it fits the goal of this project. It avoids storing plain text passwords and gives the server a clear way to know which users are logged in and available for chat.

## 6. Key Exchange Design

## 7. Secure Message Transmission

## 8. Replay and Tampering Protection

## 9. Key Management Strategy

## 10. Security Analysis

## 11. Limitations

## 12. Conclusion