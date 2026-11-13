# receiver.py
# Name: Marinelle Joan U. Tambolero
# CMSC 141 - LE5.1 (receiver)

import socket
from crc_module import mod2div

SHARED_KEY = "1001"                                                      # the shared key used for CRC error detection
CRC_BITS = len(SHARED_KEY) - 1                                           # number of CRC bits
HOST = "127.0.0.1"
PORT = 65432                                                              # must match the sender's port

# convert string of bits to text (8 bits = 1 character)
def bits_to_text(bits):
    text = ""
    for i in range(0, len(bits), 8):
        text += chr(int(bits[i:i+8], 2))                                # takes 8 bits at a time, converts to decimal, then to ASCII character
    return text


# helper function to sort votes in descending order
def get_votes(item):
    return item[1]


def show_results(area, eligible, votes):
    total = sum(votes.values())
    print(f"\n----- Area {area} | Live results -----")
    ranked = sorted(votes.items(), key=get_votes, reverse=True)

    for rank, (name, count) in enumerate(ranked, start=1):
        print(f"Rank {rank}: {name} with {count} votes ({count / total * 100:.2f}%)")

    print(f"Total votes: {total}")
    if eligible:
        print(f"Total eligible voters: {eligible}")
        print(f"Voters who voted: {total / eligible * 100:.2f}%")


# main function to run the receiver server
def run_receiver():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # create a TCP socket
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow reuse of the address
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print("[Receiver] Server listening for connections...")

    conn, addr = server_socket.accept()
    print(f"[Receiver] Connected to: {addr}")


    # initialize variables to store received data
    area, eligible, votes = None, None, {}
    error, done = False, False


    for line in conn.makefile("r", encoding="utf-8"):                   # read lines from the connection as text
        bits = line.strip()

        # too short to be a real message
        if len(bits) < 8 + CRC_BITS:
            error = True
            break

        # CRC check: a remainder with a 1 means the data was corrupted
        if "1" in mod2div(bits, SHARED_KEY):
            error = True
            break

        text = bits_to_text(bits[:-CRC_BITS])                           # remove CRC bits, decode
        print(f"[Receiver] Received text: {text}")


        # parse the text into its components
        parts = text.split("|")
        if parts[0] == "AREA":
            area = parts[1]
        elif parts[0] == "VOTE":
            votes[parts[1]] = votes.get(parts[1], 0) + int(parts[2])   # ADD to the running total
            if eligible and sum(votes.values()) > eligible:            # more votes than eligible voters
                error = True
                conn.sendall("NACK: Votes exceed eligible voters\n".encode("utf-8"))
                break
        elif parts[0] == "ELIGIBLE":
            eligible = int(parts[1])
        elif parts[0] == "DONE":
            done = True

        conn.sendall("ACK: Line received\n".encode('utf-8'))  # send acknowledgment for each line

        if parts[0] == "VOTE":
            show_results(area, eligible, votes)  # show live results after each vote line
        if done:
            break


    if error or not done:
        # error or the sender disconnected early -> disregard everything
        print("[Receiver] Error detected. All data discarded.")
        votes.clear()
    else:
        print("[Receiver] Transmission complete. Final results above.")
 
    conn.close()
    server_socket.close()

if __name__ == "__main__":
    run_receiver()