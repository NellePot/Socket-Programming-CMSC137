# server.py
# Name: Marinelle Joan U. Tambolero
# CMSC 141 - LE5.2 (RSA chat server / relay)

import socket
import threading

# ================= SETTINGS =================
HOST = '0.0.0.0'    # listen on every network interface of this laptop
PORT = 55555        # must be the same as PORT in client.py

# ================= SERVER SOCKET =================
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # avoid "port already in use"
server.bind((HOST, PORT))
server.listen()

clients = []                        # all connected client sockets
clients_lock = threading.Lock()     # only one thread edits the list at a time


def remove_client(client):
    """Removes a client from the list and closes its socket safely."""
    with clients_lock:
        if client in clients:
            clients.remove(client)
    client.close()


def broadcast(message, sender):
    """Sends one encrypted line to every client except the sender."""
    with clients_lock:
        targets = [c for c in clients if c is not sender]   # copy, so we don't loop while editing
    for c in targets:
        try:
            c.sendall(message)
        except OSError:
            remove_client(c)        # drop broken connections


def handle_client(client):
    """Runs in its own thread: reads lines from one client and relays them."""
    reader = client.makefile('rb')  # lets us read one full line at a time
    while True:
        try:
            line = reader.readline()        # waits until "\n" arrives
            if not line:                    # empty = client disconnected
                break
            print(f"[Relay] {line.decode('utf-8').strip()}")
            broadcast(line, client)
        except OSError:
            break
    remove_client(client)
    print("A client disconnected.")


def receive_connections():
    """Main loop: accepts new clients and gives each one a thread."""
    print(f"Server is running and listening on {HOST}:{PORT}...")
    while True:
        client, address = server.accept()
        print(f"Connected with {address}")
        with clients_lock:
            clients.append(client)
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    receive_connections()