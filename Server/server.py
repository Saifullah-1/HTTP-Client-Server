import pytz
import threading
from sys import argv
from socket import *
from datetime import datetime

# Global variables
count_lock = threading.Lock()  # Lock to manage connection count safely across threads
connection_count = 0  # Tracks the number of active connections
total_time = 20  # Total timeout duration in seconds


def get_content_type(extension):
    """
    Determines the MIME content type for a given file extension.

    Args:
        extension (str): The file extension (e.g., 'html', 'jpg', 'txt').

    Returns:
        str: The MIME content type as a string (e.g., 'text/html', 'image/jpeg').

    Raises:
        None
    """
    if extension == 'txt':
        extension = 'plain'

    # Define categories for text and image content types
    text = ['html', 'css', 'plain']
    image = ['png', 'jpg', 'jpeg', 'gif', 'svg+xml', 'webp']

    if extension in text:
        return f"text/{extension}"
    elif extension in image:
        return f"image/{extension}"
    else:
        return f"application/{extension}"


def generate_headers(status_code, content_type, content_length):
    """
    Generates HTTP response headers based on the provided parameters.

    This function constructs HTTP headers as a string, which can be used
    in an HTTP response to the client. It includes the status code, the
    current date in GMT, server details, content length, and content type.

    Args:
        status_code (str): The HTTP status code (e.g., '200 OK', '404 Not Found').
        content_type (str): The MIME type of the content (e.g., 'text/html', 'image/png').
        content_length (int): The length of the content being sent, in bytes.

    Returns:
        str: A formatted HTTP header string ready to be sent in the response.
    """
    now = datetime.now(pytz.timezone("GMT"))
    headers = f'HTTP/1.1 {status_code}\r\n'
    headers += f'Date: {now.strftime("%a, %d %b %Y %H:%M:%S GMT")}\r\n'
    headers += f'Server: Thunder/1.0.0 (WindowsOS)\r\n'
    headers += f'Content-Length: {content_length}\r\n'
    headers += f'Content-Type: {content_type}\r\n\r\n'
    return headers


def prepare_response(status_code, content_type, content, client_socket):
    """
    Prepares and sends an HTTP response to the client.

    Args:
        status_code (str): The HTTP status code and message (e.g., '200 OK').
        content_type (str): The MIME type of the content (e.g., 'text/html').
        content (str or bytes): The content to be sent in the response body.
        client_socket (socket): The client socket for sending the response.
    """
    global connection_count

    headers = generate_headers(status_code, content_type, len(content))
    response = headers
    response += '\r\n'  # Blank line to separate headers and body

    # Append content for text responses or concatenate in binary for images
    if 'image' not in content_type:
        response += content  # Append content for text
        client_socket.sendall(response.encode())
    else:
        response = response.encode()
        if content:
            response += content  # Append content for binary
        client_socket.sendall(response)


def parse_message(msg):
    """
    Parses an HTTP request message and extracts its components.

    Args:
        msg (bytes): The raw HTTP request message received from the client.

    Returns:
        tuple: A tuple containing:
            - method (str): The HTTP request method (e.g., 'GET', 'POST').
            - path (str): The requested file path.
            - content_type (str): The content type specified in the headers (if any).
            - body (str): The body content of the request (decoded to UTF-8 if possible).

    Raises:
        UnicodeDecodeError: If the request body cannot be decoded as UTF-8.
    """
    # Split message into header and body
    header, body = msg.split(b'\r\n\r\n')
    header = header.decode("UTF-8")
    try:
        body = body.decode("UTF-8")
    except UnicodeDecodeError:
        print("Binary data (possibly an image) received in the body.")

    print("<<<< Request Received\n", header, sep='\r\n')

    # Split header into lines and extract components
    lines = header.split('\r\n')
    request_line = lines[0].split(' ')
    method = request_line[0]
    path = request_line[1]

    # Extract 'Content-Type' header if present
    content_type = ''
    for line in lines[1:]:
        if line.startswith("Content-Type"):
            content_type = line.split(' ')[-1]
            break

    return method, path, content_type, body


def process_message(msg: bytes, client_socket):
    """
    Processes an HTTP request message and sends an appropriate response.

    Args:
        msg (bytes): The raw HTTP request message received from the client.
        client_socket (socket): The client socket for sending responses.

    Returns:
        None

    Raises:
        FileNotFoundError: If the requested file cannot be found on the server.
    """
    method, path, content_type, request_body = parse_message(msg)

    if method == 'GET':
        file_name = path.split('/')[-1]
        file_extension = file_name.split('.')[-1]
        content_type = get_content_type(file_extension)

        try:
            mode = 'r' if 'image' not in content_type else 'rb'
            file = open(f"root/{path}", mode)
            file_content = file.read()
            status_code = '200 OK'
            prepare_response(status_code, content_type, file_content, client_socket)
            file.close()
        except FileNotFoundError:
            # Send 404 response if file is not found
            status_code = '404 Not Found'
            prepare_response(status_code, 'text/html', '', client_socket)
        except IOError as e:
            # Handle other I/O errors
            print(f"Error reading file {path}: {e}")
            status_code = '500 Internal Server Error'
            prepare_response(status_code, 'text/html', '', client_socket)

    else:
        extension = content_type.split('/')[-1]
        ctype = content_type.split('/')[0]

        if extension == 'plain':
            extension = 'txt'

        mode = 'w' if 'image' not in ctype else 'wb'
        file = open(f"root/{path}.{extension}", mode)
        file.write(request_body)
        file.close()

        status_code = '200 OK'
        prepare_response(status_code, content_type, '', client_socket)


def receive_data(client_socket):
    """
    Receives data from the client socket and processes each message.

    Args:
        client_socket (socket): The client socket for receiving data.

    Returns:
        None

    Raises:
        TimeoutError: If the connection times out.
        ConnectionResetError: If the connection is reset by the client.
    """
    global connection_count

    with count_lock:
        connection_count += 1

    while True:
        try:
            # Set receive buffer and timeout based on active connections
            chunk = client_socket.recv(1024 * 100)
            client_socket.settimeout(total_time / connection_count)
            if not chunk:
                with count_lock:
                    connection_count -= 1
                break

            process_message(chunk, client_socket)
        except (TimeoutError, ConnectionResetError):
            with count_lock:
                connection_count -= 1
            return


if __name__ == '__main__':
    """
    Entry point for starting the HTTP server.

    Initializes a TCP server socket, binds it to the specified port, 
    and accepts incoming client connections in separate threads.

    Raises:
        KeyboardInterrupt: If the server is interrupted with Ctrl+C.
    """
    serverPort = int(argv[1])

    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.settimeout(None)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(5)

    try:
        while True:
            connectionSocket, addr = serverSocket.accept()
            thread = threading.Thread(target=receive_data, args=(connectionSocket,))
            thread.start()
    except KeyboardInterrupt:
        serverSocket.close()
