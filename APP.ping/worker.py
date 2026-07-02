import os
import sys
import time
import socket
import struct
import select
import platform
import subprocess
import argparse
import asyncio
from flask import Flask, request, jsonify

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

def ping_one_raw(ip, timeout=2.0):
    """
    Send an ICMP Echo Request using Python raw sockets and wait for Echo Reply.
    Returns: (is_alive: bool, latency_ms: float or None)
    """
    try:
        dest_addr = socket.gethostbyname(ip)
    except socket.gaierror:
        return False, None

    try:
        # Requires root/administrator privileges
        icmp_proto = socket.getprotobyname("icmp")
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
    except PermissionError as e:
        # Propagate permission error to invoke fallback logic
        raise e
    except Exception:
        return False, None

    my_socket.settimeout(timeout)
    
    # Generate unique ID and Sequence Number
    packet_id = (os.getpid() ^ int(time.time() * 1000)) & 0xFFFF
    seq_num = 1
    
    # Pack header with checksum=0 first
    # Format: !BBHHH (Type=8, Code=0, Checksum=0, ID, Seq)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, packet_id, seq_num)
    data = struct.pack("d", time.time())
    
    # Calculate checksum and repack header
    my_checksum = calculate_checksum(header + data)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, my_checksum, packet_id, seq_num)
    packet = header + data
    
    try:
        my_socket.sendto(packet, (dest_addr, 1))
        
        started_select = time.time()
        while True:
            how_long_in_select = time.time() - started_select
            if how_long_in_select >= timeout:
                return False, None
                
            what_ready = select.select([my_socket], [], [], timeout - how_long_in_select)
            if what_ready[0] == []:
                return False, None
                
            time_received = time.time()
            rec_packet, addr = my_socket.recvfrom(1024)
            
            # Read IP Header Length to find the start of the ICMP Header
            # The first byte contains Version (4 bits) and Internet Header Length (IHL) in 32-bit words
            ip_header_len = (rec_packet[0] & 0x0F) * 4
            icmp_header = rec_packet[ip_header_len : ip_header_len + 8]
            
            type, code, checksum_val, rec_id, rec_seq = struct.unpack("!BBHHH", icmp_header)
            
            # Type 0 = Echo Reply
            if type == 0 and rec_id == packet_id and rec_seq == seq_num:
                latency = (time_received - started_select) * 1000
                return True, round(latency, 1)
    except Exception:
        return False, None
    finally:
        my_socket.close()

def check_host_sync(ip, use_raw=True):
    """
    Checks if a host is alive using Raw Socket, System Ping, or TCP Connect sequentially.
    Returns: (is_alive, latency, method)
    """
    # 1. Try Raw Socket ICMP
    if use_raw:
        try:
            alive, latency = ping_one_raw(ip, timeout=2.0)
            return alive, latency, "raw_socket"
        except PermissionError:
            # Fall through to permissionless methods
            pass
        except Exception:
            return False, None, "raw_socket"

    # 2. First Fallback: System Ping CLI command
    is_alive = False
    latency = None
    method = "system_ping"
    
    if platform.system().lower() == 'windows':
        command = ['ping', '-n', '1', ip]
    else:
        command = ['ping', '-c', '1', '-n', '-W', '2', ip]
        
    try:
        start_t = time.time()
        res = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        end_t = time.time()
        if res.returncode == 0:
            is_alive = True
            latency = round((end_t - start_t) * 1000, 1)
    except Exception:
        is_alive = False

    # 3. Second Fallback: TCP Port checks (80 / 443)
    if not is_alive:
        method = "tcp_port"
        for port in [80, 443]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.5)
                    start_t = time.time()
                    s.connect((ip, port))
                    end_t = time.time()
                    is_alive = True
                    latency = round((end_t - start_t) * 1000, 1)
                    break
            except Exception:
                pass

    return is_alive, latency, method

async def check_host_async(ip, use_raw=True):
    """Run check_host_sync asynchronously in a worker thread."""
    return await asyncio.to_thread(check_host_sync, ip, use_raw)

# Enable CORS manually to avoid external flask-cors dependency
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'POST,GET,OPTIONS'
    return response

@app.route('/ping', methods=['OPTIONS'])
def options_ping():
    return '', 204

@app.route('/ping', methods=['POST'])
def run_ping():
    data = request.get_json()
    if not data or 'server_ips' not in data:
        return jsonify({'error': 'server_ips list is required'}), 400

    server_ips = data.get('server_ips', [])
    use_raw = data.get('use_raw', True)
    
    # Process the batch concurrently via asyncio loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        tasks = [check_host_async(ip, use_raw) for ip in server_ips]
        results_raw = loop.run_until_complete(asyncio.gather(*tasks))
    finally:
        loop.close()

    results = []
    for ip, (alive, latency, method) in zip(server_ips, results_raw):
        results.append({
            'ip': ip,
            'alive': alive,
            'latency': latency,
            'method': method
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
        'has_raw_privilege': has_raw_privilege
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="APP.ping Python Worker Service")
    parser.add_argument('--port', type=int, default=5000, help="Port to run the service on (default: 5000)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Binding address (default: 0.0.0.0)")
    args = parser.parse_args()

    print(f"Starting APP.ping Worker on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
