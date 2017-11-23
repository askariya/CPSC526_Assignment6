import string
import sys

def check_ip(ip):
    ip = ip.split(".")
    if len(ip) != 4:
        return False
    try:
        for num in ip:
            if int(num) not in range (0, 256):
                return False
    except:
        return False
    return True

# returns True if line is valid rule, False otherwise
def check_rule(rule):
    # check direction
    if rule["direction"] not in ("in", "out"):
        return False
    # check action
    if rule["action"] not in ("accept", "reject"):
        return False
    # check IP
    if rule["ip"] != "*": # if the ip is not an ALL classifier
        if not check_ip(rule["ip"]):
            return False
    # check subnet
    if rule["subnet"] is not None: # if the subnet exists
        try:
            if int(rule["subnet"]) not in range(0, 33):
                return False
        except:
            return False
    # check ports
    if rule["ports"][0] != "*": # if the port is not an ALL classifier
        for port in rule["ports"]:
            try:
                if int(port) not in range(0, 65536):
                    return False
            except:
                return False
    # check flag
    if rule["flag"] != '0' and rule["flag"] != '1':
        return False

    return True

# returns a ditionary containing the rule from the argument
def create_rule(line, line_num):
    rule = {}
    rule["line_num"] = line_num
    if (len(line) == 4):
        rule["direction"] = line[0]
        rule["action"] = line[1]
        rule["ip"] = line[2]
        rule["ports"] = line[3].split(",")
        rule["flag"] = None
    elif (len(line) == 5):
        rule["direction"] = line[0]
        rule["action"] = line[1]
        rule["ip"] = line[2]
        rule["ports"] = line[3].split(",")
        rule["flag"] = line[4]
    else:
        return None, False

    # format full ip into an ip and a subnet
    full_ip = rule["ip"].split("/")
    if len(full_ip) == 1:
        rule["ip"] = full_ip[0]
        rule["subnet"] = None
    elif len(full_ip) == 2:
        rule["ip"] = full_ip[0]
        rule["subnet"] = full_ip[1]
    else:
        return None, False

    # format flag
    if rule["flag"] == "established":
        rule["flag"] = '1'
    elif rule["flag"] is None:
        rule["flag"] = '0'

    return rule, check_rule(rule)

# creates and returns a dictionary containing a packet
def create_packet(line):
    packet = {}
    line = line.split()
    if len(line) != 4:
        return None, False
    packet["direction"] = line[0]
    packet["ip"] = line[1]
    packet["port"] = line[2]
    packet["flag"] = line[3]

    # ERROR CHECKING
    # direction
    if packet["direction"] not in ("in", "out"):
        return None, False
    # IP
    if not check_ip(packet["ip"]):
        return None, False
    # port
    try:
        if int(packet["port"]) not in range(0, 65536):
            return None, False
    except:
        return None, False
    # flag
    if packet["flag"] not in ("0", "1"):
        return None, False

    # successful packet -- no errors
    return packet, True

# checks the packet against the rules
# "continue" means no match with a rule
def validate_packet(rules, packet):
    # rule_num = 0 # rule number counter
    for rule in rules:
        # check flag
        # if rule only applies to established packets
        if packet["flag"] == '0' and rule["flag"] == '1':
            continue
        # check direction
        if packet["direction"] != rule["direction"]:
            continue
        # check IP
        if not compare_ips(packet["ip"], rule["ip"], rule["subnet"]):
            continue
        # check port
        if rule["ports"][0] != "*":
            if packet["port"] not in rule["ports"]:
                continue
        # return the output if a match is found
        result = rule["action"] + "(" + str(rule["line_num"]) + ") " + packet["direction"] \
        + " " + packet["ip"] + " " + packet["port"] + " " + packet["flag"]
        return result

    # drop if no match found
    result = "drop() " + packet["direction"] + \
    " " + packet["ip"] + " " + packet["port"] + " " + packet["flag"]
    return result

# adapted from:
# https://codereview.stackexchange.com/questions/19388/\decimal-to-binary-converter-for-ip-addresses
def ip_to_binary(ip):
    return ''.join(['{0:08b}'.format(int(num)) for num in ip.split(".")])

# function to check whether packet_ip fits in rule_ip's subnet
def compare_ips(packet_ip, rule_ip, subnet):
    # if there is no subnet
    if subnet is None:
        if packet_ip == rule_ip or rule_ip == "*":
            return True
        else:
            return False
    packet_ip = ip_to_binary(packet_ip)
    rule_ip = ip_to_binary(rule_ip)
    # get first subnet # of bits
    matching_bits = rule_ip[0:int(subnet)]
    # check if the subnet bits are in the packet IP
    if packet_ip.startswith(matching_bits):
        return True
    else:
        return False
