import time
import threading
from socket import *
import matplotlib.pyplot as plt


lock = threading.Lock()  # Create a lock to ensure thread-safe access to rtts list
request = 'GET /index.html HTTP/1.1\r\n'
request += '\r\n'


def send_request(request, rtts):
    start_time = time.time()
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.connect(('localhost', 12000))
        sock.sendall(request.encode())
        response = sock.recv(2048)

    end_time = time.time()
    rtt = end_time - start_time
    with lock:
        rtts.append(rtt)


def test(request, requests_count):
    rtts = []
    threads = []

    # Start threads
    for i in range(requests_count):
        thread = threading.Thread(target=send_request, args=(request, rtts,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    print(rtts)
    return rtts


if __name__ == '__main__':
    request_counts = [5, 10, 20, 50, 70]
    average_rrts = []

    for count in request_counts:
        rtts = test(request, count)
        average_rrt = sum(rtts) / len(rtts)
        average_rrts.append(average_rrt)

    plt.plot(request_counts, average_rrts)
    plt.xlim(5, 70)
    plt.xlabel('Number of Requests')
    plt.ylabel('Average RTT')
    plt.title('Server Performance')

    plt.show()


