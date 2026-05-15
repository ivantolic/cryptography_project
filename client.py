import socket
import getpass
import threading
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import x25519

from crypto_utils import (
    generate_x25519_key_pair,
    derive_shared_key,
    fingerprint_public_key,
)
from protocol import send_json, receive_json


HOST = "127.0.0.1"
PORT = 5000


current_partner: Optional[str] = None
partner_lock = threading.Lock()

private_key: Optional[x25519.X25519PrivateKey] = None
public_key_b64: Optional[str] = None

session_keys: dict[str, bytes] = {}
session_keys_lock = threading.Lock()

pending_key_exchanges: dict[str, str] = {}
pending_key_exchanges_lock = threading.Lock()

sent_key_exchanges_to: set[str] = set()
sent_key_exchanges_lock = threading.Lock()


def connect_to_server() -> socket.socket:
    """
    Connects the client to the local chat server.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    return client_socket


def set_current_partner(username: str) -> None:
    """
    Sets the current outgoing chat partner.
    """
    global current_partner

    with partner_lock:
        current_partner = username


def get_current_partner() -> Optional[str]:
    """
    Returns the current outgoing chat partner.
    """
    with partner_lock:
        return current_partner


def set_session_key(username: str, key: bytes) -> None:
    """
    Stores a derived session key for a specific chat partner.
    """
    with session_keys_lock:
        session_keys[username] = key


def get_session_key(username: str) -> Optional[bytes]:
    """
    Returns the stored session key for a specific chat partner.
    """
    with session_keys_lock:
        return session_keys.get(username)


def list_session_key_users() -> list[str]:
    """
    Returns users with established session keys.
    """
    with session_keys_lock:
        return list(session_keys.keys())


def store_pending_key_exchange(username: str, peer_public_key_b64: str) -> None:
    """
    Stores a received public key until the user manually accepts it.
    """
    with pending_key_exchanges_lock:
        pending_key_exchanges[username] = peer_public_key_b64


def get_pending_key_exchange(username: str) -> Optional[str]:
    """
    Returns a pending public key for a user, if it exists.
    """
    with pending_key_exchanges_lock:
        return pending_key_exchanges.get(username)


def remove_pending_key_exchange(username: str) -> None:
    """
    Removes a pending key exchange after it is accepted.
    """
    with pending_key_exchanges_lock:
        pending_key_exchanges.pop(username, None)


def list_pending_key_exchanges() -> list[str]:
    """
    Returns users with pending key exchange requests.
    """
    with pending_key_exchanges_lock:
        return list(pending_key_exchanges.keys())


def has_sent_key_exchange_to(username: str) -> bool:
    """
    Checks whether this client has already sent its public key to a user.
    """
    with sent_key_exchanges_lock:
        return username in sent_key_exchanges_to


def mark_key_exchange_sent(username: str) -> None:
    """
    Marks that this client has sent its public key to a user.
    """
    with sent_key_exchanges_lock:
        sent_key_exchanges_to.add(username)


def send_key_exchange(client_socket: socket.socket, sender: str, recipient: str) -> None:
    """
    Sends this client's public key to another user.

    The private key never leaves this client.
    """
    if public_key_b64 is None:
        print("[ERROR] Local public key is not available.")
        return

    send_json(client_socket, {
        "type": "key_exchange",
        "from": sender,
        "to": recipient,
        "public_key": public_key_b64,
    })

    mark_key_exchange_sent(recipient)
    print(f"[KEYX] Public key sent to {recipient}.")


def register(client_socket: socket.socket) -> None:
    """
    Sends a register request to the server.
    """
    print("\n--- Register ---")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    send_json(client_socket, {
        "type": "register",
        "username": username,
        "password": password,
    })

    response = receive_json(client_socket)
    print(f"[{response.get('status').upper()}] {response.get('message')}")


def login(client_socket: socket.socket) -> str | None:
    """
    Sends a login request to the server.
    """
    print("\n--- Login ---")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    send_json(client_socket, {
        "type": "login",
        "username": username,
        "password": password,
    })

    response = receive_json(client_socket)
    print(f"[{response.get('status').upper()}] {response.get('message')}")

    if response.get("status") == "success":
        return username

    return None


def main_menu(client_socket: socket.socket) -> str | None:
    """
    Displays the authentication menu.
    """
    while True:
        print("\nSecure E2EE Chat")
        print("----------------")
        print("1) Register")
        print("2) Login")
        print("3) Exit")

        choice = input("> ").strip()

        if choice == "1":
            register(client_socket)

        elif choice == "2":
            username = login(client_socket)

            if username:
                return username

        elif choice == "3":
            send_json(client_socket, {"type": "logout"})
            try:
                receive_json(client_socket)
            except Exception:
                pass
            return None

        else:
            print("Invalid option. Please choose 1, 2, or 3.")


def receive_messages(client_socket: socket.socket, own_username: str) -> None:
    """
    Continuously listens for incoming messages from the server.

    Incoming chat messages are shown immediately.
    Key exchange messages are stored as pending requests and must be
    manually accepted with /accept username.
    """
    while True:
        try:
            message = receive_json(client_socket)
            message_type = message.get("type")

            if message_type == "chat":
                sender = message.get("from")
                plaintext = message.get("message")

                print(f"\n[{sender}] {plaintext}")

                if sender and sender != own_username and get_current_partner() is None:
                    set_current_partner(sender)
                    print(f"[INFO] Current chat partner automatically set to '{sender}'.")

                print("> ", end="", flush=True)

            elif message_type == "key_exchange":
                sender = message.get("from")
                peer_public_key = message.get("public_key")

                if not sender or not peer_public_key:
                    print("\n[KEYX ERROR] Invalid key exchange message.")
                    print("> ", end="", flush=True)
                    continue

                store_pending_key_exchange(sender, peer_public_key)

                try:
                    fingerprint = fingerprint_public_key(peer_public_key)
                except Exception:
                    fingerprint = "INVALID-FINGERPRINT"

                print(f"\n[KEYX] Key exchange request from {sender}.")
                print(f"[KEYX] Public key fingerprint: {fingerprint}")
                print(f"[KEYX] Verify this fingerprint out-of-band, then type: /accept {sender}")

                if get_current_partner() is None:
                    set_current_partner(sender)
                    print(f"[INFO] Current chat partner automatically set to '{sender}'.")

                print("> ", end="", flush=True)

            elif message_type == "response":
                status = message.get("status", "").upper()
                text = message.get("message", "")

                # Avoid printing noisy confirmations for every sent message/key.
                if text not in ("Message delivered.", "Public key delivered."):
                    print(f"\n[{status}] {text}")
                    print("> ", end="", flush=True)

            else:
                print(f"\n[SERVER] {message}")
                print("> ", end="", flush=True)

        except ConnectionError:
            print("\n[ERROR] Connection to server was lost.")
            break

        except OSError:
            break

        except Exception as e:
            print(f"\n[ERROR] Receiver thread stopped: {e}")
            break


def print_chat_help() -> None:
    """
    Prints available chat commands.
    """
    print("\nChat started.")
    print("Commands:")
    print("  /to username       choose who you want to send messages to")
    print("  /keyx username     send your X25519 public key to a user")
    print("  /pending           show pending key exchange requests")
    print("  /accept username   accept a pending key exchange after verifying fingerprint")
    print("  /keys              show users with established session keys")
    print("  /who               show current chat partner")
    print("  /quit              exit chat")
    print("\nExample:")
    print("  /to marko")
    print("  /keyx marko")
    print("  /pending")
    print("  /accept marko")
    print("  bok marko\n")


def handle_accept_key_exchange(client_socket: socket.socket, username: str, peer_username: str) -> None:
    """
    Accepts a pending key exchange request.

    This derives and stores the shared session key. If this client has not yet
    sent its own public key to the peer, it sends it as a response.
    """
    global private_key

    if private_key is None:
        print("[KEYX ERROR] Local private key is not available.")
        return

    peer_public_key = get_pending_key_exchange(peer_username)

    if peer_public_key is None:
        print(f"[KEYX] No pending key exchange from {peer_username}.")
        return

    try:
        fingerprint = fingerprint_public_key(peer_public_key)
        shared_key = derive_shared_key(private_key, peer_public_key)

        set_session_key(peer_username, shared_key)
        remove_pending_key_exchange(peer_username)

        if get_current_partner() is None:
            set_current_partner(peer_username)

        print(f"[KEYX] Accepted key exchange from {peer_username}.")
        print(f"[KEYX] Accepted fingerprint: {fingerprint}")
        print(f"[KEYX] Shared session key established with {peer_username}.")

        # If we have not already sent our public key to this user, send it now.
        # This lets the other side complete the exchange manually as well.
        if not has_sent_key_exchange_to(peer_username):
            send_key_exchange(client_socket, username, peer_username)

    except Exception as e:
        print(f"[KEYX ERROR] Could not accept key exchange from {peer_username}: {e}")


def chat_loop(client_socket: socket.socket, username: str) -> None:
    """
    Starts the plaintext chat loop.

    This version still sends plaintext chat messages.
    X25519 key exchange with manual fingerprint acceptance is supported.
    AES-GCM encrypted messaging will be added in the next phase.
    """
    receiver_thread = threading.Thread(
        target=receive_messages,
        args=(client_socket, username),
        daemon=True,
    )
    receiver_thread.start()

    print_chat_help()

    while True:
        user_input = input("> ").strip()

        if not user_input:
            continue

        if user_input == "/quit":
            send_json(client_socket, {"type": "logout"})
            break

        if user_input == "/who":
            partner = get_current_partner()

            if partner:
                print(f"Current chat partner: {partner}")
            else:
                print("No chat partner selected. Use: /to username")

            continue

        if user_input == "/keys":
            users = list_session_key_users()

            if users:
                print("Established session keys with:", ", ".join(users))
            else:
                print("No session keys established yet.")

            continue

        if user_input == "/pending":
            pending_users = list_pending_key_exchanges()

            if pending_users:
                print("Pending key exchange requests from:", ", ".join(pending_users))
                print("Use /accept username after verifying the fingerprint.")
            else:
                print("No pending key exchange requests.")

            continue

        if user_input == "/accept":
            print("Usage: /accept username")
            continue

        if user_input.startswith("/accept "):
            peer_username = user_input.removeprefix("/accept ").strip()

            if not peer_username:
                print("Usage: /accept username")
                continue

            if peer_username == username:
                print("You cannot accept a key exchange from yourself.")
                continue

            handle_accept_key_exchange(client_socket, username, peer_username)
            continue

        if user_input == "/to":
            print("Usage: /to username")
            continue

        if user_input.startswith("/to "):
            partner = user_input.removeprefix("/to ").strip()

            if not partner:
                print("Usage: /to username")
                continue

            if partner == username:
                print("You cannot chat with yourself. Choose another user.")
                continue

            set_current_partner(partner)
            print(f"Now chatting with {partner}.")
            continue

        if user_input == "/keyx":
            print("Usage: /keyx username")
            continue

        if user_input.startswith("/keyx "):
            recipient = user_input.removeprefix("/keyx ").strip()

            if not recipient:
                print("Usage: /keyx username")
                continue

            if recipient == username:
                print("You cannot perform key exchange with yourself.")
                continue

            send_key_exchange(client_socket, username, recipient)
            set_current_partner(recipient)
            print("[KEYX] Waiting for peer public key. Accept it with /accept username when received.")
            continue

        if user_input.startswith("/"):
            print("Unknown command. Available commands: /to, /keyx, /pending, /accept, /keys, /who, /quit")
            continue

        recipient = get_current_partner()

        if recipient is None:
            print("No chat partner selected. Use: /to username")
            continue

        send_json(client_socket, {
            "type": "chat",
            "from": username,
            "to": recipient,
            "message": user_input,
        })


def main() -> None:
    """
    Starts the client application.
    """
    global private_key, public_key_b64

    client_socket = None

    try:
        client_socket = connect_to_server()
        print("[CONNECTED] Connected to server.")

        username = main_menu(client_socket)

        if username:
            private_key, public_key_b64 = generate_x25519_key_pair()

            print(f"\nWelcome, {username}.")
            print("[KEYX] X25519 key pair generated for this session.")
            print(f"[KEYX] Your public key fingerprint: {fingerprint_public_key(public_key_b64)}")

            chat_loop(client_socket, username)

    except ConnectionRefusedError:
        print("[ERROR] Could not connect to server. Is server.py running?")

    except ConnectionError:
        print("[ERROR] Connection to server was lost.")

    finally:
        if client_socket:
            client_socket.close()


if __name__ == "__main__":
    main()