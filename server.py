import socket
import threading
from typing import Optional

from auth_utils import init_db, register_user, verify_user
from protocol import receive_json, send_json, make_success, make_error


HOST = "127.0.0.1"
PORT = 5000

connected_clients: dict[str, socket.socket] = {}
clients_lock = threading.Lock()


def register_connected_user(username: str, client_socket: socket.socket) -> None:
    """
    Stores an authenticated user's socket connection.
    """
    with clients_lock:
        connected_clients[username] = client_socket


def remove_connected_user(username: Optional[str]) -> None:
    """
    Removes a disconnected user from the active clients list.
    """
    if username is None:
        return

    with clients_lock:
        if username in connected_clients:
            del connected_clients[username]


def get_recipient_socket(recipient: str) -> Optional[socket.socket]:
    """
    Returns the socket for an online recipient.
    """
    with clients_lock:
        return connected_clients.get(recipient)


def forward_message_to_recipient(message: dict) -> bool:
    """
    Forwards a message to the intended recipient.

    Used for both encrypted chat messages and key exchange messages.
    """
    recipient = message.get("to")

    if not recipient:
        return False

    recipient_socket = get_recipient_socket(recipient)

    if recipient_socket is None:
        return False

    send_json(recipient_socket, message)
    return True


def validate_authenticated_sender(
    message: dict,
    authenticated_user: Optional[str],
    client_socket: socket.socket,
) -> bool:
    """
    Checks whether the client is logged in and whether the message sender
    matches the authenticated username.
    """
    if authenticated_user is None:
        send_json(client_socket, make_error("You must be logged in before sending messages."))
        return False

    sender = message.get("from")

    if sender != authenticated_user:
        send_json(client_socket, make_error("Sender username does not match authenticated user."))
        return False

    return True


def handle_register(message: dict, client_socket: socket.socket) -> None:
    """
    Handles user registration.
    """
    username = message.get("username", "")
    password = message.get("password", "")

    success = register_user(username, password)

    if success:
        send_json(client_socket, make_success("Registration successful."))
        print(f"[REGISTER] User '{username}' registered.")
    else:
        send_json(client_socket, make_error("Registration failed. Username may already exist."))


def handle_login(
    message: dict,
    client_socket: socket.socket,
    client_address: tuple,
) -> Optional[str]:
    """
    Handles user login.
    """
    username = message.get("username", "")
    password = message.get("password", "")

    success = verify_user(username, password)

    if success:
        register_connected_user(username, client_socket)
        send_json(client_socket, make_success("Login successful."))
        print(f"[LOGIN] User '{username}' logged in from {client_address}.")
        return username

    send_json(client_socket, make_error("Invalid username or password."))
    return None


def handle_chat(
    message: dict,
    authenticated_user: Optional[str],
    client_socket: socket.socket,
) -> None:
    """
    Handles encrypted chat forwarding.

    The server only forwards nonce, counter, and ciphertext.
    It does not have the session key and cannot read message contents.
    """
    if not validate_authenticated_sender(message, authenticated_user, client_socket):
        return

    sender = message.get("from")
    recipient = message.get("to")
    nonce = message.get("nonce")
    ciphertext = message.get("ciphertext")
    counter = message.get("counter")

    if not recipient or not nonce or not ciphertext or counter is None:
        send_json(client_socket, make_error("Invalid encrypted chat message."))
        return

    if not isinstance(counter, int) or counter <= 0:
        send_json(client_socket, make_error("Invalid message counter."))
        return

    delivered = forward_message_to_recipient(message)

    if delivered:
        print(f"[CHAT] Encrypted message #{counter} forwarded from {sender} to {recipient}.")
        send_json(client_socket, make_success("Message delivered."))
    else:
        send_json(client_socket, make_error(f"User '{recipient}' is not online."))


def handle_key_exchange(
    message: dict,
    authenticated_user: Optional[str],
    client_socket: socket.socket,
) -> None:
    """
    Handles X25519 public key forwarding.

    The server only relays public keys between clients.
    It never receives private keys and cannot derive the shared session key.
    """
    if not validate_authenticated_sender(message, authenticated_user, client_socket):
        return

    sender = message.get("from")
    recipient = message.get("to")
    public_key = message.get("public_key")

    if not recipient or not public_key:
        send_json(client_socket, make_error("Invalid key exchange message."))
        return

    delivered = forward_message_to_recipient(message)

    if delivered:
        print(f"[KEY EXCHANGE] Public key forwarded from {sender} to {recipient}.")
        send_json(client_socket, make_success("Public key delivered."))
    else:
        send_json(client_socket, make_error(f"User '{recipient}' is not online."))


def handle_client(client_socket: socket.socket, client_address: tuple) -> None:
    """
    Handles one connected client.

    Supported phases:
    - authentication phase: register/login
    - key exchange phase: X25519 public key forwarding
    - secure message transmission phase: AES-GCM encrypted message forwarding
    """
    print(f"[NEW CONNECTION] {client_address} connected.")

    authenticated_user: Optional[str] = None

    try:
        while True:
            message = receive_json(client_socket)
            message_type = message.get("type")

            if message_type == "register":
                handle_register(message, client_socket)

            elif message_type == "login":
                authenticated_user = handle_login(message, client_socket, client_address)

            elif message_type == "chat":
                handle_chat(message, authenticated_user, client_socket)

            elif message_type == "key_exchange":
                handle_key_exchange(message, authenticated_user, client_socket)

            elif message_type == "logout":
                if authenticated_user:
                    print(f"[LOGOUT] User '{authenticated_user}' logged out.")

                send_json(client_socket, make_success("Logged out."))
                break

            else:
                send_json(client_socket, make_error("Unknown message type."))

    except ConnectionError:
        print(f"[DISCONNECTED] {client_address} disconnected.")

    except Exception as e:
        print(f"[ERROR] {client_address}: {e}")

    finally:
        remove_connected_user(authenticated_user)
        client_socket.close()
        print(f"[CLOSED] Connection with {client_address} closed.")


def start_server() -> None:
    """
    Starts the chat server.
    """
    init_db()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print("[SERVER STARTED]")
    print(f"Listening on {HOST}:{PORT}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True,
            )

            client_thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print("\n[SERVER STOPPED]")

    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()