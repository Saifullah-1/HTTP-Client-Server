import pytz
import threading
from sys import argv
from socket import *
from datetime import datetime

# Open the log file in append mode
log_file = open('root/log.txt', 'a')


# Function to write log entries to the log file
def write_to_log_file(client_address, method=None, connection=None):
    # Write log entry based on whether the method is provided or not (i.e., timeout case)
    if method is not None:
        log_file.write(
            f"{datetime.now()} | INFO | Request received | Method: {method} | Client Address: {client_address[0]} | "
            f"Client Port: {client_address[1]} | Connection: {connection}\n"
        )
    else:
        log_file.write(
            f"{datetime.now()} | INFO | Connection Timeout | Client Address: {client_address[0]} | "
            f"Client Port: {client_address[1]}\n"
        )
    log_file.flush()  # Ensure the log is written immediately


# Function to get the appropriate content type based on the file extension
def get_content_type(extension):
    if extension == 'txt':
        extension = 'plain'

    # Define content types for text, image, and application
    text = ['html', 'css', 'plain']
    image = ['png', 'jpg', 'jpeg', 'gif', 'svg+xml', 'webp']

    if extension in text:
        return f"text/{extension}"
    elif extension in image:
        return f"image/{extension}"
    else:
        return f"application/{extension}"


# Function to prepare and send the HTTP response
def prepare_response(status_code, content_type, content, clientSocket, connection, client_address):
    now = datetime.now(pytz.timezone("GMT"))
    # Format the HTTP response headers
    response = f'HTTP/1.1 {status_code}\r\n'
    response += f'Date: {now.strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n'
    response += f'Server: Thunder/1.0.0 (WindowsOS)\r\n'
    response += f'Content-Length: {len(content)}\r\n'
    response += f'Content-Type: {content_type}\r\n'
    response += '\r\n'  # Blank line to separate headers and body

    # If the content is an image, send the headers and content in two steps
    if status_code == '404 Not Found' or 'image' not in content_type:
        response += content  # Add the content to the response body
        clientSocket.send(response.encode())  # Send the response
    else:
        clientSocket.send(response.encode())  # Send headers first
        clientSocket.send(content)  # Send the content

    # If the connection should be closed, close the socket and write to the log file
    if connection == 'close':
        clientSocket.close()
        write_to_log_file(client_address)


# Function to process incoming requests
def process_message(msg: str, clientSocket, client_address):
    print(msg)
    msg = msg.rstrip()  # Remove trailing whitespace characters
    lines = msg.split('\r\n')  # Split the message into lines
    request_line = lines[0].split(' ')  # Extract the request line (first line of the HTTP request)
    method = request_line[0]  # Extract the HTTP method (GET, POST, etc.)
    path = request_line[1]  # Extract the file path requested
    connection = 'close'  # Default connection is close

    # Check if the 'Connection' header exists and update the connection status
    for line in lines[1:]:
        if line.startswith("Connection"):
            connection = line.split(' ')[-1]  # Extract 'keep-alive' or 'close'
            break

    # Start a new thread to log the request
    thread = threading.Thread(target=write_to_log_file, args=(client_address, method, connection))
    thread.start()

    # Handle GET requests
    if method == 'GET':
        file_name = path.split('/')[-1]
        file_extension = file_name.split('.')[-1]

        # Determine the content type based on the file extension
        content_type = get_content_type(file_extension)

        try:
            # Open the file to read (binary mode for images)
            mode = 'r'
            if 'image' in content_type:
                mode = 'rb'  # Open in binary mode for image files

            file = open(f"root/{path}", mode)
            file_content = file.read()  # Read the content of the file
            status_code = '200 OK'
            prepare_response(status_code, content_type, file_content, clientSocket, connection, client_address)
            file.close()  # Close the file after reading

        except FileNotFoundError:
            # If the file is not found, return a 404 page
            file = open(f"root/page_not_found.html")
            file_content = file.read()
            status_code = '404 Not Found'
            prepare_response(status_code, 'text/html', file_content, clientSocket, connection, client_address)
            file.close()

    # Handle POST requests
    else:
        extension = 'html'
        ctype = 'text'
        content_type = 'text/html'

        # Extract content type for POST requests
        for line in lines:
            if line.startswith('Content-Type'):
                content_type = line.split(' ')[-1]
                ctype, extension = content_type.split('/')  # Extract extension (e.g., html, json)
                break

        # Open the file in write mode (binary for images)
        mode = 'w'
        if 'image' in ctype:
            mode = 'wb'

        file = open(f"root/{path}.{extension}", mode)

        # Extract the body of the request (content after the empty line)
        idx = lines.index('')
        request_body = '\n'.join(lines[idx + 1:])

        # Write the request body (data sent with POST) to the file
        file.writelines(request_body)
        file.close()

        # Send the response
        status_code = '200 OK'
        prepare_response(status_code, content_type, request_body, clientSocket, connection, client_address)

    # Wait for the logging thread to finish
    thread.join()


# Main server loop to handle incoming connections
if __name__ == '__main__':
    # Get the server port from command line arguments
    serverPort = int(argv[1])

    # Create a TCP/IP socket
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', serverPort))  # Bind the socket to the server address and port
    serverSocket.listen(5)  # Enable the server to accept connections (5 is the max number of queued connections)

    while True:
        connectionSocket, addr = serverSocket.accept()  # Accept a new connection
        message = connectionSocket.recv(2048).decode()  # Receive the request message
        # Start a new thread to process the message
        threading.Thread(target=process_message, args=(message, connectionSocket, addr,)).start()
