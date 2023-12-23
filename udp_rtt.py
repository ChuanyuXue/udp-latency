import socket
import time
import math
import csv
import sys
import getopt
from multiprocessing import Process, Queue
from typing import Any, Optional, List, Union

HEADER_SIZE = 32 + 4 + 8
BUFFER_SIZE = 3_000_000


class Client:
    def __init__(
        self,
        local_ip: str = "0.0.0.0",
        local_port: int = 20002,
        remote_ip: str = "127.0.0.1",
        to_port: int = 20001,
    ) -> None:
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.to_port = to_port
        self.send_log: List[List[Union[int, float]]] = []
        self.receive_log: List[List[Union[int, float]]] = []
        self.packet_index = 1

        self._udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
        self._udp_socket.bind((self.local_ip, self.local_port))

    def send(
        self,
        frequency: float,
        packet_size: int,
        running_time: int,
        dyna: bool,
        q: Queue,
    ) -> None:
        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise Exception(
                "Warning: packet size is not allowed larger than 1500 bytes (MTU size)"
            )

        _payload_size = packet_size - HEADER_SIZE

        start_time = time.time_ns()
        total_packets = frequency * running_time
        running_time = running_time * int(1e9)
        period = 1 / frequency
        _fill = b"".join([b"\x00"] * (_payload_size))

        while True:
            index_bytes = self.packet_index.to_bytes(4, "big")
            current_time = time.time_ns()
            msg = index_bytes + current_time.to_bytes(8, "big") + _fill
            send_nums = self._udp_socket.sendto(msg, (self.remote_ip, self.to_port))
            self.send_log.append([self.packet_index, current_time, send_nums])

            if (
                current_time - start_time
            ) > running_time or self.packet_index >= total_packets:
                break
            self.packet_index += 1

            if dyna:
                prac_period = (
                    (running_time - (current_time - start_time))
                    / (total_packets - len(self.send_log))
                    * (
                        len(self.send_log)
                        / (frequency * (current_time - start_time) * 1e-9)
                    )
                    * 1e-9
                )
                prac_period = period if prac_period > period else prac_period
            else:
                prac_period = period

            time.sleep(prac_period)
            # time.sleep(period)

        while q.empty():
            self._udp_socket.sendto(
                (0).to_bytes(4, "big"), (self.remote_ip, self.to_port)
            )
            time.sleep(0.05)
        self._udp_socket.close()

    def listen(
        self, buffer_size: int, verbose: bool, save: Optional[str], q: Queue
    ) -> None:
        latency = 0.0
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            recv_time = time.time_ns()
            packet_index = int.from_bytes(msg[:4], "big")
            send_time = int.from_bytes(msg[4:12], "big")

            old_latency = latency
            latency = round((recv_time - send_time) * 1e-9, 6)
            jitter = abs(latency - old_latency)
            recv_size = len(msg)
            if packet_index == 0:
                break
            self.receive_log.append(
                [packet_index, latency, jitter, recv_time, recv_size]
            )

            if verbose:
                print(
                    "[  Server: %d  |  Packet: %6d  |  Latency: %f ｜ Jitter: %f |  Data size: %4d  ]"
                    % (self.local_port, packet_index, latency, jitter, recv_size)
                )

        self.evaluate()

        if save:
            self.save(save)
        q.put(0)

    def evaluate(self):
        latency_list = [row[1] for row in self.receive_log]
        latency_max = max(latency_list)
        latency_avg = sum(latency_list) / len(latency_list)
        var = sum(pow(x - latency_avg, 2) for x in latency_list) / len(latency_list)
        latency_std = math.sqrt(var)
        jitter = max(latency_list) - min(latency_list)
        cycle = (self.receive_log[-1][3] - self.receive_log[0][3]) * 1e-9
        bandwidth = sum([x[4] + 32 for x in self.receive_log]) / cycle
        packet_loss = (max([x[0] for x in self.receive_log]) - len(latency_list)) / max(
            [x[0] for x in self.receive_log]
        )

        print("| -------------  Summary  --------------- |")
        print(
            "Total %d packets are received in %f seconds"
            % (len(self.receive_log), cycle)
        )
        print("Average latency: %f second" % latency_avg)
        print("Maximum latency: %f second" % latency_max)
        print("Std latency: %f second" % latency_std)
        print("bandwidth: %f Mbits" % (bandwidth * 8 / 1024 / 1024))
        print("Jitter (Latency Max - Min): %f second" % jitter)
        print("Packet loss: %f" % packet_loss)
        return {
            "latency_max": latency_max,
            "latency_avg": latency_avg,
            "jitter": jitter,
            "bandwidth": bandwidth,
        }

    def save(self, path):
        with open(path, "w") as f:
            writer = csv.writer(f, delimiter=",")
            content = [["index", "latency", "jitter", "recv-time", "recv-size"]]
            writer.writerows(content + self.receive_log)

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

        self._udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
        self._udp_socket.bind((self.local_ip, self.local_port))

    def listen(self, buffer_size, verbose, q):
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            recv_time = time.time_ns()
            packet_index = int.from_bytes(msg[:4], "big")
            send_time = int.from_bytes(msg[4:12], "big")
            q.put((packet_index, send_time - recv_time))

            if packet_index == 0:
                break

            if verbose:
                print("Receive message at time %d" % recv_time)

    def send(self, packet_size, verbose, q):
        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise "Warning: packet size is not allowed larger than 1500 bytes (MTU size)"

        _payload_size = packet_size - HEADER_SIZE
        _fill = b"".join([b"\x00"] * (_payload_size))
        while True:
            packet_index, time_diff = q.get()
            index_bytes = packet_index.to_bytes(4, "big")
            current_time = time.time_ns()
            time_bytes = (current_time + time_diff).to_bytes(8, "big")

            msg = index_bytes + time_bytes + _fill
            self._udp_socket.sendto(msg, (self.remote_ip, self.to_port))

            if packet_index == 0:
                break

            if verbose:
                print("Send message at time %d" % current_time)

    def __del__(self):
        self._udp_socket.close()


