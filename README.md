# udp-latency
A tiny end-to-end latency testing tool implemented by UDP protocol in Python 📈. 



## Features

Compare with other existing latency testing tools.

|                              | [udp-latency](https://github.com/ChuanyuXue/udp-latency) | [tcp-latency](https://github.com/dgzlopes/tcp-latency) | Ping command | [IPerf](https://iperf.fr) |
| ---------------------------- | -------------------------------------------------------- | ------------------------------------------------------ | ------------ | ------------------------- |
| Support UDP                  | ✅                                                        | ❌                                                      | ❌            | ✅                         |
| Flexible packet size         | ✅                                                        | ❌                                                      | ❌            | ❌                         |
| Specific sending frequency   | ✅                                                        | ✅                                                      | ✅            | ❌                         |
| Simple as single Python file | ✅                                                        | ❌                                                      | ❌            | ❌                         |



## Server Usage

`python3 udp_latency.py -c -f <frequency> -n <packet size> -t <running time> --ip <remote ip> --port <to port> --verbose <bool>`



## Client Usage

`python3 udp_latency.py -s -b <buffer size> --ip <remote ip> --port <local port> --verbose <bool> --save <records saving path>`



## Arguments

| Argument | Description                                                  | Default value |
| -------- | ------------------------------------------------------------ | ------------- |
| -c       | Client                                                       | N/A           |
| -s       | Server                                                       | N/A           |
| -f       | Frequency of sending packets in clients, unit is Hz (number of packet per second). -f “m” means constantly send UDP packets in maximum bandwidth | 1             |
| -n       | Size of sending packets in clients, unit is bytes. Notes that it is the frame size on wire including IP header and UDP header, the size of payload should be smaller by 32. | 1500          |
| -t       | Client running time, uint is second. The server also stops when client stops running. | 10            |
| -b       | Buffer size in server.                                       | 1500          |
| –ip      | Remote ip.                                                   | 127.0.0.1     |
| –port    | To port and local port for client and server respectively.   | 20001         |
| –verbose | Whether print the testing result each iteration.             | True          |
| –save    | File path to save testing result.                            | ./result.csv  |



## Contact

Feel free to contact me at chuanyu.xue@uconn.edu
