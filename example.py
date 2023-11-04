import os

client = "python3 udp_rtt.py -c -f {frequency} -n {packetsize} -t {time} --ip {ip} --lp {local_port} --rp {remote_port} --save {save} --verbose False"

server = "python3 udp_rtt.py -s -b 1024 -n {packetsize} --ip {ip} --lp {local_port} --rp {remote_port} --verbose False"

FREQUENCY = 1

for packet_size in range(50, 1500, 10):
    os.system(
        server.format(packetsize=packet_size,
                      ip="localhost",
                      local_port=10003,
                      remote_port=10002) + '|' +
        client.format(frequency=FREQUENCY,
                      packetsize=packet_size,
                      time=10,
                      ip="localhost",
                      local_port=10002,
                      remote_port=10003,
                      save="test_%04d.csv" % packet_size))
    break
