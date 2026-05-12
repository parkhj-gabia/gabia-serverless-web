import argparse
import os
import subprocess
import sys
import platform

def main():
    parser = argparse.ArgumentParser(description="L2 switch IP address to check.")
    parser.add_argument("L2IpAddress", type=str, help="Enter the L2 switch IP address to check.")
    args = parser.parse_args()

    l2_ip = args.L2IpAddress
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # l2.list 파일을 사용하도록 지정
    list_file_path = os.path.join(script_dir, "l2.list")

    if not os.path.exists(list_file_path):
        print(f"\033[91mError: Cannot find file '{list_file_path}'.\033[0m")
        sys.exit(1)

    is_found = False
    l2_comment = ""
    server_ips = []

    try:
        with open(list_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('#', 1)
                clean_line = parts[0].strip()
                comment = parts[1].strip() if len(parts) > 1 else ""

                if not is_found:
                    if clean_line == l2_ip:
                        is_found = True
                        l2_comment = comment
                else:
                    if clean_line.startswith("-"):
                        ip = clean_line[1:].strip()
                        server_ips.append(ip)
                    else:
                        break
    except Exception as e:
        print(f"\033[91mError reading file: {e}\033[0m")
        sys.exit(1)

    if not is_found:
        print(f"\033[93mResult: '{l2_ip}' is not in the list.\033[0m")
        sys.exit(0)
    
    if not server_ips:
        print(f"\033[93mResult: No server IPs found under '{l2_ip}'.\033[0m")
        sys.exit(0)

    header_text = f"L2 IP [{l2_ip}]"
    if l2_comment:
        header_text += f" (# {l2_comment})"
    header_text += " Sub-server Ping Test Results"

    # Cyan color
    print(f"\033[96m{header_text}\033[0m")
    print(f"\033[96m{'-' * 50}\033[0m")

    # ping 명령어 파라미터 (Windows는 -n, Mac/Linux는 -c)
    ping_param = '-n' if platform.system().lower() == 'windows' else '-c'

    for ip in server_ips:
        # ping 1회 전송
        command = ['ping', ping_param, '1', ip]
        try:
            # 2초 이내에 응답이 없으면 timeout 처리
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            is_alive = (result.returncode == 0)
        except subprocess.TimeoutExpired:
            is_alive = False
        except Exception:
            is_alive = False

        if is_alive:
            # Green color
            print(f"\033[92m [OK] Alive : {ip}\033[0m")
        else:
            # Red color
            print(f"\033[91m [XX] Dead  : {ip}\033[0m")

    # Cyan color
    print(f"\033[96m{'-' * 50}\033[0m")

if __name__ == "__main__":
    main()
