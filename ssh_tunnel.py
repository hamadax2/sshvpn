# -*- coding: utf-8 -*-
"""
SSH tunnel manager.

Establishes an SSH connection with paramiko and runs a local SOCKS5 proxy
server. Any TCP traffic sent to the local proxy is forwarded through the
SSH transport using dynamic port forwarding ("direct-tcpip" channels),
which is exactly how SSH-based VPN/proxy tunnels work.

Point your apps (or the system proxy) at:  socks5h://127.0.0.1:<local_port>
"""

import select
import socket
import struct
import threading

try:
    import paramiko
except ImportError:  # pragma: no cover - paramiko is required at runtime
    paramiko = None

# SOCKS5 protocol constants
SOCKS_VERSION = 0x05
CMD_CONNECT = 0x01
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04


class SSHTunnel:
    """Manages an SSH connection and a local SOCKS5 proxy over it."""

    def __init__(self):
        self._client = None
        self._transport = None
        self._server_socket = None
        self._accept_thread = None
        self._running = False
        self._lock = threading.Lock()
        self.bytes_up = 0
        self.bytes_down = 0

    @property
    def is_connected(self):
        return self._running

    def connect(self, host, port, username, password, local_port):
        """Open the SSH connection and start the local SOCKS5 listener.

        Raises an exception on failure (caught by the caller).
        """
        if paramiko is None:
            raise RuntimeError("paramiko is not installed")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            port=int(port),
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=20,
        )

        transport = client.get_transport()
        transport.set_keepalive(30)

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", int(local_port)))
        server.listen(100)
        server.settimeout(1.0)

        with self._lock:
            self._client = client
            self._transport = transport
            self._server_socket = server
            self._running = True
            self.bytes_up = 0
            self.bytes_down = 0

        self._accept_thread = threading.Thread(
            target=self._accept_loop, daemon=True
        )
        self._accept_thread.start()

    def disconnect(self):
        """Tear down the proxy and SSH connection."""
        with self._lock:
            self._running = False
            server = self._server_socket
            client = self._client
            self._server_socket = None
            self._client = None
            self._transport = None

        if server is not None:
            try:
                server.close()
            except OSError:
                pass
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    # ----- internal -----

    def _accept_loop(self):
        while True:
            with self._lock:
                if not self._running:
                    break
                server = self._server_socket
            if server is None:
                break
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(
                target=self._handle_client, args=(conn,), daemon=True
            ).start()

    def _handle_client(self, conn):
        try:
            if not self._socks_handshake(conn):
                conn.close()
                return
            target = self._socks_request(conn)
            if target is None:
                conn.close()
                return
            dst_addr, dst_port = target
            self._open_tunnel(conn, dst_addr, dst_port)
        except Exception:
            try:
                conn.close()
            except OSError:
                pass

    def _socks_handshake(self, conn):
        # Greeting: VER, NMETHODS, METHODS...
        header = self._recv_exact(conn, 2)
        if not header or header[0] != SOCKS_VERSION:
            return False
        nmethods = header[1]
        self._recv_exact(conn, nmethods)
        # Reply: VER, METHOD (0x00 = no authentication)
        conn.sendall(struct.pack("!BB", SOCKS_VERSION, 0x00))
        return True

    def _socks_request(self, conn):
        # Request: VER, CMD, RSV, ATYP, DST.ADDR, DST.PORT
        data = self._recv_exact(conn, 4)
        if not data or data[0] != SOCKS_VERSION:
            return None
        cmd, _rsv, atyp = data[1], data[2], data[3]
        if cmd != CMD_CONNECT:
            self._send_socks_reply(conn, 0x07)  # command not supported
            return None

        if atyp == ATYP_IPV4:
            raw = self._recv_exact(conn, 4)
            dst_addr = socket.inet_ntoa(raw)
        elif atyp == ATYP_DOMAIN:
            length = self._recv_exact(conn, 1)[0]
            dst_addr = self._recv_exact(conn, length).decode("utf-8", "ignore")
        elif atyp == ATYP_IPV6:
            raw = self._recv_exact(conn, 16)
            dst_addr = socket.inet_ntop(socket.AF_INET6, raw)
        else:
            self._send_socks_reply(conn, 0x08)  # address type not supported
            return None

        dst_port = struct.unpack("!H", self._recv_exact(conn, 2))[0]
        return dst_addr, dst_port

    def _open_tunnel(self, conn, dst_addr, dst_port):
        with self._lock:
            transport = self._transport
        if transport is None:
            self._send_socks_reply(conn, 0x01)
            conn.close()
            return
        try:
            chan = transport.open_channel(
                "direct-tcpip",
                (dst_addr, dst_port),
                conn.getpeername(),
            )
        except Exception:
            self._send_socks_reply(conn, 0x05)  # connection refused
            conn.close()
            return

        # Success reply with bound address 0.0.0.0:0
        self._send_socks_reply(conn, 0x00)
        self._pipe(conn, chan)

    def _pipe(self, sock, chan):
        sock.setblocking(False)
        chan.setblocking(False)
        try:
            while True:
                with self._lock:
                    if not self._running:
                        break
                r, _w, _e = select.select([sock, chan], [], [], 1.0)
                if sock in r:
                    try:
                        data = sock.recv(4096)
                    except (BlockingIOError, InterruptedError):
                        data = b""
                    if data == b"":
                        if not r:
                            continue
                        break
                    if data:
                        chan.sendall(data)
                        self.bytes_up += len(data)
                if chan in r:
                    if chan.recv_ready():
                        data = chan.recv(4096)
                        if not data:
                            break
                        sock.sendall(data)
                        self.bytes_down += len(data)
                    elif chan.closed or chan.eof_received:
                        break
        except (OSError, EOFError):
            pass
        finally:
            try:
                chan.close()
            except Exception:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def _send_socks_reply(self, conn, rep_code):
        # VER, REP, RSV, ATYP(IPv4), BND.ADDR(0.0.0.0), BND.PORT(0)
        reply = struct.pack(
            "!BBBB", SOCKS_VERSION, rep_code, 0x00, ATYP_IPV4
        ) + socket.inet_aton("0.0.0.0") + struct.pack("!H", 0)
        try:
            conn.sendall(reply)
        except OSError:
            pass

    @staticmethod
    def _recv_exact(conn, n):
        buf = b""
        while len(buf) < n:
            try:
                chunk = conn.recv(n - len(buf))
            except (BlockingIOError, InterruptedError):
                continue
            if not chunk:
                return buf if buf else None
            buf += chunk
        return buf
