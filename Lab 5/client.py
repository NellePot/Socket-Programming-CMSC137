"""starter only to test connection"""

import socket

HOST = "127.0.0.1"
PORT = 5000


def main():
    message = input("Message to send: ")

    with socket.create_connection((HOST, PORT)) as client:
        client.sendall(f"{message}\n".encode("utf-8"))
        # read one newline-terminated reply from the server.
        reader = client.makefile("r", encoding="utf-8")
        reply = reader.readline()

    print(f"Server replied: {reply.rstrip()}")


if __name__ == "__main__":
    main()
