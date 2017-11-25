import argparse
import socket
import time
import hmac
import hashlib
import random
import string
import os.path
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


BLOCK_SIZE = 1024


class Server:
    def __init__(self, port, secret_key):
        self.secret_key = secret_key
        self.port = port
        self.challenge = None
        self.nonce = None
        self.iv = None
        self.session_key = None
        self.cipher = "null"
        self.backend = default_backend()

    # Code adapted from:
    # http://www.bogotobogo.com/python/python_network_programming_server_client.php
    def start_server(self):

        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(('', self.port))
        serversocket.listen(1)

        print("Listening on port: " + str(self.port))
        print("Using secret key: " + self.secret_key)

        while True:
            # accept a client connection
            self.clientsocket, self.addr = serversocket.accept()
            log("New connection from: " + str(self.addr))

            # STEP 1: Receive cipher from client
            self.cipher, self.nonce = self.recv_init_msg()

            # # Generate IV and SK
            self.iv = self.generate_hash("IV")
            self.session_key = self.generate_hash("SK")

            # Format IV and session key to fit AES method
            self.iv = self.iv[:16].encode()
            if self.cipher == "aes128":
                self.session_key = self.session_key[:16].encode()
            if self.cipher == "aes256":
                self.session_key = self.session_key[:32].encode()

            if self.cipher == "aes128" or self.cipher == "aes256":
                log("iv=" + self.iv.decode())
                log("sk=" + self.session_key.decode())

            # STEP 2: Authentication
            self.send_challenge()
            if not self.verify_challenge():
                self.clientsocket.close()
                continue

            # STEP 3: Handle request
            self.recv_file_request()
            self.clientsocket.close()
            sys.exit(0)

    def recv_init_msg(self):
        # receive cipher and nonce from client
        client_msg = self.clientsocket.recv(BLOCK_SIZE).decode()
        cipher, nonce = client_msg.split(",")
        log("nonce=" + nonce)
        log("cipher=" + cipher)
        self.clientsocket.send("Successful".encode())
        client_msg = self.clientsocket.recv(BLOCK_SIZE).decode()
        if client_msg != "OK":
            self.clientsocket.close()
        return cipher, nonce

    # Geenrates random string as challenge
    # https://stackoverflow.com/questions/2257441/
    def send_challenge(self):
        self.challenge = ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits) for _ in range(16))
        self.send_msg(self.challenge)

    # Computes HMAC of challenge
    # Code taken from Hash Functions lecture slides
    def compute_challenge(self):
        computed_challenge = hmac.new(self.secret_key.encode('utf-8'),
                                      digestmod=hashlib.sha256)
        computed_challenge.update(self.challenge.encode('utf-8'))
        return computed_challenge.hexdigest()

    def verify_challenge(self):
        received_challenge = self.recv_msg()
        computed_challenge = self.compute_challenge()
        if received_challenge != computed_challenge:
            self.send_msg("Unsuccessful")
            log("status: error - bad key")
            return False
        else:
            self.send_msg("Successful")
            return True

    # Generate sha256 hash of message
    def generate_hash(self, message):
        if self.nonce is not None:
            data = self.secret_key + self.nonce + message
            return hashlib.sha256(data.encode()).hexdigest()

    # recieves the command and file name from the client
    def recv_file_request(self):
        client_msg = self.recv_msg()
        command, filename = client_msg.split(",")
        log("Command: " + command + ", Filename: " + filename)
        if command == "read":
            self.send_file(filename)

        elif command == "write":
            self.send_msg("Successful")
            self.receive_file(filename)

        else:
            self.send_msg("Error: Unknown Command")

    # function to write the input client data to a file
    def receive_file(self, filename):
        wfile = open(filename, "wb")
        wData = self.recv_data()
        while wData:
            wfile.write(wData)  # write to file
            wData = self.recv_data()
        log("Status: success")

    # function to read a file on the server and send to the client
    def send_file(self, filename):
        if os.path.isfile(filename):
            self.send_msg("Successful")
        else:
            self.send_msg("Error: File " + filename + " does not exist")
            return

        client_msg = self.recv_msg()
        if client_msg == "Begin":
            # open file; read and send to client
            rfile = open(filename, "rb")
            fRead = rfile.read(BLOCK_SIZE-1)
            while fRead:
                self.send_data(fRead)
                fRead = rfile.read(BLOCK_SIZE-1)
            log("Status: success")
        else:
            raise ValueError("No indication from client")

    # functions to send/receive messages to/from client
    def send_msg(self, message):
        self.clientsocket.send(self.encrypt_data(message.encode()))

    def recv_msg(self):
        data = self.clientsocket.recv(BLOCK_SIZE)
        data = self.decrypt_data(data)
        try:
            msg = data.decode()
        except UnicodeDecodeError:
            return "Unsuccessful"

        return msg

    def send_data(self, data):
        self.clientsocket.send(self.encrypt_data(data))

    def recv_data(self):
        data = self.clientsocket.recv(BLOCK_SIZE)
        data = self.decrypt_data(data)
        return data

    # Encryption and Decryption methods
    def encrypt_data(self, data):

        if self.cipher == "null":
            return data
        elif self.cipher == "aes128" or self.cipher == "aes256":

            padded_data = self.pad(data, 128)

            cipher = Cipher(algorithms.AES(self.session_key),
                            modes.CBC(self.iv), backend=self.backend)
            encryptor = cipher.encryptor()
            cipher_data = encryptor.update(padded_data) + encryptor.finalize()

            return cipher_data

    def decrypt_data(self, cipher_data):

        if self.cipher == "null":
            return cipher_data
        elif self.cipher == "aes128" or self.cipher == "aes256":

            cipher = Cipher(algorithms.AES(self.session_key),
                            modes.CBC(self.iv), backend=self.backend)
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(cipher_data) + decryptor.finalize()

            # catch the case where server doesn't understand
            # client's encryption
            try:
                plain_data = self.unpad(padded_data, 128)
            except ValueError:
                return "Unsuccessful".encode()

            return plain_data

    # padding functions
    def pad(self, data, block_size):
        padder = padding.PKCS7(block_size).padder()
        return padder.update(data) + padder.finalize()

    def unpad(self, data, block_size):
        if data != b'':
            unpadder = padding.PKCS7(block_size).unpadder()
            return unpadder.update(data) + unpadder.finalize()


def log(message):
    print(time.strftime("%H:%M:%S " + message))


# argparse function to handle user input
# Reference: https://docs.python.org/3.6/howto/argparse.html
# define a string to hold the usage error msg
def parse_arguments():
    usage_string = ("server.py port key")
    parser = argparse.ArgumentParser(usage=usage_string)

    parser.add_argument("port",
                        help="specifies the address of the server, "
                        "and the port on which the server is listening. "
                        "Port in integer range 0-65535",
                        type=int)
    parser.add_argument("key",
                        help="the secret key.",
                        type=str)
    args = parser.parse_args()

    # check that port is in a valid range
    if args.port < 0 or args.port > 65535:
        parser.exit("usage: " + usage_string)
    return args


def main():
    args = parse_arguments()
    # launch the server
    server = Server(args.port, args.key)
    server.start_server()


if __name__ == '__main__':
    main()
