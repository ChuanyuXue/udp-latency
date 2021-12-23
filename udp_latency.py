import socket
import time
import math
import csv
import sys, getopt

HEADER_SIZE = 32 + 4 + 8


class Client:
    def __init__(
            self,
            local_ip="127.0.0.1",
            local_port=20001,
            remote_ip="127.0.0.1",
            to_port=20002
    ) -> None:

        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.to_port = to_port
        self.log = []
        self.packet_index = 1

        self._udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)

    def send(self, frequency, packet_size, running_time, verbose=True):
        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise "Warning: packet size is not allowed larger than 1500 bytes (MTU size)"

        _payload_size = packet_size - HEADER_SIZE

        start_time = time.time_ns()
        running_time = running_time * 1e9
        while True:
            current_time = time.time_ns()
            index_bytes = self.packet_index.to_bytes(4, 'big')
            time_bytes = current_time.to_bytes(8, 'big')
            msg = b''.join([b'\x00'] * (_payload_size))
            msg = index_bytes + time_bytes + msg
            send_nums = self._udp_socket.sendto(
                msg, (self.remote_ip, self.to_port))
            self.log.append([self.packet_index, current_time, send_nums])

            if (current_time - start_time) > running_time:
                break

            if verbose:
                print('|  Client: %d  |  Packet: %d  |  Time: %d  |  Data size: %d  |' %
                      (self.local_port, self.packet_index, current_time, send_nums))
            self.packet_index += 1
            time.sleep(1 / frequency)

        self._udp_socket.sendto(
            (0).to_bytes(4, 'big'), (self.remote_ip, self.to_port))
        self._udp_socket.close()

    def __del__(self):
        self._udp_socket.close()


class Server:
    def __init__(
        self,
        local_ip="127.0.0.1",
        local_port=20002,
        remote_ip="127.0.0.1",
        to_port=20001,
    ) -> None:
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.to_port = to_port
        self.log = []

        self._udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.remote_ip, self.local_port))

    def listen(self, buffer_size, verbose):
        if verbose:
            print('|  ---------- Listen from Client %d ------------  |' %
                  self.to_port)
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            packet_index = int.from_bytes(msg[:4], 'big')
            send_time = int.from_bytes(msg[4:12], 'big')
            recv_time = time.time_ns()
            latency = round((recv_time - send_time) * 1e-9, 6)
            recv_size = len(msg)
            if packet_index == 0:
                break
            self.log.append([packet_index, latency, recv_time, recv_size])

            if verbose:
                print('|  Server: %d  |  Packet: %d  |  Latency: %f  |  Data size: %d  |' %
                      (self.local_port, packet_index, latency, recv_size))

    def evaluate(self):
        latency_list = [row[1] for row in self.log]
        latency_max = min(latency_list)
        latency_avg = sum(latency_list) / len(latency_list)
        var = sum(pow(x - latency_avg, 2)
                  for x in latency_list) / len(latency_list)
        jitter = math.sqrt(var)
        bandwidth = sum([x[3] for x in self.log]) / \
            ((self.log[-1][2] - self.log[0][2]) * 1e-9)

        print('| -------------  Summary  --------------- |')
        print('Average latency: %f second' % latency_avg)
        print('Maximum latency: %f second' % latency_max)
        print('bandwidth: %f Mbits' % (bandwidth * 0.000008))
        print('Jitter: %f' % jitter)
        return {
            'latency_max': latency_max,
            'latency_avg': latency_avg,
            'jitter': jitter,
            'bandwidth': bandwidth,
        }

    def save(self, path):
        with open(path, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(self.log)

    def __del__(self):
        self._udp_socket.close()

if __name__ == "__main__":
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csf:n:t:b:', ["verbose=", "save=", "ip=", "port="])
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
        print('For Client --> udp_latency.py -c -f <frequency> -n <packet size> -t <running time> --ip <remote ip> --port <to port> --verbose <bool>')
        print('For Server --> udp_latency.py -s -b <buffer size> --ip <remote ip> --port <local port> --verbose <bool> --save <records saving path>')
        sys.exit(2)
    
    if '-c' in opts.keys():
        client = Client(remote_ip=opts['--ip'], to_port=int(opts['--port']))
        client.send(int(opts['-f']), int(opts['-n']), int(opts['-t']), eval(opts['--verbose']))
    if '-s' in opts.keys():
        server = Server(remote_ip=opts['--ip'], local_port=int(opts['--port']))
        server.listen(buffer_size=int(opts['-b']), verbose=eval(opts['--verbose']))
        server.evaluate()
        if '--save' in opts.keys():
            server.save(opts['--save'])




