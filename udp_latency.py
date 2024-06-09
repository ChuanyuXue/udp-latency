import socket
import time
import math
import csv
import sys
import getopt

from typing import List, Tuple, Union

HEADER_SIZE = 32 + 4 + 8


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
        self.log: List[List[Union[int, float]]] = []
        self.packet_index = 1

        self._udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.local_ip, self.local_port))

    def synchronize(self, verbose: bool) -> None:
        if verbose:
            print("|  ---------- Sychonizing Server & Client by PTP ------------  |")
        for _ in range(10):
            t1 = time.time_ns()
            time_bytes = t1.to_bytes(8, "big")
            index_bytes = (0).to_bytes(4, "big")
            msg = b"".join([b"\x00"] * 128)
            msg = index_bytes + time_bytes + msg
            _send_nums = self._udp_socket.sendto(msg, (self.remote_ip, self.to_port))

            msg, _ = self._udp_socket.recvfrom(128 + HEADER_SIZE)
            t2 = int.from_bytes(msg[4:12], "big")
            t2_p = time.time_ns()
            time.sleep(0.05)

            index_bytes = (0).to_bytes(4, "big")
            time_bytes = t2_p.to_bytes(8, "big")
            msg = b""
            msg = index_bytes + time_bytes + msg
            _send_nums = self._udp_socket.sendto(msg, (self.remote_ip, self.to_port))
            time.sleep(1)

    def send(
        self,
        frequency: float,
        packet_size: int,
        running_time: int,
        verbose: bool,
        sync: bool,
        dyna: bool,
    ):
        if sync:
            self.synchronize(verbose)

        if packet_size < HEADER_SIZE or packet_size > 1500:
            raise Exception("warning: packet size should be no larger than 1500 bytes.")

        _payload_size = packet_size - HEADER_SIZE
        _fill = b"".join([b"\x00"] * (_payload_size))

        start_time = time.time_ns()
        total_packets = math.ceil(frequency * running_time)
        running_time = running_time * int(1e9)
        period = 1 / frequency

        while True:
            index_bytes = self.packet_index.to_bytes(4, "big")
            current_time = time.time_ns()
            time_bytes = current_time.to_bytes(8, "big")
            send_nums = self._udp_socket.sendto(
                index_bytes + time_bytes + _fill, (self.remote_ip, self.to_port)
            )
            self.log.append([self.packet_index, current_time, send_nums])

            if (
                current_time - start_time
            ) > running_time or self.packet_index >= total_packets:
                break

            if verbose:
                print(
                    "|  Client: %d  |  Packet: %d  |  Time: %d  |  Data size: %d  |"
                    % (self.local_port, self.packet_index, current_time, send_nums)
                )
            self.packet_index += 1

            if dyna:
                prac_period = (
                    (running_time - (current_time - start_time))
                    / (total_packets - len(self.log))
                    * (len(self.log) / (frequency * (current_time - start_time + 1) * 1e-9))
                    * 1e-9
                )
                prac_period = period if prac_period > period else prac_period
            else:
                prac_period = period

            time.sleep(prac_period)
            # time.sleep(period)

        self._udp_socket.sendto((0).to_bytes(4, "big"), (self.remote_ip, self.to_port))
        self._udp_socket.close()

    def __del__(self):
        self._udp_socket.close()


