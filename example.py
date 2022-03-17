import os

client = "python3 udp_rtt.py -c -f {frequency} -n {packetsize} -t {time} --ip {ip} --port {port} --save {save} --verbose False"

server = "python3 udp_rtt.py -s -b 1024 -n {packetsize} --ip {ip} --port {port} --verbose False"

FREQUENCY = 1000

for packet_size in range(50, 1500, 10):
    os.system(
        server.format(packetsize=packet_size, ip="localhost", port=4399) +
        '|' + client.format(frequency=FREQUENCY,
                            packetsize=packet_size,
                            time=10,
                            ip="localhost",
                            port=4399,
                            save="test_%04d.csv" % packet_size))
