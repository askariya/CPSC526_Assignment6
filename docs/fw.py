import argparse
import sys
import os.path
import funcs

rules = [] # global list to hold a set of rules (dictionaries)

def print_error(message):
    print(message, file=sys.stderr)

def check_file_exists(filename):
    if not os.path.isfile(filename):
        print_error("Error: File " + filename + " not found")
        sys.exit()


# read in the firewall rules from the config file
def read_config(filename):
    global rules
    # exit program if file doesn't exist
    check_file_exists(filename)
    line_num = 0
    with open(filename) as f:
        for line in f:
            line_num += 1
            line = line.strip()
            # replace any tab characters with spaces
            line = line.replace('\\t', ' ')
            # if the line is empty or is a comment, ignore
            if line.startswith("#") or line == "":
                continue
            line = line.split()
            # check if the line contains a valid rule
            rule, correct = funcs.create_rule(line, line_num)
            if correct:
                # create and add the rule to the rules list
                rules.append(rule)
            else:
                print_error("Warning: Invalid Rule on Line: " + str(line_num) \
                + "\nContinuing...")

# reads in the packets from std input
def read_input_packets():
    line_num = 0
    for line in sys.stdin:
        line_num += 1
        line = line.strip() # strip extra whitespace
        packet, correct = funcs.create_packet(line)
        # if the packet is invalid, skip
        if not correct:
            print_error("Warning: Invalid Packet on Line: " + str(line_num) \
                + "\nContinuing...")
            continue
        # print output
        print(funcs.validate_packet(rules, packet))

# argparse function to handle user input
# Reference: https://docs.python.org/3.6/howto/argparse.html
# define a string to hold the usage error msg
def parse_arguments():
    usage_string = ("fw.py filename")
    parser = argparse.ArgumentParser(usage=usage_string)

    parser.add_argument("filename",
                        help="file containing firewall rules",
                        type=str)
    args = parser.parse_args()
    return args


def main():
    args = parse_arguments()
    read_config(args.filename) # read in the firewall rules
    read_input_packets()

if __name__ == '__main__':
    main()