class Server:
    def __init__(
        self,
        local_ip: str = "0.0.0.0",
        local_port: int = 20001,
        remote_ip: str = "127.0.0.1",
        to_port: int = 20002,
    ) -> None:
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.to_port = to_port
        self.log: List[List[Union[int, float]]] = []

        self.offset: List[float] = []
        self.OFFSET = 0.0

        self._udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_socket.bind((self.local_ip, self.local_port))

    def synchronize(self, verbose: bool):
        if verbose:
            print("|  ---------- Sychonizing Server & Client by PTP ------------  |")

        for i in range(10):
            msg, _ = self._udp_socket.recvfrom(128 + HEADER_SIZE)
            t1 = int.from_bytes(msg[4:12], "big")
            t1_p = time.time_ns()
            time.sleep(0.05)

            t2 = time.time_ns()
            index_bytes = (0).to_bytes(4, "big")
            time_bytes = t2.to_bytes(8, "big")
            msg = b"".join([b"\x00"] * 128)
            msg = index_bytes + time_bytes + msg
            send_nums = self._udp_socket.sendto(msg, (self.remote_ip, self.to_port))

            msg, _ = self._udp_socket.recvfrom(1024)
            t2_p = int.from_bytes(msg[4:12], "big")

            offset = round(((t1_p - t1 + t2 - t2_p) / 2) * 1e-9, 6)
            self.offset.append(offset)
            print("----- Offset at time %d second:  %f -----" % (i, offset))
        abs_min = 1e9
        for v in self.offset:
            if abs(v) < abs_min:
                abs_min = abs(v)
                self.OFFSET = v

    def listen(self, buffer_size: int, verbose: bool, sync: bool):
        if sync:
            self.synchronize(verbose)

        if verbose:
            print("|  ---------- Listen from Client %d ------------  |" % self.to_port)
        latency = 0.0
        while True:
            msg, _ = self._udp_socket.recvfrom(buffer_size)
            recv_time = time.time_ns()
            packet_index = int.from_bytes(msg[:4], "big")
            send_time = int.from_bytes(msg[4:12], "big")
            old_latency = latency
            latency = round(float(recv_time - send_time) * 1e-9 - float(self.OFFSET), 6)
            jitter = abs(latency - old_latency)
            recv_size = len(msg)
            if packet_index == 0:
                break
            self.log.append([packet_index, latency, jitter, recv_time, recv_size])

            if verbose:
                print(
                    "[  Server: %d  |  Packet: %6d  |  Latency: %f ｜ Jitter: %f |  Data size: %4d  ]"
                    % (self.local_port, packet_index, latency, jitter, recv_size)
                )

    def evaluate(self):
        latency_list = [row[1] for row in self.log]
        latency_max = max(latency_list)
        latency_avg = sum(latency_list) / len(latency_list)
        var = sum(pow(x - latency_avg, 2) for x in latency_list) / len(latency_list)
        latency_std = math.sqrt(var)
        jitter = max(latency_list) - min(latency_list)
        cycle = (self.log[-1][3] - self.log[0][3]) * 1e-9
        bandwidth = sum([x[4] + 32 for x in self.log]) / cycle
        packet_loss = (max([x[0] for x in self.log]) - len(latency_list)) / max(
            [x[0] for x in self.log]
        )

        print("| -------------  Summary  --------------- |")
        print("Total %d packets are received in %f seconds" % (len(self.log), cycle))
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
            writer.writerows(content + self.log)

    def __del__(self):
        self._udp_socket.close()


if __name__ == "__main__":
    try:
        _opts, _ = getopt.getopt(
            sys.argv[1:],
            "csf:n:t:b:m:",
            ["verbose=", "save=", "ip=", "port=", "sync=", "dyna="],
        )
        opts = dict(_opts)
        opts.setdefault("-f", "1")
        opts.setdefault("-n", "1500")
        opts.setdefault("-t", "10")
        opts.setdefault("-b", "1500")
        opts.setdefault("--ip", "127.0.0.1")
        opts.setdefault("--port", "20001")
        opts.setdefault("--verbose", "True")
        opts.setdefault("--save", "result.csv")
        opts.setdefault("--dyna", "True")
        opts.setdefault("--sync", "True")

    except getopt.GetoptError:
        print(
            "For Client --> udp_latency.py -c -f/m <frequency / bandwidth> -m <bandwidth> -n <packet size> -t <running time> --ip <remote ip> --port <to port> --verbose <bool> --sync <bool>"
        )
        print(
            "For Server --> udp_latency.py -s -b <buffer size> --ip <remote ip> --port <local port> --verbose <bool> --sync <bool> --save <records saving path>"
        )
        sys.exit(2)

    if "-c" in opts.keys():
        client = Client(remote_ip=opts["--ip"], to_port=int(opts["--port"]))
        _f: float
        if "-m" in opts:
            _f = float(opts["-m"]) * 125000 / int(opts["-n"])
        elif opts["-f"] == "m":
            _f = math.inf
        else:
            _f = float(opts["-f"])
        client.send(
            float(_f),
            int(opts["-n"]),
            int(opts["-t"]),
            eval(opts["--verbose"]),
            sync=eval(opts["--sync"]),
            dyna=eval(opts["--dyna"]),
        )

    if "-s" in opts.keys():
        server = Server(remote_ip=opts["--ip"], local_port=int(opts["--port"]))
        server.listen(
            buffer_size=int(opts["-b"]),
            verbose=eval(opts["--verbose"]),
            sync=eval(opts["--sync"]),
        )
        server.evaluate()
        if "--save" in opts.keys():
            server.save(opts["--save"])
