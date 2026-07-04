import os
import sys
import time
import socket
import struct
import select
import platform
import subprocess
import argparse
import threading
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import random
from flask import Flask, request, jsonify


tunnel_url = None

def start_tunnel_thread(port):
    global tunnel_url
    print("[*] Starting localtunnel via npx...")
    try:
        use_shell = os.name == 'nt'
        cmd = ["npx", "localtunnel", "--port", str(port)]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=use_shell,
            text=True,
            bufsize=1
        )
        
        # Read stdout line by line
        for line in iter(proc.stdout.readline, ''):
            stripped = line.strip()
            if stripped:
                print(f"[Tunnel] {stripped}")
            match = re.search(r'your url is:\s*(https?://[^\s]+)', stripped)
            if match:
                tunnel_url = match.group(1)
                print(f"\n=========================================")
                print(f"🎉 터널 생성 완료: {tunnel_url}")
                print(f"=========================================\n")
                
        proc.stdout.close()
        proc.wait()
    except Exception as e:
        print(f"[!] 터널 기동 중 에러 발생: {e}")
        print("[!] Node.js 및 npm이 설치되어 있는지 확인해 주세요.")

app = Flask(__name__)

# ICMP Echo Request protocol type
ICMP_ECHO_REQUEST = 8

def calculate_checksum(source_string):
    """
    Calculate the standard Internet Checksum (RFC 1071) for the packet data.
    """
    if len(source_string) % 2:
        source_string += b'\x00'
    countTo = (len(source_string) // 2) * 2
    checksum_sum = 0
    count = 0
    while count < countTo:
        thisVal = source_string[count + 1] * 256 + source_string[count]
        checksum_sum = checksum_sum + thisVal
        checksum_sum = checksum_sum & 0xffffffff
        count = count + 2
    
    checksum_sum = (checksum_sum >> 16) + (checksum_sum & 0xffff)
    checksum_sum = checksum_sum + (checksum_sum >> 16)
    answer = ~checksum_sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def ping_one_raw(ip, timeout=2.5):
    """
    Send an ICMP Echo Request using Python raw sockets and wait for Echo Reply.
    Returns: (is_alive: bool, latency_ms: float or None, error_type: str or None)
    """
    try:
        dest_addr = socket.gethostbyname(ip)
    except socket.gaierror:
        return False, None, "unreachable"

    try:
        # Requires root/administrator privileges
        icmp_proto = socket.getprotobyname("icmp")
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
    except PermissionError as e:
        # Propagate permission error to invoke fallback logic
        raise e
    except Exception:
        return False, None, "unreachable"

    try:
        my_socket.settimeout(timeout)
        
        # Generate unique ID using random module to prevent collisions in concurrent execution
        packet_id = random.randint(1, 65535)
        seq_num = 1
        
        # Pack header with checksum=0 first
        # Format: !BBHHH (Type=8, Code=0, Checksum=0, ID, Seq)
        header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, packet_id, seq_num)
        data = struct.pack("d", time.time())
        
        # Calculate checksum and repack header
        my_checksum = calculate_checksum(header + data)
        header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, my_checksum, packet_id, seq_num)
        packet = header + data
        
        my_socket.sendto(packet, (dest_addr, 1))
        
        started_select = time.time()
        while True:
            how_long_in_select = time.time() - started_select
            if how_long_in_select >= timeout:
                return False, None, "timeout"
                
            what_ready = select.select([my_socket], [], [], timeout - how_long_in_select)
            if what_ready[0] == []:
                return False, None, "timeout"
                
            time_received = time.time()
            rec_packet, addr = my_socket.recvfrom(1024)
            
            # Read IP Header Length to find the start of the ICMP Header
            # The first byte contains Version (4 bits) and Internet Header Length (IHL) in 32-bit words
            ip_header_len = (rec_packet[0] & 0x0F) * 4
            icmp_header = rec_packet[ip_header_len : ip_header_len + 8]
            
            type, code, checksum_val, rec_id, rec_seq = struct.unpack("!BBHHH", icmp_header)
            
            # Type 0 = Echo Reply
            if type == 0 and rec_id == packet_id and rec_seq == seq_num:
                if addr[0] == dest_addr:
                    latency = (time_received - started_select) * 1000
                    return True, round(latency, 1), None
            # Type 3 = Destination Unreachable
            elif type == 3:
                try:
                    orig_icmp = rec_packet[ip_header_len + 28 : ip_header_len + 36]
                    orig_type, orig_code, orig_checksum, orig_id, orig_seq = struct.unpack("!BBHHH", orig_icmp)
                    if orig_id == packet_id and orig_seq == seq_num:
                        return False, None, "unreachable"
                except Exception:
                    pass
    except Exception:
        return False, None, "timeout"
    finally:
        try:
            my_socket.close()
        except Exception:
            pass


# Limit concurrent ping executions across threads to protect system FD/process limits
thread_sem = threading.BoundedSemaphore(100)
executor = ThreadPoolExecutor(max_workers=100)

