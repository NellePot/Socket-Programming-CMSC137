# Ong_CH_LE5.1_sender.py
# Name: Christel Hope S. Ong
# CMSC 137 - LE5.1 (Client / Sender)

import socket
import sys
from crc_module import encode_data      # sir's CRC encoder (unchanged)

# ---------- SETTINGS ----------
SHARED_KEY = "1001"                                        # CRC key, same as the receiver's
HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"   # receiver IP (optional argument)
PORT = 65432                                               # must match the receiver's port
TEST_ERROR = False                                         # True = damage the first line to test NACK


def is_valid_text(text):
    #a name or code is valid if it's not empty, is plain ASCII, and has no '|' (separates the fields, 8 bits per character needs ASCII)
    return text != "" and text.isascii() and "|" not in text


def ask_text(prompt):
#Keeps asking until the user types a valid text
    while True:
        text = input(prompt).strip()
        if is_valid_text(text):
            return text
        print("Invalid input. Try again.") #can't be empty or contain '|', must be plain ASCII, and cannot contain '|'


def ask_number(prompt, minimum=0):
    #Keeps asking until the user types a whole number that is at least `minimum`
    while True:
        text = input(prompt).strip()
        if text.isascii() and text.isdigit() and int(text) >= minimum:
            return int(text)
        print(f"Please type a whole number ({minimum} or more).")


def send_line(client, reader, text, corrupt=False):
    #CRC-encodes one line, sends it, and returns True if the receiver replies ACK
    frame = encode_data(text, SHARED_KEY)[0]     # [0] = data bits + CRC bits
    if corrupt:                                  # testing only: flip one bit
        frame = frame[:5] + str(int(frame[5]) ^ 1) + frame[6:]
    print(f"\n[Sender] {text}  ->  {frame}")
    client.sendall((frame + "\n").encode("utf-8"))        # "\n" marks the end of the line
    reply = reader.readline().strip()                     # wait for ACK or NACK
    print(f"[Receiver] {reply or 'no reply (connection closed)'}")
    return reply.startswith("ACK")


def run_sender():
    # 1. Ask for the data first, so a typing mistake never reaches the network
    area = ask_text("Area code: ")
    eligible = ask_number("Total eligible voters: ", minimum=1)

    # 2. Connect, then send line by line; stop as soon as the receiver says NACK
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        reader = client.makefile("r", encoding="utf-8")   # reads the replies line by line

        ok = send_line(client, reader, f"AREA|{area}", corrupt=TEST_ERROR)
        ok = ok and send_line(client, reader, f"ELIGIBLE|{eligible}")

        # 3. Keep asking for nominees until the user presses Enter on an empty name
        nominees_sent = 0
        while ok:
            name = input("\nNominee name (press Enter to finish): ").strip()
            if name == "":
                if nominees_sent == 0:
                    print("Please enter at least one nominee.")
                    continue
                break
            if not is_valid_text(name):
                print("Invalid name: no '|' and plain characters only.")
                continue
            votes = ask_number(f"Total votes for {name}: ")
            ok = send_line(client, reader, f"VOTE|{name}|{votes}")
            nominees_sent += 1

        # 4. Tell the receiver we are done, unless it already rejected the data
        if ok:
            send_line(client, reader, "DONE")
        else:
            print("\n[Sender] Receiver rejected the data. Nothing more will be sent.")


if __name__ == "__main__":
    run_sender()