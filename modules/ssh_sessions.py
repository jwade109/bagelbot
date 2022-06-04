#! /usr/bin/env python3

import os

def ssh_sessions():
    return int(os.popen("ss | grep -i ssh | wc -l").read())

def main():
    print(ssh_sessions())

if __name__ == "__main__":
    main()