def check_host_sync(ip, use_raw=True):
    with thread_sem:
        """
        Checks if a host is alive using Raw Socket, System Ping, or TCP Connect sequentially.
        Retries twice (total 2 attempts) to stay safe under proxy timeouts.
        Returns: (is_alive, latency, method, error)
        """
        timeout = 1.5
        retries = 1

        # 1. Try Raw Socket ICMP
        if use_raw:
            try:
                last_err = "timeout"
                for attempt in range(retries):
                    alive, latency, err = ping_one_raw(ip, timeout=timeout)
                    if alive:
                        return True, latency, "raw_socket", None
                    if err:
                        last_err = err
                    if attempt < retries - 1:
                        time.sleep(0.1)
                return False, None, "raw_socket", last_err
            except PermissionError:
                # Fall through to permissionless methods
                pass
            except Exception:
                return False, None, "raw_socket", "timeout"

        # 2. First Fallback: System Ping CLI command
        is_alive = False
        latency = None
        method = "system_ping"
        error_type = "timeout"
    
        timeout_ms = str(int(timeout * 1000))
        timeout_sec = str(max(1, int(timeout + 0.5)))
        if platform.system().lower() == 'windows':
            command = ['ping', '-n', '1', '-w', timeout_ms, ip]
        elif platform.system().lower() == 'darwin':
            command = ['ping', '-c', '1', '-n', '-W', timeout_ms, ip]  # macOS uses ms
        else:
            command = ['ping', '-c', '1', '-n', '-W', timeout_sec, ip]  # Linux uses seconds
        
        for attempt in range(retries):
            try:
                start_t = time.time()
                res = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 1)
                end_t = time.time()
                if res.returncode == 0:
                    is_alive = True
                    latency = round((end_t - start_t) * 1000, 1)
                    error_type = None
                    break
                else:
                    output = (res.stdout or "") + (res.stderr or "")
                    if "unreachable" in output.lower() or "host down" in output.lower():
                        error_type = "unreachable"
                    else:
                        error_type = "timeout"
            except subprocess.TimeoutExpired:
                error_type = "timeout"
            except Exception:
                error_type = "timeout"
        
            if attempt < retries - 1:
                time.sleep(0.1)

        # 3. Second Fallback: TCP Port checks (80 / 443)
        if not is_alive:
            method = "tcp_port"
            error_type = "timeout"
            for port in [80, 443]:
                for attempt in range(retries):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1.0)
                            start_t = time.time()
                            s.connect((ip, port))
                            end_t = time.time()
                            is_alive = True
                            latency = round((end_t - start_t) * 1000, 1)
                            error_type = None
                            break
                    except ConnectionRefusedError:
                        is_alive = False
                        error_type = "refused"
                    except (socket.timeout, TimeoutError):
                        is_alive = False
                        error_type = "timeout"
                    except Exception as e:
                        is_alive = False
                        err_str = str(e).lower()
                        if "unreachable" in err_str or "host down" in err_str:
                            error_type = "unreachable"
                        else:
                            error_type = "timeout"
                    if attempt < retries - 1:
                        time.sleep(0.1)
                if is_alive:
                    break

        return is_alive, latency, method, error_type

# Enable CORS manually to avoid external flask-cors dependency
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'POST,GET,OPTIONS'
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

@app.route('/ping', methods=['OPTIONS'])
def options_ping():
    return '', 204

@app.route('/status', methods=['OPTIONS'])
def options_status():
    return '', 204

@app.route('/ping', methods=['POST'])
def run_ping():
    data = request.get_json()
    if not data or 'server_ips' not in data:
        return jsonify({'error': 'server_ips list is required'}), 400

    server_ips = data.get('server_ips', [])
    use_raw = data.get('use_raw', True)
    
    # Process the batch concurrently using ThreadPoolExecutor submit
    futures = [executor.submit(check_host_sync, ip, use_raw) for ip in server_ips]
    results_raw = [f.result() for f in futures]

    results = []
    for ip, (alive, latency, method, error) in zip(server_ips, results_raw):
        results.append({
            'ip': ip,
            'alive': alive,
            'latency': latency,
            'method': method,
            'error': error
        })

    return jsonify({'results': results})

@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint for the web frontend to verify if the worker is up."""
    # Check if raw sockets can be created (if running as root/admin)
    has_raw_privilege = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        s.close()
        has_raw_privilege = True
    except PermissionError:
        has_raw_privilege = False
    except Exception:
        pass

    return jsonify({
        'status': 'online',
        'platform': platform.system(),
        'has_raw_privilege': has_raw_privilege,
        'tunnel_url': tunnel_url
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="APP.ping Python Worker Service")
    parser.add_argument('--port', type=int, default=5000, help="Port to run the service on (default: 5000)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Binding address (default: 0.0.0.0)")
    parser.add_argument('--tunnel', action='store_true', help="Start npx localtunnel automatically")
    args = parser.parse_args()

    if args.tunnel:
        t = threading.Thread(target=start_tunnel_thread, args=(args.port,), daemon=True)
        t.start()

    print(f"Starting APP.ping Worker on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
