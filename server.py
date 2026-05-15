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


def forward_chat_message(message: dict) -> bool:
    """
    Forwards a chat message to the intended recipient.

    Returns True if the recipient is online, False otherwise.
    """
    recipient = message.get("to")

    with clients_lock:
        recipient_socket = connected_clients.get(recipient)

    if recipient_socket is None:
        return False

    send_json(recipient_socket, message)
    return True


def handle_client(client_socket: socket.socket, client_address: tuple) -> None:
    """
    Handles one connected client.

    Supported phases in this version:
    - register
    - login
    - plaintext chat forwarding

    E2EE will be added later.
    """
    print(f"[NEW CONNECTION] {client_address} connected.")

    authenticated_user: Optional[str] = None

    try:
        while True:
            message = receive_json(client_socket)
            message_type = message.get("type")

            if message_type == "register":
                username = message.get("username", "")
                password = message.get("password", "")

                success = register_user(username, password)

                if success:
                    send_json(client_socket, make_success("Registration successful."))
                    print(f"[REGISTER] User '{username}' registered.")
                else:
                    send_json(client_socket, make_error("Registration failed. Username may already exist."))

            elif message_type == "login":
                username = message.get("username", "")
                password = message.get("password", "")

                success = verify_user(username, password)

                if success:
                    authenticated_user = username
                    register_connected_user(username, client_socket)

                    send_json(client_socket, make_success("Login successful."))
                    print(f"[LOGIN] User '{username}' logged in from {client_address}.")
                else:
                    send_json(client_socket, make_error("Invalid username or password."))

            elif message_type == "chat":
                if authenticated_user is None:
                    send_json(client_socket, make_error("You must be logged in before sending messages."))
                    continue

                sender = message.get("from")
                recipient = message.get("to")
                plaintext = message.get("message")

                if sender != authenticated_user:
                    send_json(client_socket, make_error("Sender username does not match authenticated user."))
                    continue

                delivered = forward_chat_message(message)

                if delivered:
                    print(f"[CHAT] {sender} -> {recipient}: {plaintext}")
                    send_json(client_socket, make_success("Message delivered."))
                else:
                    send_json(client_socket, make_error(f"User '{recipient}' is not online."))

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