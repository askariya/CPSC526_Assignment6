"""
a bot client for a botnet
"""

import argparse
import sys
import socket


class botClient:
    def __init__(self, host, port, channel, secret_phrase):
        self.host = host
        self.port = port
        self.channel = channel
        self.secret_phrase = secret_phrase
        self.sock = None

    def start_client(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))  # connect to server



# argparse function to handle user input
# Reference: https://docs.python.org/3.6/howto/argparse.html
# define a string to hold the usage error msg
def parse_arguments():
    usage_string = ("bot.py <host> <port> <channel> <secret-phrase>")
    parser = argparse.ArgumentParser(usage=usage_string)

    parser.add_argument("host",
                        help="Specifies the address of the server",
                        type=str)
    parser.add_argument("port",
                        help="Specifies the port on which the server is listening. "
                        "Port in integer range 0-65535",
                        type=int)
    parser.add_argument("channel",
                        help="IRC channel to join",
                        type=str)
    parser.add_argument("secret_phrase",
                        help="A secret text required to connect",
                        type=str)
    args = parser.parse_args()

    # check that port is in a valid range
    if args.port < 0 or args.port > 65535:
        parser.exit("usage: " + usage_string)
        
    return args


def main():
    args = parse_arguments()
    # launch the client
    bot_client = botClient(args.host,
                    int(args.port), args.channel, args.secret_phrase)
    bot_client.start_client()

if __name__ == '__main__':
    main()
