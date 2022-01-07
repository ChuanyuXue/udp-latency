import socket
import time
import math
import csv
import sys
import getopt
from multiprocessing import Process, Queue

HEADER_SIZE = 32 + 4 + 8

class Client:
    def __init__(
            self,
            local_ip="0.0.0.0",
            local_port=20002,
            remote_ip="127.0.0.1",
            to_port=20001
    ) -> None:

        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.to_port = to_port
        self.send_log = []
        self.receive_log = []
        self.packet_index = 1

        self._udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.local_ip, self.local_port))
    
    def send(self, frequency, packet_size, running_time):
        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise "Warning: packet size is not allowed larger than 1500 bytes (MTU size)"

        _payload_size = packet_size - HEADER_SIZE

        start_time = time.time_ns()
        running_time = running_time * 1e9
        period = 1 / frequency if frequency else 0
        _fill = b''.join([b'\x00'] * (_payload_size))

        while True:
            index_bytes = self.packet_index.to_bytes(4, 'big')
            current_time = time.time_ns()
            msg = index_bytes + current_time.to_bytes(8, 'big') + _fill
            send_nums = self._udp_socket.sendto(
                msg, (self.remote_ip, self.to_port))
            self.send_log.append([self.packet_index, current_time, send_nums])

            if (current_time - start_time) > running_time:
                break
            self.packet_index += 1
            time.sleep(period)

        self._udp_socket.sendto(
            (0).to_bytes(4, 'big'), (self.remote_ip, self.to_port))
        self._udp_socket.close()

    def listen(self, buffer_size, verbose):
        latency = 0
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            recv_time = time.time_ns()
            packet_index = int.from_bytes(msg[:4], 'big')
            send_time = int.from_bytes(msg[4:12], 'big')
            
            old_latency = latency
            latency = round(((recv_time - send_time) * 1e-9) / 2, 6)
            jitter = abs(latency - old_latency)
            recv_size = len(msg)
            if packet_index == 0:
                break
            self.receive_log.append(
                [packet_index, latency, jitter, recv_time, recv_size])

            if verbose:
                print('|  Server: %d  |  Packet: %d  |  Latency: %f ｜ Jitter: %f |  Data size: %d  |' %
                      (self.local_port, packet_index, latency, jitter, recv_size))

    def __del__(self):
        self._udp_socket.close()


class Server:
    def __init__(
        self,
        local_ip="0.0.0.0",
        local_port=20001,
        remote_ip="127.0.0.1",
        to_port=20002,
    ) -> None:
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.to_port = to_port

        self._udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.local_ip, self.local_port))

    def listen(self, buffer_size, verbose, q):
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            recv_time = time.time_ns()
            packet_index = int.from_bytes(msg[:4], 'big')
            send_time = int.from_bytes(msg[4:12], 'big')
            q.put((packet_index, send_time - recv_time))

            if packet_index == 0:
                q.put((0, 0))
                break

            if verbose:
                print("Receive message at time %d"%recv_time)

    def send(self, packet_size, verbose, q):
        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise "Warning: packet size is not allowed larger than 1500 bytes (MTU size)"

        _payload_size = packet_size - HEADER_SIZE
        _fill = b''.join([b'\x00'] * (_payload_size))
        while True:
            packet_index, time_diff = q.get()
            index_bytes = packet_index.to_bytes(4, 'big')
            current_time = time.time_ns()
            time_bytes = (current_time + time_diff).to_bytes(8, 'big')
            
            msg = index_bytes + time_bytes + _fill
            self._udp_socket.sendto(
                msg, (self.remote_ip, self.to_port))

            if packet_index == 0:
                break
            
            if verbose:
                print("Send message at time %d"%current_time)

    def __del__(self):
        self._udp_socket.close()



if __name__ == "__main__":
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csf:n:t:b:m:', [
                                "verbose=", "save=", "ip=", "port=", "sync="])
        opts = dict(opts)
        opts.setdefault('-f', "1")
        opts.setdefault('-n', "1500")
        opts.setdefault('-t', "10")
        opts.setdefault('-b', "1500")
        opts.setdefault('--ip', "127.0.0.1")
        opts.setdefault('--port', "20001")
        opts.setdefault('--verbose', "True")
        opts.setdefault('--save, "result.csv"')

    except getopt.GetoptError:
        print('For Client --> udp_latency.py -c -f/m <frequency / bandwidth> -m <bandwidth> -n <packet size> -t <running time> -b <buffer size> --ip <remote ip> --port <to port> --verbose <bool> --save <records saving path>')
        print('For Server --> udp_latency.py -s -b <buffer size> --ip <remote ip> --port <local port> --verbose <bool>')
        sys.exit(2)

    if '-c' in opts.keys():
        client = Client(remote_ip=opts['--ip'], to_port=int(opts['--port']))
        if '-m' in opts:
            opts['-f'] = int(opts['-m']) * 125000 / int(opts['-n'])
        if opts['-f'] == 'm':
            opts['-f'] = 0

        listen_process = Process(target=client.listen, args = (int(opts['-b']), eval(opts['--verbose'])))

        listen_process.start()
        client.send(int(opts['-f']), int(opts['-n']),
                    int(opts['-t']))
        listen_process.join()
        

    if '-s' in opts.keys():
        server = Server(remote_ip=opts['--ip'], local_port=int(opts['--port']))
        q = Queue()

        listen_process = Process(target=server.listen, args=(int(opts['-b']), eval(opts['--verbose']), q))
        listen_process.start()
        server.send(int(opts['-n']), eval(opts['--verbose']), q)
        listen_process.join
