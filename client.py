import socket
import getpass
import threading
from typing import Optional

from protocol import send_json, receive_json


HOST = "127.0.0.1"
PORT = 5000


current_partner: Optional[str] = None
partner_lock = threading.Lock()


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
    If no chat partner is selected yet, the sender automatically becomes
    the current chat partner so the user can reply directly.
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

            elif message_type == "response":
                status = message.get("status", "").upper()
                text = message.get("message", "")

                # Avoid printing delivery confirmations for every sent message.
                if text != "Message delivered.":
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
    print("  /to username   choose who you want to send messages to")
    print("  /who           show current chat partner")
    print("  /quit          exit chat")
    print("\nExample:")
    print("  /to marko")
    print("  bok marko\n")


def chat_loop(client_socket: socket.socket, username: str) -> None:
    """
    Starts the plaintext chat loop.

    This version is intentionally plaintext.
    E2EE will be added in the cryptographic phase.
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
    client_socket = None

    try:
        client_socket = connect_to_server()
        print("[CONNECTED] Connected to server.")

        username = main_menu(client_socket)

        if username:
            print(f"\nWelcome, {username}.")
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