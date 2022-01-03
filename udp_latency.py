import socket
import time
import math
import csv
import sys
import getopt

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
        self.log = []
        self.packet_index = 1

        self._udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.local_ip, self.local_port))

    def synchronize(self):
        for i in range(10):
            t1 = time.time_ns()
            time_bytes = t1.to_bytes(8, 'big')
            index_bytes = (0).to_bytes(4, 'big')
            msg = b''
            msg = index_bytes + time_bytes + msg
            send_nums = self._udp_socket.sendto(
                msg, (self.remote_ip, self.to_port))
            
            msg, _ = self._udp_socket.recvfrom(1024)
            t2 = int.from_bytes(msg[4:12], 'big')
            t2_p = time.time_ns()
            time.sleep(0.01)

            index_bytes = (0).to_bytes(4, 'big')
            time_bytes = t2_p.to_bytes(8, 'big')
            msg = b''
            msg = index_bytes + time_bytes + msg
            send_nums = self._udp_socket.sendto(
                msg, (self.remote_ip, self.to_port))
            time.sleep(1)
            



    def send(self, frequency, packet_size, running_time, verbose=True):
        
        self.synchronize()

        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise "Warning: packet size is not allowed larger than 1500 bytes (MTU size)"

        _payload_size = packet_size - HEADER_SIZE

        start_time = time.time_ns()
        running_time = running_time * 1e9
        period = 1 / frequency if frequency else 0
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
            time.sleep(period)

        self._udp_socket.sendto(
            (0).to_bytes(4, 'big'), (self.remote_ip, self.to_port))
        self._udp_socket.close()

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
        self.log = []

        self.offset = []

        self._udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.local_ip, self.local_port))
        
    def synchronize(self, verbose):
        if verbose:
            print('|  ---------- Sychonizing Server & Client ------------  |')
        
        for i in range(10):
            msg, _ = self._udp_socket.recvfrom(1024)
            t1 = int.from_bytes(msg[4:12], 'big')
            t1_p = time.time_ns()
            time.sleep(0.01)

            t2 = time.time_ns()
            index_bytes = (0).to_bytes(4, 'big')
            time_bytes = t2.to_bytes(8, 'big')
            msg = b''
            msg = index_bytes + time_bytes + msg
            send_nums = self._udp_socket.sendto(
                msg, (self.remote_ip, self.to_port))

            msg, _ = self._udp_socket.recvfrom(1024)
            t2_p = int.from_bytes(msg[4:12], 'big')

            offset = round(((t1_p - t1 + t2 - t2_p) / 2 )* 1e-9, 6)
            self.offset.append(offset)
            print('----- Offset at time %d second:  %f -----'%(i, offset))            


    def listen(self, buffer_size, verbose):
        self.synchronize(True)

        if verbose:
            print('|  ---------- Listen from Client %d ------------  |' %
                  self.to_port)
        latency = 0
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            packet_index = int.from_bytes(msg[:4], 'big')
            send_time = int.from_bytes(msg[4:12], 'big')
            recv_time = time.time_ns()
            old_latency = latency
            latency = round((recv_time - send_time) * 1e-9, 6)
            jitter = abs(latency - old_latency)
            recv_size = len(msg)
            if packet_index == 0:
                break
            self.log.append([packet_index, latency, jitter, recv_time, recv_size])

            if verbose:
                print('|  Server: %d  |  Packet: %d  |  Latency: %f ｜ Jitter: %f |  Data size: %d  |' %
                      (self.local_port, packet_index, latency, jitter, recv_size))

    def evaluate(self):
        latency_list = [row[1] for row in self.log]
        latency_max = max(latency_list)
        latency_avg = sum(latency_list) / len(latency_list)
        var = sum(pow(x - latency_avg, 2)
                  for x in latency_list) / len(latency_list)
        latency_std = math.sqrt(var)
        jitter = sum(
            [abs(v - latency_list[i]) for i, v in enumerate(latency_list[1:])]) / len(latency_list[1:])
        bandwidth = sum([x[4] for x in self.log]) / \
            ((self.log[-1][3] - self.log[0][3]) * 1e-9)
        packet_loss = (
            max([x[0] for x in self.log]) - len(latency_list)) / max([x[0] for x in self.log])

        print('| -------------  Summary  --------------- |')
        print('Average latency: %f second' % latency_avg)
        print('Maximum latency: %f second' % latency_max)
        print('Std latency: %f second' % latency_std)
        print('bandwidth: %f Mbits' % (bandwidth * 0.000008))
        print('Jitter: %f second' % jitter)
        print('Packet loss: %f' % packet_loss)
        return {
            'latency_max': latency_max,
            'latency_avg': latency_avg,
            'jitter': jitter,
            'bandwidth': bandwidth,
        }

    def save(self, path):
        with open(path, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            content = [['index', 'latency', 'recv-time', 'recv-size']]
            writer.writerows(content + self.log)

    def __del__(self):
        self._udp_socket.close()


if __name__ == "__main__":
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csf:n:t:b:m:', [
                                "verbose=", "save=", "ip=", "port="])
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
        print('For Client --> udp_latency.py -c -f/m <frequency / bandwidth> -m <bandwidth> -n <packet size> -t <running time> --ip <remote ip> --port <to port> --verbose <bool>')
        print('For Server --> udp_latency.py -s -b <buffer size> --ip <remote ip> --port <local port> --verbose <bool> --save <records saving path>')
        sys.exit(2)

    if '-c' in opts.keys():
        client = Client(remote_ip=opts['--ip'], to_port=int(opts['--port']))
        if '-m' in opts:
            opts['-f'] = int(opts['-m']) * 125000 / int(opts['-n'])
        if opts['-f'] == 'm':
            opts['-f'] = 0
        client.send(int(opts['-f']), int(opts['-n']),
                    int(opts['-t']), eval(opts['--verbose']))
    if '-s' in opts.keys():
        server = Server(remote_ip=opts['--ip'], local_port=int(opts['--port']))
        server.listen(buffer_size=int(
            opts['-b']), verbose=eval(opts['--verbose']))
        server.evaluate()
        if '--save' in opts.keys():
            server.save(opts['--save'])
