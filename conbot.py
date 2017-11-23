import argparse
import sys
# argparse function to handle user input
# Reference: https://docs.python.org/3.6/howto/argparse.html
# define a string to hold the usage error msg
def parse_arguments():
    usage_string = ("conbot.py <hostname> <port> <channel> <secret-phrase>")
    parser = argparse.ArgumentParser(usage=usage_string)

    parser.add_argument("hostname",
                        help="Specifies the address of the server",
                        type=str)
    parser.add_argument("port",
                        help="Specifies the port on which the server is listening. "
                        "Port in integer range 0-65535",
                        type=int)
    parser.add_argument("channel",
                        help="IRC channel to join",
                        type=str)
    parser.add_argument("secret phrase",
                        help="A secret text required to connect",
                        type=str)
    args = parser.parse_args()

    # check that port is in a valid range
    if args.port < 0 or args.port > 65535:
        parser.exit("usage: " + usage_string)

    return args


def main():
    args = parse_arguments()

if __name__ == '__main__':
    main()
