from sys import argv
from socket import *


def send_request(line):
    method, path, host, port = parse_command(line)
    request = form_request(method, path, file_type(path))
    print(">>>> Request Sent", request, sep='\n')

    sock.send(request.encode())
    response = sock.recv(1024 * (10**6))

    if method == "POST":
        status = response.decode("UTF-8")
        print("<<<< Response Received", status.split("\r\n")[0], sep='\n')
        print()
    else:
        status, body = response.split(b'\r\n\r\n')
        status = status.decode("UTF-8")    
        mode = "w"    
        if file_type(path).split("/")[0] == "image":
            mode = "wb"
        saved_file_path = path.split("/")[-1]
        file = open(saved_file_path, mode)

        try:
            body = body.decode("UTF-8")
        except UnicodeDecodeError:
            body = body

        file.write(body)
        file.close()


def parse_command(command):
    command = command.strip().split(" ")
    method = "GET" if command[0] == "client_get" else "POST"
    path = command[1]
    host = command[2]
    port = 80
    if (len(command)>3):
        port = command[3]
    return method, path, host, port


def file_type(path):
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
    mode = "r"
    if type.split("/")[0] == "image":
        mode = "rb"
    
    try:
        file = open(file_path, mode)
        data = file.read()
        file.close()
    except:
        print("File not found.")
        exit(0)
    return data


def form_request(method, path, type):
    file_name = path.split("/")[-1]
    if method == "POST":
        file_name = file_name.split(".")[0]
    request = f"{method} /{file_name} HTTP/1.1\r\n"
    if method == "POST":
        request += (f"Content-Type: {type}\r\n")
        request += (f"\r\n{read_posted_file(path, type)}")
    else:
        request += '\r\n'
    return request


if __name__ == "__main__":
    ip = argv[1]
    port = int(argv[2])
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((ip, port))
    command_file = input("Enter the path of the commands file: ")
    
    try:
        file = open(command_file, 'r')
    except:  
        print("File not found.")
        exit(0)
    
    for line in file:
        send_request(line)
    file.close()
        
# client_get file-path host-name (port-number)
# client_post file-path host-name (port-number)
