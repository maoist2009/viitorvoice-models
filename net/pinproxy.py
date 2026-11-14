#!/usr/bin/env python3
"""pinproxy: 本地 CONNECT 代理，按域名分流。

  huggingface.co / *.huggingface.co  -> 默认路由（tun0 代理，治 SNI RST）
  *.hf.co / *.xethub.hf.co           -> SO_BINDTODEVICE wlan0 + 钉优选边缘 IP（直连）

必须 root 运行（SO_BINDTODEVICE 需要 CAP_NET_RAW）。
"""
import select
import socket
import sys
import threading
import time

LISTEN = ("127.0.0.1", 8912)
BUF = 65536

# 优选结果（CloudFront anycast，同一 SNI 换 IP 即换 POP）
PIN = {
    "transfer.xethub.hf.co":     "18.172.34.154",   # NRT20 东京
    "cdn-lfs-us-east-1.hf.co":   "18.172.34.154",   # NRT20 东京
    "us.aws.cdn.hf.co":         "16.144.186.109",  # 只有 us-west-2 服务这个 SNI
}

DOH = "https://cloudflare-dns.com/dns-query?name={h}&type=A"

lock = threading.Lock()
stats = {}


def log(msg):
    with lock:
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
        sys.stderr.flush()


_dns_cache = {}
_dns_lock = threading.Lock()


def dns_a(host, server="223.5.5.5", timeout=4):
    """裸 UDP DNS 查询（绑 wlan0 直连，不用 DoH、不用系统 fake-ip）。"""
    import random
    tid = random.randint(0, 0xFFFF)
    q = bytearray()
    q += tid.to_bytes(2, "big") + b"\x01\x00" + b"\x00\x01" + b"\x00\x00" * 3
    for label in host.rstrip(".").split("."):
        q += bytes([len(label)]) + label.encode()
    q += b"\x00" + b"\x00\x01" + b"\x00\x01"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, 25, b"wlan0\x00")
        s.settimeout(timeout)
        s.sendto(bytes(q), (server, 53))
        data, _ = s.recvfrom(2048)
    finally:
        s.close()
    # 跳过 header + question
    i = 12
    while data[i] != 0:
        i += data[i] + 1
    i += 5
    ancount = int.from_bytes(data[6:8], "big")
    ips = []
    for _ in range(ancount):
        while True:  # name（可能有压缩指针）
            if data[i] & 0xC0 == 0xC0:
                i += 2
                break
            if data[i] == 0:
                i += 1
                break
            i += data[i] + 1
        rtype = int.from_bytes(data[i:i + 2], "big")
        rdlen = int.from_bytes(data[i + 8:i + 10], "big")
        rdata = data[i + 10:i + 10 + rdlen]
        i += 10 + rdlen
        if rtype == 1 and rdlen == 4:
            ips.append(".".join(str(b) for b in rdata))
    if not ips:
        raise OSError("no A record for %s" % host)
    return ips


def resolve_direct(host):
    """给直连域名找一个真实 IP（不能走系统 DNS：那是 fake-ip）。"""
    h = host.lower()
    if h in PIN:
        return PIN[h]
    with _dns_lock:
        if h in _dns_cache:
            return _dns_cache[h]
    ips = dns_a(h)
    with _dns_lock:
        _dns_cache[h] = ips[0]
    return ips[0]


# 只让 SNI 被墙、流量又极小的 API 主域走梯子；其余一律直连（梯子有流量配额）
TUNNEL_ONLY = ("huggingface.co", "www.huggingface.co", "api.huggingface.co", "hf.co")


def is_direct(host):
    h = host.lower()
    if h in TUNNEL_ONLY:
        return False
    if h.endswith(".huggingface.co"):
        return False
    return True   # 其余（*.hf.co / *.xethub.hf.co / *.amazonaws.com ...）全部直连


def dial(host, port):
    direct = is_direct(host)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(20)
    if direct:
        ip = resolve_direct(host)
        s.setsockopt(socket.SOL_SOCKET, 25, b"wlan0\x00")  # SO_BINDTODEVICE
        s.connect((ip, port))
        return s, "direct-wlan0:%s" % ip
    s.connect((host, port))  # 走默认路由 -> tun0
    return s, "tunnel"


def pipe(a, b):
    """双向搬运，返回 (up, down)。"""
    up = down = 0
    socks = [a, b]
    while socks:
        r, _, _ = select.select(socks, [], [], 30)
        if not r:
            break
        for s in r:
            try:
                data = s.recv(BUF)
            except OSError:
                data = b""
            if not data:
                try:
                    other = b if s is a else a
                    other.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                socks.remove(s)
                continue
            other = b if s is a else a
            try:
                other.sendall(data)
            except OSError:
                return up, down
            if s is a:
                up += len(data)
            else:
                down += len(data)
    return up, down


def handle(conn, addr):
    conn.settimeout(15)
    buf = b""
    try:
        while b"\r\n\r\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk
            if len(buf) > 65536:
                return
        head = buf.split(b"\r\n\r\n")[0].decode("latin-1")
        first = head.split("\r\n")[0]
        method, target, _ = (first.split(" ") + ["", ""])[:3]
        if method.upper() != "CONNECT":
            conn.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            return
        host, _, port = target.rpartition(":")
        port = int(port or 443)
        conn.settimeout(30)
        try:
            upstream, route = dial(host, port)
        except Exception as e:  # noqa
            log("FAIL %-28s %s" % (host, e))
            conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            return
        conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        up, down = pipe(conn, upstream)
        log("OK   %-28s %-22s up=%7d down=%8d" % (host, route, up, down))
        upstream.close()
    except Exception as e:  # noqa
        log("ERR  %s %s" % (addr, e))
    finally:
        conn.close()


class Server:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(LISTEN)
        self.s.listen(64)

    def serve(self):
        log("pinproxy listening on %s:%d" % LISTEN)
        while True:
            conn, addr = self.s.accept()
            threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    import os
    if os.geteuid() != 0:
        log("warning: 非 root，SO_BINDTODEVICE 会失败（直连分支会报 EPERM）")
    Server().serve()
