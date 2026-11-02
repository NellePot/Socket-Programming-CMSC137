import socket
from crc_module import mod2div

SHARED_KEY = "1001"
CRC_BITS = len(SHARED_KEY) - 1

# convert string of bits to text (8 bits = 1 character)
def bits_to_text(bits):
    text = ""
    for i in range(0, len(bits), 8):
        text += chr(int(bits[i:i+8], 2))
    return text

# helper function to sort votes in descending order
def get_votes(item):
    return item[1]

def run_receiver():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('192.168.254.110', 65432))
    server_socket.listen(1)
    print("[Receiver] Server listening for connections...")

    conn, addr = server_socket.accept()
    print(f"[Receiver] Connected to: {addr}")

    area, eligible, votes = None, None, {}
    error, done = False, False

    for line in conn.makefile("r", encoding="utf-8"):
        bits = line.strip()

        # too short to be a real message
        if len(bits) < 8 + CRC_BITS:
            error = True
            break

        # CRC check: a remainder with a 1 means the data was corrupted
        if "1" in mod2div(bits, SHARED_KEY):
            error = True
            break

        text = bits_to_text(bits[:-CRC_BITS])    # remove CRC bits, decode
        print(f"[Receiver] Received text: {text}")

        parts = text.split("|")
        if parts[0] == "AREA":
            area = parts[1]
        elif parts[0] == "NOMINEE":
            votes[parts[1]] = int(parts[2])
        elif parts[0] == "ELIGIBLE":
            eligible = int(parts[1])
        elif parts[0] == "DONE":
            done = True
            break

    if error or not done or area is None or eligible is None or not votes:
        print("[Receiver] Error detected in transmission.")
        conn.sendall("NACK: Data corrupted\n".encode('utf-8'))
    else:
        conn.sendall("ACK: Data received successfully\n".encode('utf-8'))
        total = sum(votes.values())
        ranked = sorted(votes.items(), key=get_votes, reverse=True)
        for rank, (name, count) in enumerate(ranked, start=1):
            print(f"Rank {rank}: {name} with {count} votes ({count / total * 100:.2f}%)")
        print(f"Total votes: {total}")
        print(f"Total eligible voters: {eligible}")
        print(f"Voters who voted: {total / eligible * 100:.2f}%")

    conn.close()
    server_socket.close()


if __name__ == "__main__":
    run_receiver()