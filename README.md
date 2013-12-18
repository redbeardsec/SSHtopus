SSHtopus v0.1
=============

Description
-----------

SSHtopus is a Python tool for deploying and executing scripts on multiple SSH servers simultaneously.  

Dependencies
------------

* Paramiko - SSH library for Python

That's it!

Usage
-----

* Creating an SSHtopus hosts file

SSHtopus is capable of taking server connection details directly from its interactive prompt, or it can read that information from a pre-generated hosts file.  Not to be confused with the system "hosts" file, an SSHtopus hosts file should have specific formatting to allow the tool to properly parse the server connection info.  The proper format is as follows, one record per line:

username@host[:port]

Where username is the SSH user account to use when authenticating, host is the hostname or IPv4 address of the remote server, and port is the server's SSH listening port.  Note that port specification is optional; if no port is specified, SSHtopus will assume port 22 and continue normally.

* Write your script

Write a script, save it locally, and make note of the file path.  SSHtopus' interactive prompt will ask for that file path later, to know what it needs to deploy.

* Ready to run

Once those conditions are met, simply invoke the script from the command-line and follow the interactive prompts to deploy and/or execute your script on as many hosts as needed.
