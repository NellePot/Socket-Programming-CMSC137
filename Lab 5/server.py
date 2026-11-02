"""starter only to test connection"""

import socket

HOST = "127.0.0.1"
PORT = 5000


def main():
    # context manager so the listening socket closes cleanly on exit
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            connection, address = server.accept()
            with connection:
                print(f"Connected by {address}")
                # newline marks the end of one message
                reader = connection.makefile("r", encoding="utf-8")
                message = reader.readline()
                if not message:
                    continue

                message = message.rstrip("\r\n")
                print(f"Client says: {message}")
                connection.sendall(f"Server received: {message}\n".encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped.")
