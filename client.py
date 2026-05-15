import socket
import getpass

from protocol import send_json, receive_json


HOST = "127.0.0.1"
PORT = 5000


def connect_to_server() -> socket.socket:
    """
    Connects the client to the local chat server.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    return client_socket


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

    Returns:
        username if login succeeds, otherwise None.
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

    Returns:
        authenticated username, or None if user exits.
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


def main() -> None:
    """
    Starts the client application.
    """
    try:
        client_socket = connect_to_server()
        print("[CONNECTED] Connected to server.")

        username = main_menu(client_socket)

        if username:
            print(f"\nWelcome, {username}.")
            print("Chat functionality will be added in the next step.")

    except ConnectionRefusedError:
        print("[ERROR] Could not connect to server. Is server.py running?")

    except ConnectionError:
        print("[ERROR] Connection to server was lost.")

    finally:
        try:
            client_socket.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()