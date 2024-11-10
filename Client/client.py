from sys import argv
import time
from socket import *


def send_request(line):
    method, path, host, port = parse_command(line)
    # Parsing the command and get the method, path, host, and port
    request = form_request(method, path, file_type(path))
    # Forming the request
    print(">>>> Request Sent", request, sep='\n')

    sock.send(request)
    # Send the whole request (may be divided)
    response = sock.recv(2048)

    if method == "POST":
        status = response.decode("UTF-8")
        # Decoding the status line then print it
        print("<<<< Response Received", status.split("\r\n")[0], sep='\n')
        print()
    else:
        print(response)
        status, body = response.split(b'\r\n\r\n')
        status = status.decode("UTF-8")    
        # Splitting the response into status line and body then decode the status line
        if status.split("\r\n")[0].split(" ")[1] == "404":
            print("File not found.")
            return
            # If file isn't found on the server, return and continue serving the next commands in the file
        print("<<<< Response Received", status.split("\r\n")[0], sep='\n')
        # print the status line
        print()
        
        headers = status.split("\r\n")[1:]
        for header in headers:
            if header.startswith("Content-Length"):
                length = int(header.split(": ")[1])
                break
        
        length -= len(body.decode("UTF-8", errors='ignore'))
        if length > 0:
            response = sock.recv(length)
            body += response
        
        mode = "w"    
        if 'image' in file_type(path):
            mode = "wb"
            # if the file is an image, open it in binary mode
        saved_file_path = path.split("/")[-1]
        file = open(saved_file_path, mode)
        # open the file to write the body in it in case of GET request

        try:
            body = body.decode("UTF-8")
            # decode the body if it's a text file, if it's an image (binary file) it will raise an exception, so skip
        except UnicodeDecodeError:
            body = body

        print(body)
        # printing the received data
        file.write(body)
        # write to the file to store the received data
        file.close()


def parse_command(command):
    # Extracting the method, path, host, and port from the command
    command = command.strip().split(" ")
    method = "GET" if command[0] == "client_get" else "POST"
    path = command[1]
    host = command[2]
    port = 80
    if (len(command)>3):
        port = command[3]
        # if there's a port number, assign it to the variable. else, it will be 80 by default
    return method, path, host, port


def file_type(path):
    # Detect the file type to handle it correctly
    extention = path.split(".")[-1]
    type = "text/"
    
    if extention == "html" or extention == "css":
        type += (extention)  
    elif extention == "txt":
        type += "plain"  
    else :
        type = "image/" + (extention)
    return type


def read_posted_file(file_path, type):
    # if the method is POST, then we need to read the file contents to send in the request body
    mode = "r"
    if type.split("/")[0] == "image":
        mode = "rb"
    
    try:
        # open the file and read its contents
        file = open(file_path, mode)
        data = file.read()
        file.close()
    except:
        print("File not found.")
        exit(0)
        # If the file to be posted isn't found, exit the application
    return data


def form_request(method, path, type):
    # Form the request to be sent to the server
    file_name = path.split("/")[-1]
    if method == "POST":
        file_name = file_name.split(".")[0]
        # if the method is POST, the file name should be without the extention
    request = f"{method} /{file_name} HTTP/1.1\r\n"
    if method == "POST":
        # in POST, the request should contain the content-type header and the body should be the content to be uploaded to the server
        request += (f"Content-Type: {type}\r\n\r\n")
        body = read_posted_file(path, type)
        if "image" not in type:
            # if the file is a text file, add the body then encode
            request += body
            request = request.encode()
        else:
            # if the file is an image, encode the header then add body
            request = request.encode()
            request += body
    else:
        # in GET, the request doesn't need additional headers
        request += '\r\n'
        request = request.encode()
    return request


if __name__ == "__main__":
    # Starting the application
    ip = argv[1]
    port = int(argv[2])
    # Getting the IP address and the port of the server from the command line arguments
    sock = socket(AF_INET, SOCK_STREAM)
    # Initiating a TCP socket
    sock.connect((ip, port))
    # Initiating a TCP connection to the server
    command_file = input("Enter the path of the commands file: ")
    # Getting the path of the file that contains the commands to be executed
    try:
        file = open(command_file, 'r')
    except:  
        # If the input file containing commands isn't found, print an error message and exit the application
        print("File not found.")
        exit(0)
    
    for line in file:
        # For each command in the file,
        try:
            # Mark the start time of the request, may be needed to calculate the timeout
            start = time.time()
            # Send the request of the current line to the server
            send_request(line)
        except ConnectionAbortedError:
            # If the connection is aborted due to inactivity, print the inactivity duration limit exceeded and continue to the next command
            end = time.time()
            print(f"Connection aborted due to inactivity. Time taken: {end-start}")
    file.close()
        
# client_get file-path host-name (port-number)
# client_post file-path host-name (port-number)
