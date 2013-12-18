#!/usr/bin/env python

import os
import socket
import sys
import threading
import traceback

import paramiko

from getpass import getpass

###########
# Globals #
###########

STORED_PASS = ""
ALLOW_EXECUTION = False

###########
# Classes #
###########

class FileTypeException(Exception):
    pass

#############
# Functions #
#############

def header():
    '''
    Script Banner.  Nothing special.
    '''
    os.system('clear')
    print "*-----------------------------------------------------------------*"
    print "| SSHtopus | Deploy scripts to multiple hosts in parallel via SSH |"
    print "|-----------------------------------------------------------------|"
    print "| Created by @redbeardsec | www.redbeardsec.com |                 |"
    print "*-----------------------------------------------------------------*"
    print "\n"

def client_connect(host, port, username, password):
    '''
    Establishes a connection with a remote SSH server using specified
    host, port, username and password values.

    returns:  a paramiko.SSHClient() object
    '''
    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.connect(host, port, username, password)
        return client
    except Exception, e:
        print "[-] Connection to %s@%s failed: %s: %s" % (str(username), str(host), e.__class__, e)
        print "[+] Moving on..."
        return

def load_script(path):
    '''
    Makes sure the user-supplied path to the script file
    is an absolute path.

    returns:  an absolute path in string form
    '''
    if path[0] == "~":
        path = os.environ['HOME'] + path[1:]
    if not os.path.isabs(path):
        script = open(os.path.realpath(path), "r")
    else:
        script = open(path, "r")
    return script

def parse_hostsfile(path):
    '''
    Parses a pre-defined hosts file and builds a list of connection
    parameters to feed into the main routine.

    returns:  a list object containing [host, port, username, password] objects
    '''
    result = []
    if not os.path.isabs(path):
        hostfile = open(os.path.realpath(path), "r")
    else:
        hostfile = open(path, "r")
    for line in hostfile.readlines():
        port = 22
        sline = line.strip()
        username, host = sline.split("@")
        if host.find(":"):
            host, port = host.split(":")
        result.append([str(host), int(port), str(username)])
    for host in result:
        pw = password(host[0])
        host.append(pw)
    return result

def password(hostname):
    '''
    Password input implementation.  Allows user to enter a password interactively,
    so cleartext credentials do not need to be saved in a hosts file.  Allows a
    password to be specified once and applied to multiple hosts.

    returns:  a password string, either from STORED_PASS global or user input
    '''
    global STORED_PASS
    if len(STORED_PASS) > 0:
        return STORED_PASS
    else:
        password = getpass("Enter password for %s: " % hostname)
        reuse = raw_input("Apply this password to all hosts: [y]es or [n]o? [n] ")
        if reuse == "y":
            STORED_PASS = password
        return password

def single_host():
    '''
    Build a single [host, port, username, password] list object from CLI input.

    returns:  a [host, port, username, password] list object
    '''
    hostname = raw_input("Enter hostname or IP address: ")
    port = raw_input("Enter SSH port: ")
    username = raw_input("Enter username: ")
    pw = password(hostname)
    return [str(hostname), int(port), str(username), str(pw)]

