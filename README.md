# udp-latency
A tiny end-to-end latency testing tool implemented by UDP protocol in Python 📈. 

- **udp_latency.py** records one way latency.
- **udp_rrt.py** records two way average of latency, which has same arguments as udp_latency.

![example](example.png)

## Features

Compare with other existing latency testing tools.

|                              | [udp-latency](https://github.com/ChuanyuXue/udp-latency) | [tcp-latency](https://github.com/dgzlopes/tcp-latency) | Ping command | [IPerf](https://iperf.fr) |
| ---------------------------- | -------------------------------------------------------- | ------------------------------------------------------ | ------------ | ------------------------- |
| Support UDP                  | ✅                                                        | ❌                                                      | ❌            | ✅                         |
| Flexible packet size         | ✅                                                        | ❌                                                      | ❌            | ❌                         |
| Flexible bandwidth           | ✅                                                        | ❌                                                      | ❌            | ✅                         |
| Specific sending period   | ✅                                                        | ✅                                                      | ✅            | ❌                         |
| Simple as single Python file | ✅                                                        | ❌                                                      | ❌            | ❌                         |


## Server Usage

`python3 udp_latency.py -c -f/m <frequency / bandwidth> -n <packet size> -t <running time> --ip <remote ip> --port <to port> --verbose <bool> --sync <bool>`



## Client Usage

`python3 udp_latency.py -s -b <buffer size> --ip <remote ip> --port <local port> --verbose <bool> --sync <bool> --save <records saving path>`



## Arguments

| Argument  | Description                                                                                                                                                                   | Default value |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| -c        | Client                                                                                                                                                                        | N/A           |
| -s        | Server                                                                                                                                                                        | N/A           |
| -f        | Frequency of sending packets from clients, unit is Hz (number of packet per second). -f “m” means constantly send UDP packets in maximum bandwidth                            | 1             |
| -m        | Bandwidth of sending packets from clients, unit is Mbits. This argument will overwritten -f argument.                                                                         | N/A           |
| -n        | Size of sending packets in clients, unit is bytes. Notes that it is the frame size on wire including IP header and UDP header, the packet size should be within \(44, 1500\]. | 1500          |
| -t        | Client running time, uint is second. The server also stops when client stops running.                                                                                         | 10            |
| -b        | Buffer size in server.                                                                                                                                                        | 1500          |
| --ip      | Remote ip.                                                                                                                                                                    | 127.0.0.1     |
| --port    | To port and local port for client and server respectively.                                                                                                                    | 20001         |
| --verbose | Whether to print the testing result each iteration.                                                                                                                              | True          |
| --sync    | Whether to do the time synchronization in advance.  (only for udp_latency.py)                                                                                                                                       | True          |
| --save    | File path to save testing result.                                                                                                                                             | ./result.csv  |



## Time synchronization

⚠️ Udp-latency requires the precise synchronization (same clock time) between server and clients. The basic idea for built-in function is from [IEEE PTP](https://en.wikipedia.org/wiki/Precision_Time_Protocol) protocol.

![ptp](https://upload.wikimedia.org/wikipedia/commons/d/db/IEEE1588_1.jpg)

In the first 10 seconds before latency test, PTP events are exchanged per second for calculating **time offset** between server and clients. To aviod the impact of exchanging PTP packet on experimental traffic, udp-latency assumes that time offset keeps constant during the test.

Udp-rrt requirest no synchronization.



## Contact

Feel free to contact me at chuanyu.xue@uconn.edu
