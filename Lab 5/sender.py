# sender.py
# CMSC 137 - LE5.1 (Client / Sender)
 
import socket
from crc_module import encode_data      # sir's CRC encoder (unchanged)
 
# ---------- SETTINGS ----------
SHARED_KEY = "1001"                                   # CRC key, same as the receiver's
HOST = "192.168.254.110"   # receiver IP (optional argument)
PORT = 65432                                           # must match the receiver's port
TEST_ERROR = False                                    # True = damage one line to test NACK
 
# ---------- data / made-up sample values ----------
AREA_CODE = "0101"
NOMINEES = {"Ong": 1200, "Tambolero": 950, "Yap": 700}
ELIGIBLE_VOTERS = 5000
 
 #this function is used to build the lines of text to send, in the agreed format w/ receiver. 
 #creates a list of strings that represent the area code, nominees with their votes, eligible voters, & END marker to indicate completion of mssg
def build_lines():
    lines = [f"AREA|{AREA_CODE}"]
    lines += [f"NOMINEE|{name}|{votes}" for name, votes in NOMINEES.items()]
    lines.append(f"ELIGIBLE|{ELIGIBLE_VOTERS}")
    lines.append("DONE")                 # marks that the message is complete
    return lines
 
 #this function is to encode the data w/ crc, by calling the encode_data function from crc_module
 #returns a list of codewords (binary strings) that represent the encoded data to be sent
def run_sender():
    # 1. Build the lines and CRC-encode each one separately.
    #    encode_data returns (codeword, raw_bits); we only need the codeword [0]
    lines = build_lines()
    frames = [encode_data(line, SHARED_KEY)[0] for line in lines]
 
    # 2. Testing only.. flip one bit of the first NOMINEE line (like noise on the line)
    if TEST_ERROR:
        bad = frames[1]
        frames[1] = bad[:5] + str(int(bad[5]) ^ 1) + bad[6:]
 
    # 3. Show what is being sent: the original text and its CRC bits
    for line, frame in zip(lines, frames):
        print(f"[Sender] {line}  ->  {frame}")
 
    # 4. Connect to the receiver, send everything, then wait for its reply
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        client.sendall("\n".join(frames).encode("utf-8"))   # "\n" separates the codewords
        client.shutdown(socket.SHUT_WR)                     # "im done sending"
        reply = client.recv(1024).decode("utf-8")           # ACK or NACK (acknowledgment or negative acknowledgment)
        print(f"[Sender] Feedback from receiver: {reply}")
 
 
if __name__ == "__main__":
    run_sender() #to run the sender function when this script is executed directly