def handler(hostinfo, sema, filename, script_path, print_to_stdout):
    '''
    Target subroutine for thread creation.  Handles uploading and execution of
    scripts on remote SSH servers.

    returns:  no return value
    '''
    #Semaphore acquisition

    sema.acquire()

    # Connection creation section

    print "[+] Establishing SSH connection to %s@%s" % (hostinfo[2], hostinfo[0])
    try:
        client = client_connect(hostinfo[0], hostinfo[1], hostinfo[2], hostinfo[3])
    except Exception, e:
        print "[-] Caught ssh connection exception in handler: %s: %s" % (e.__class__, e)
        traceback.print_exc()
        try:
            client.close()
        except:
            pass
        finally:
            print
            print "[-] Connection to %s@%s failed!" % (hostinfo[2], hostinfo[0])
            sema.release()
    print "[+] Creating SFTP tunnel over SSH to %s@%s" % (hostinfo[2], hostinfo[0])
    sftp = client.open_sftp()
    try:
        print "[+] Creating upload directory on remote host..."
        sftp.mkdir("sshtopus_uploads/")
    except IOError:
        print "[-] Assuming directory already exists, continuing..."
    
    # Script upload section

    print "[+] Uploading %s to sshtopus_uploads directory on %s..." % (filename, hostinfo[0])
    try:
        sftp.put(script_path, "sshtopus_uploads/%s" % filename)
    except Exception, e:
        print "[-] File upload failed: %s: %s" % (e.__class__, e)
    print "[+] File upload succeeded to %s@%s!" % (hostinfo[2], hostinfo[0])
    sftp.close()
    
    # Script execution section

    if ALLOW_EXECUTION == True:
        file_ext = "." + filename.split(".")[1]
        print "[+] File extension detected as " + file_ext
        print "[+] Setting executable permissions on %s" % filename
        try:
            client.exec_command("chmod 744 sshtopus_uploads/%s" % filename)
        except Exception, e:
            print "[-] Caught exception while setting executable flag: %s: %s" % (e.__class__, e)
        try:
            if file_ext == ".sh":
                stdin, stdout, stderr = client.exec_command("/bin/bash -e ./sshtopus_uploads/%s" % filename)
            elif file_ext == ".py":
                print "[+] Executing python file %s on %s" % (filename, hostinfo[0])
                stdin, stdout, stderr = client.exec_command("./sshtopus_uploads/%s" % filename)
            else:
                raise FileTypeException
            stdin.close()
            if print_to_stdout == "y":
                out_data = stdout.read().splitlines()
                err_data = stderr.read().splitlines()
                if len(out_data) > 0:
                    print
                    print "[+] Script execution succeeded on %s!\n" % hostinfo[0]
                    for line in out_data:
                        print line
                if len(err_data) > 0:
                    print
                    print "[+] Script execution failed on %s!\n" % hostinfo[0]
                    for line in err_data:
                        print line
        except FileTypeException:
            print
            print "[-] File extension missing. Scripts must end in '.sh' or '.py' to execute."
        except paramiko.SSHException:
            print
            print "[-] File permissions could not be set, execution aborted on %s" % hostinfo[0]

    # Housecleaning operations
    print "[+] Closing connection to %s@%s" % (hostinfo[2], hostinfo[0])
    client.close()
    print "[+] Releasing semaphore lock belonging to %s@%s" % (hostinfo[2], hostinfo[0])
    sema.release()

################
# Main Routine #
################

def main():
    try:
        global ALLOW_EXECUTION
        header()
        hosts = []
        threads = []
        use_hostfile = raw_input("Load hosts from file: [y]es or [n]o? [y] ")
        if use_hostfile == "y" or len(use_hostfile) == 0:
            path_input = raw_input("Enter path to hosts file: ")
            hosts = parse_hostsfile(path_input)
        else:
            loop = "y"
            while loop == "y":
                host = single_host()
                hosts.append(host)
                loop = raw_input("Add additional hosts: [y]es or [n]o? ")
        script_path = raw_input("Enter path to script file: ")
        data = load_script(script_path).read()
        filename = script_path.split("/")[-1]
        print "Filename set to " + filename
        print_to_stdout = raw_input("Would you like to have script output printed to the screen: [y]es or [n]o? ")
        if print_to_stdout == "y":
            print"\n *********** NOTICE ***********\n\nThe next option deals with threading.  If you have elected to have script stdout\nprinted to the terminal window, you need to set the maximum connection threads\noption to 1.  Otherwise, your output can get comingled and become unreadable.\n\nIgnore this warning at your peril.\n\n*********** NOTICE ***********\n\n"
        max_threads = raw_input("Specify a value for maximum connection threads: ")
        sema = threading.Semaphore(int(max_threads))
        do_execute = raw_input("Execute script files on remote hosts after upload: [y]es or [n]o? [n] ")
        if do_execute == "y":
            ALLOW_EXECUTION  = True
        for host in hosts:
            thread = threading.Thread(target=handler, args=(host, sema, filename, script_path, print_to_stdout))
            thread.daemon = True
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print
        print "[-] Caught SIGINT, terminating program..."
        print
        sys.exit(0)
    except Exception, e:
        print
        print "[-] Caught exception in main: %s: %s" %(e.__class__, e)
        traceback.print_exc()

if __name__ == '__main__':
    main()