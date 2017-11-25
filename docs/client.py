from __future__ import print_function
import argparse
import os
import socket
import binascii
import hmac
import hashlib
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

BLOCK_SIZE = 1024


class Client:
    def __init__(self, command, filename, host, port, cipher, key):
        self.command = command
        self.filename = filename
        self.host = host
        self.port = port
        self.cipher = cipher
        self.secret_key = key
        self.challenge = None
        self.session_key = None
        self.nonce = binascii.hexlify(os.urandom(16)).decode()
        self.backend = default_backend()

    # Code adapted from:
    # http://www.bogotobogo.com/python/python_network_programming_server_client.php
    def start_client(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))  # connect to server

        # STEP 1: send the cipher to the server
        self.send_init_msg()

        # # Generate IV and SK
        self.iv = self.generate_hash("IV")
        self.session_key = self.generate_hash("SK")

        # Format IV and session key to fit AES method
        self.iv = self.iv[:16].encode()
        if self.cipher == "aes128":
            self.session_key = self.session_key[:16].encode()
        if self.cipher == "aes256":
            self.session_key = self.session_key[:32].encode()

        # STEP 2: Authentication
        self.receive_challenge()
        self.send_computed_challenge()
        self.receive_authentication_result()

        # STEP 3: Send request
        self.send_file_request()
        self.sock.close()  # close the socket

    # sends the cipher and the nonce to the server
    def send_init_msg(self):
        message = self.cipher + "," + self.nonce
        self.sock.send(message.encode())
        server_response = self.sock.recv(BLOCK_SIZE).decode()

        if server_response != "Successful":
            self.sock.send("NOT OK".encode())
            sys.exit(server_response)
        else:
            self.sock.send("OK".encode())

    def receive_challenge(self):
        self.challenge = self.recv_msg()

    def receive_authentication_result(self):
        status = self.recv_msg()
        if status == "Successful":
            display_stderr("Challenge was verified")
        else:
            sys.exit("Challenge was not verified")

    def send_computed_challenge(self):
        challenge = self.compute_challenge()
        self.send_msg(challenge)

    # Computes HMAC of challenge
    # Code taken from Hash Functions lecture slides
    def compute_challenge(self):
        computed_challenge = hmac.new(self.secret_key.encode('utf-8'),
                                      digestmod=hashlib.sha256)
        computed_challenge.update(self.challenge.encode('utf-8'))
        return computed_challenge.hexdigest()

    # Generate sha256 hash of message
    def generate_hash(self, message):
        data = self.secret_key + self.nonce + message
        return hashlib.sha256(data.encode()).hexdigest()

    # sends the command and file name to server
    def send_file_request(self):
        message = self.command + "," + self.filename
        self.send_msg(message)  # sends the command and file name to server
        server_response = self.recv_msg()

        if server_response == "Successful":
            if self.command == "read":
                self.download_file()
            elif self.command == "write":
                self.upload_file()
        else:
            # Exit client program -- display errors
            sys.exit(server_response)

    # read file data from stdin and send to server
    def upload_file(self):
        display_stderr("Uploading...")
        sRead = sys.stdin.buffer.read(BLOCK_SIZE-1)
        while sRead:
            self.send_data(sRead)
            sRead = sys.stdin.buffer.read(BLOCK_SIZE-1)
        display_stderr("File uploaded successfully\n")

    # function to receive a file from the server and pipe to stdout
    def download_file(self):
        display_stderr("Downloading...")
        self.send_msg("Begin")
        rData = self.recv_data()
        while rData:
            sys.stdout.buffer.write(rData)
            rData = self.recv_data()
        display_stderr("File downloaded successfully\n")
        self.sock.close()

    # functions to sendtreceive messages to/from server
    def send_msg(self, message):
        self.sock.send(self.encrypt_data(message.encode()))

    def recv_msg(self):
        data = self.sock.recv(BLOCK_SIZE)
        data = self.decrypt_data(data)
        try:
            msg = data.decode()
        except UnicodeDecodeError:
            return "Unsuccessful"
        return msg

    # functions to send/receive data to/from server
    def send_data(self, data):
        self.sock.send(self.encrypt_data(data))

    def recv_data(self):
        data = self.sock.recv(BLOCK_SIZE)
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

            # catch the case where client doesn't understand
            # server's encryption
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


def display_stderr(message):
    print(message, file=sys.stderr)


# argparse function to handle user input
def parse_arguments():
    # Reference: https://docs.python.org/3.6/howto/argparse.html
    # define a string to hold the usage error msg
    usage_string = ("client.py command filename host:port cipher key")
    parser = argparse.ArgumentParser(usage=usage_string)

    parser.add_argument("command",
                        help="determines if the client will be uploading "
                        "or downloading data to/from the server. "
                        "Valid values are write and read.",
                        type=str)
    parser.add_argument("filename",
                        help="name of the file to be used by "
                        "the server application.",
                        type=str)
    parser.add_argument("host_port",
                        help="specifies the address of the server, "
                        "and the port on which the server is listening the "
                        "server is listening. Port in integer range 0-65535",
                        type=str)
    parser.add_argument("cipher",
                        help="cipher to be used for encrypting the "
                        "communication with the server. "
                        "Valid values are aes256, aes128 and null.",
                        type=str)
    parser.add_argument("key",
                        help="a secret key that must match "
                        "the server’s secret key.",
                        type=str)

    args = parser.parse_args()

    # parse the host and port
    if ":" not in args.host_port:
        parser.exit("usage: " + usage_string)  # print usage
    else:
        host, port = args.host_port.split(":")
        if host == "" or port == "" or not port.isdigit():
            parser.exit("usage: " + usage_string)
        else:
            if int(port) < 0 or int(port) > 65535:
                parser.exit("usage: " + usage_string)

    if args.cipher not in ("null", "aes128", "aes256"):
        parser.exit("usage: " + usage_string)

    return args


def main():
    args = parse_arguments()
    host, port = args.host_port.split(":")

    # launch the client
    client = Client(args.command, args.filename, host,
                    int(port), args.cipher, args.key)
    client.start_client()


if __name__ == '__main__':
    main()