if __name__ == "__main__":
    try:
        _opts, _ = getopt.getopt(
            sys.argv[1:],
            "csf:n:t:b:m:",
            ["verbose=", "save=", "ip=", "rp=", "lp=", "sync=", "dyna="],
        )
        opts = dict(_opts)
        opts.setdefault("-f", "1")
        opts.setdefault("-n", "1500")
        opts.setdefault("-t", "10")
        opts.setdefault("-b", "1500")
        opts.setdefault("--ip", "127.0.0.1")
        opts.setdefault("--verbose", "True")
        opts.setdefault("--dyna", "True")
        opts.setdefault("--save", "result.csv")

    except getopt.GetoptError:
        print(
            "For Client --> udp_latency.py -c -f/m <frequency / bandwidth> -m <bandwidth> -n <packet size> -t <running time> -b <buffer size> --ip <remote ip> --lp <local port> --rp <remote port> --verbose <bool> --save <records saving path>"
        )
        print(
            "For Server --> udp_latency.py -s -b <buffer size> --ip <remote ip> --lp <local port> --rp <remote port> --verbose <bool>"
        )
        sys.exit(2)

    if "-c" in opts.keys():
        opts.setdefault("--lp", "20002")
        opts.setdefault("--rp", "20001")

        client = Client(
            remote_ip=opts["--ip"],
            to_port=int(opts["--rp"]),
            local_port=int(opts["--lp"]),
        )
        q: Queue = Queue()

        _f: float
        if "-m" in opts:
            _f = float(opts["-m"]) * 125000 / int(opts["-n"])
        elif opts["-f"] == "m":
            _f = math.inf
        else:
            _f = float(opts["-f"])

        listen_process = Process(
            target=client.listen,
            args=(
                int(opts["-b"]),
                eval(opts["--verbose"]),
                opts["--save"],
                q,
            ),
        )

        listen_process.start()
        client.send(_f, int(opts["-n"]), int(opts["-t"]), eval(opts["--dyna"]), q)

        listen_process.join()
        listen_process.close()

    if "-s" in opts.keys():
        opts.setdefault("--lp", "20001")
        opts.setdefault("--rp", "20002")

        server = Server(
            remote_ip=opts["--ip"],
            local_port=int(opts["--lp"]),
            to_port=int(opts["--rp"]),
        )
        q = Queue()

        listen_process = Process(
            target=server.listen, args=(int(opts["-b"]), eval(opts["--verbose"]), q)
        )
        listen_process.start()
        server.send(int(opts["-n"]), eval(opts["--verbose"]), q)
        listen_process.join()
        listen_process.close()
