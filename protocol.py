import json
import socket
from typing import Any, Dict


HEADER_SIZE = 4
ENCODING = "utf-8"


def send_json(sock: socket.socket, message: Dict[str, Any]) -> None:
    """
    Sends a JSON message over a socket.

    Message format:
    [4-byte length header][JSON payload]

    The length header tells the receiver how many bytes to read.
    This prevents problems with partial socket reads.
    """
    json_data = json.dumps(message).encode(ENCODING)
    message_length = len(json_data)

    header = message_length.to_bytes(HEADER_SIZE, byteorder="big")
    sock.sendall(header + json_data)


def receive_exact(sock: socket.socket, length: int) -> bytes:
    """
    Receives exactly 'length' bytes from a socket.

    Raises ConnectionError if the connection closes before enough data is received.
    """
    data = b""

    while len(data) < length:
        chunk = sock.recv(length - len(data))

        if not chunk:
            raise ConnectionError("Socket connection closed unexpectedly.")

        data += chunk

    return data


def receive_json(sock: socket.socket) -> Dict[str, Any]:
    """
    Receives a JSON message from a socket.

    First reads a fixed-size length header, then reads the JSON payload.
    """
    header = receive_exact(sock, HEADER_SIZE)
    message_length = int.from_bytes(header, byteorder="big")

    if message_length <= 0:
        raise ValueError("Invalid message length.")

    json_data = receive_exact(sock, message_length)
    message = json.loads(json_data.decode(ENCODING))

    if not isinstance(message, dict):
        raise ValueError("Invalid message format. Expected JSON object.")

    return message


def make_response(status: str, message: str) -> Dict[str, str]:
    """
    Creates a standard server response.
    """
    return {
        "type": "response",
        "status": status,
        "message": message,
    }


def make_error(message: str) -> Dict[str, str]:
    """
    Creates a standard error response.
    """
    return make_response("error", message)


def make_success(message: str) -> Dict[str, str]:
    """
    Creates a standard success response.
    """
    return make_response("success", message)


if __name__ == "__main__":
    example_login = {
        "type": "login",
        "username": "ivan",
        "password": "test123",
    }

    encoded = json.dumps(example_login)
    decoded = json.loads(encoded)

    print("Protocol test")
    print("-------------")
    print("Original:", example_login)
    print("Encoded:", encoded)
    print("Decoded:", decoded)