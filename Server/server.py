import pytz
import threading
from sys import argv
from socket import *
from datetime import datetime

# Open the log file in append mode for storing logs
log_file = open('root/log.txt', 'a')
lock = threading.Lock()  # Initialize a lock for thread-safe logging
connection_count = 0
count_lock = threading.Lock()


# Function to write log entries to the log file
def write_to_log_file(client_address, new_connection=False, close_connection=False):
    # Ensure only one thread writes to the log at a time
    with lock:
        # Log request details if a new connection was established
        if new_connection:
            log_file.write(
                f"{datetime.now()} | New Connection <Active Connections: {connection_count}> | Client IP Address: {client_address[0]} |"
                f"Client Port: {client_address[1]}\n"
            )
        else:
            if not close_connection:
                log_file.write(
                    f"{datetime.now()} | INFO | Request received | Client IP Address: {client_address[0]} |"
                    f"Client Port: {client_address[1]}\n"
                )
            # Log connection timeout if no method is provided
            else:
                log_file.write(
                    f"{datetime.now()} | Connection Timeout <Active Connections: {connection_count}> | Client IP "
                    f"Address: {client_address[0]} | Client Port: {client_address[1]}\n"
                )

        log_file.flush()  # Ensure log entry is written immediately


# Function to determine content type based on file extension
def get_content_type(extension):
    # Adjust for plain text files
    if extension == 'txt':
        extension = 'plain'

    # Define content types for text, image, and application files
    text = ['html', 'css', 'plain']
    image = ['png', 'jpg', 'jpeg', 'gif', 'svg+xml', 'webp']

    if extension in text:
        return f"text/{extension}"
    elif extension in image:
        return f"image/{extension}"
    else:
        return f"application/{extension}"


# Function to prepare and send the HTTP response
def prepare_response(status_code, content_type, content, clientSocket):
    global connection_count

    # Format the current date and time in GMT
    now = datetime.now(pytz.timezone("GMT"))

    # Build the HTTP response headers
    response = f'HTTP/1.1 {status_code}\r\n'
    response += f'Date: {now.strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n'
    response += f'Server: Thunder/1.0.0 (WindowsOS)\r\n'
    response += f'Content-Length: {len(content)}\r\n'
    response += f'Content-Type: {content_type}\r\n'
    response += '\r\n'  # Blank line to separate headers and body

    print(">>>> Response Sent", response, sep='\n')

    # Send response differently based on content type
    if 'image' not in content_type:
        response += content  # Append content directly for text responses
        clientSocket.send(response.encode())  # Send response as a single message
    else:
        response = response.encode()
        response += content
        clientSocket.send(response)

    print(content)


# Function to parse an HTTP request message
def parse_message(msg):
    header, body = msg.split(b'\r\n\r\n')
    header = header.decode()
    try:
        body = body.decode()
    except UnicodeDecodeError:
        print("Image")

    print()
    print("<<<< Request Received")
    print(header, body, sep='\r\n')
    print()

    lines = header.split('\r\n')  # Split message into lines
    request_line = lines[0].split(' ')  # Extract the request line
    method = request_line[0]  # Get HTTP method (e.g., GET, POST)
    path = request_line[1]  # Get requested file path
    # connection = 'close'  # Default to closing connection

    # # Look for 'Connection' header to override default if specified
    # for line in lines[1:]:
    #     if line.startswith("Connection"):
    #         connection = line.split(' ')[-1]  # Extract 'keep-alive' or 'close'
    #         break

    # Check for 'Content-Type' header if present
    content_type = ''
    for line in lines[1:]:
        if line.startswith("Content-Type"):
            content_type = line.split(' ')[-1]  # Extract content type
            break

    # # Extract the request body (if any) after the blank line
    # try:
    #     idx = lines.index('')
    #     request_body = '\n'.join(lines[idx + 1:])
    # except ValueError:
    #     request_body = ''  # Nobody present

    return method, path, content_type, body


# Function to process incoming requests
def process_message(msg: str, clientSocket, client_address):
    global connection_count

    method, path, content_type, request_body = parse_message(msg)  # Parse the request

    # Start a new thread to log the request
    thread = threading.Thread(target=write_to_log_file, args=(client_address, False,))
    thread.start()

    # Process GET requests
    if method == 'GET':
        file_name = path.split('/')[-1]
        file_extension = file_name.split('.')[-1]

        # Determine content type from file extension
        content_type = get_content_type(file_extension)

        try:
            # Open requested file in read mode (binary for images)
            mode = 'r'
            if 'image' in content_type:
                mode = 'rb'  # Binary mode for images
            file = open(f"root/{path}", mode)
            file_content = file.read()  # Read file content
            status_code = '200 OK'
            prepare_response(status_code, content_type, file_content, clientSocket)
            file.close()  # Close the file after reading

        except FileNotFoundError:
            # Serve a custom 404 error page if the file is not found
            # file = open(f"root/page_not_found.html")
            # file_content = file.read()
            status_code = '404 Not Found'
            prepare_response(status_code, 'text/html', '', clientSocket)
            # file.close()

    # Process POST requests (saving data sent by the client)
    else:
        extension = content_type.split('/')[-1]
        ctype = content_type.split('/')[0]

        if extension == 'plain':
            extension = 'txt'

        # Determine mode for writing (binary for images)
        mode = 'w'
        if extension == 'plain':
            extension = 'txt'
        
        if 'image' in ctype:
            mode = 'wb'
        file = open(f"root/{path}.{extension}", mode)

        # Write request body to file
        file.writelines(request_body)
        file.close()

        # Send a successful response
        status_code = '200 OK'
        prepare_response(status_code, content_type, '', clientSocket)

    # Wait for the logging thread to finish before exiting
    thread.join()


def receive_data(client_socket, client_address):
    global connection_count

    with count_lock:
        connection_count += 1

    thread = threading.Thread(target=write_to_log_file, args=(client_address, True,))
    thread.start()

    try:
        while True:
            chunk = client_socket.recv(2048)
            if not chunk:
                break  # No more data, exit the loop
            thread = threading.Thread(target=process_message, args=(chunk, connectionSocket, addr))
            thread.start()
        with count_lock:
            connection_count -= 1
            write_to_log_file(client_address, False, True)
    except ConnectionResetError:
        with count_lock:
            connection_count -= 1
            write_to_log_file(client_address, False, True)
    thread.join()


# Main server loop to handle incoming connections
if __name__ == '__main__':
    # Get the server port from command-line arguments
    serverPort = int(argv[1])

    # Create a TCP/IP socket and set up the server
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', serverPort))  # Bind to all network interfaces on the specified port
    serverSocket.listen(5)  # Listen for incoming connections (max queue of 5)

    # Accept connections and process each in a new thread
    while True:
        connectionSocket, addr = serverSocket.accept()  # Accept a new client connection
        # message = connectionSocket.recv(2048).decode()  # Receive the request message
        receive_data(connectionSocket, addr)
        # Start a new thread to process the request
