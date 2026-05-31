#!/usr/bin/env python3
import sys
import os
import re
import json
from datetime import datetime, timedelta

def get_normalize_center(n):
    if n in ["강남", "서초"]:
        return "서초"
    if n in ["과천", "가산"]:
        return "가산"
    return n

def main():
    try:
        # Read JSON string from standard input
        input_data = sys.stdin.read()
        if not input_data:
            print("Error: Stdin is empty.")
            sys.exit(1)
            
        data = json.loads(input_data)
        worker_name = data.get('workerName', '').strip()
        date_str = data.get('date', '').strip()
        dailywork_content = data.get('dailyworkContent', '')
    except Exception as e:
        print(f"Error parsing input JSON: {e}")
        sys.exit(1)

    if not worker_name:
        print("Error: workerName is required.")
        sys.exit(1)

    # Date logic: if date_str is provided, use it, otherwise default to yesterday
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("Error: Date format must be YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = datetime.now() - timedelta(days=1)

    # Constants
    K_GS = "가산"
    K_SC = "서초"
    K_GN = "강남"
    K_GC = "과천"
    K_HI = "하이웍스"
    K_WH = "웹훅"
    K_NW = "야간근무자"
    K_OU = "운영유닛"
    K_N1 = "없음"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_list_path = os.path.join(script_dir, "userlist.txt")
    template_path = os.path.join(script_dir, "template.txt")

    if not os.path.exists(user_list_path):
        print(f"Error: userlist.txt not found at {user_list_path}")
        sys.exit(1)
        
    primary_workers = [pw.strip() for pw in worker_name.split(",")]
    korean_names = []
    target_dcs = []

    # Read userlist.txt (UTF-8 encoding)
    with open(user_list_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            for pw in primary_workers:
                pattern = rf"^([^\(]+)\(.*{re.escape(pw)}.*:\s*(.+)$"
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    korean_name = match.group(1).strip()
                    dc = match.group(2).strip()
                    korean_names.append(korean_name)
                    if dc not in target_dcs:
                        target_dcs.append(dc)

    if not target_dcs:
        print(f"Error: Worker '{worker_name}' not found in userlist.txt.")
        sys.exit(1)

    date_string = target_date.strftime("%Y-%m-%d")
    days_kor = ["월", "화", "수", "목", "금", "토", "일"]
    day_of_week = days_kor[target_date.weekday()]

    if not korean_names:
        sys.exit(0)

    target_dc = get_normalize_center(target_dcs[0]).strip()
    header_line = f"{date_string} ({day_of_week}) {K_NW} - IDC{K_OU} {worker_name}"

    work_items = []
    for line in dailywork_content.splitlines():
        line = line.strip('\r\n')
        if not line.strip():
            continue
        cols = line.split('\t')
        if len(cols) >= 8:
            w = cols[1].strip()
            w_list = [ws.strip() for ws in w.split(',')]
            
            found = False
            for ws in w_list:
                if ws in korean_names:
                    found = True
                    break
            if not found:
                continue

            time_val = 0
            time_str = ""
            match_time = re.search(r"\s(\d{2}:\d{2})", cols[0])
            if match_time:
                time_str = match_time.group(1)
                h = int(time_str[:2])
                m = int(time_str[3:])
                if h < 8:
                    h += 24
                time_val = (h * 60) + m

            work_items.append({
                'Worker': cols[1].strip(),
                'TimeStr': time_str,
                'MemberId': cols[5].strip(),
                'IP': cols[6].strip(),
                'Content': cols[7].strip(),
                'Service': cols[4].strip(),
                'SortVal': time_val
            })

    items_g2 = [
        item for item in work_items
        if (K_HI not in item['Service']) and (K_WH not in item['Content']) and ("83" not in item['Content'])
    ]
    items_g2.sort(key=lambda x: (x['Worker'], x['SortVal']))

    items_g4 = [
        item for item in work_items
        if (K_HI in item['Service']) or (K_WH in item['Content']) or ("83" in item['Content'])
    ]
    items_g4.sort(key=lambda x: (x['Worker'], x['SortVal']))

    output = []
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        in_g3 = False
        in_g4 = False
        in_g6 = False
        line_idx = 0
        
        for raw_line in lines:
            line = raw_line.strip('\r\n')
            if line_idx == 0:
                output.append(header_line)
                line_idx += 1
                continue
            line_idx += 1
            
            if re.match(r"^3\)", line):
                output.append(line)
                in_g3 = True
                if not items_g2:
                    output.append(f"- {K_N1}")
                else:
                    for i in items_g2:
                        output.append(f"- [{i['TimeStr']}] {i['MemberId']} / {i['IP']} - {i['Content']}")
                continue
                
            if re.match(r"^4\)", line):
                output.append("")
                in_g3 = False
                output.append(line)
                in_g4 = True
                if not items_g4:
                    output.append(f"- {K_N1}")
                else:
                    for i in items_g4:
                        output.append(f"- [{i['TimeStr']}] {i['Content']}")
                continue
                
            if re.match(r"^5\)", line):
                output.append("")
                in_g4 = False
                
            if re.match(r"^6\)", line):
                in_g6 = True
                output.append(line)
                continue
                
            if "INTMON ARP" in line or "육안점검" in line:
                continue
                
            if in_g6 and line.strip() == "":
                continue
                
            if re.match(r"^감사", line) or re.match(r"^7\)", line):
                if in_g6:
                    if target_dc == K_GS:
                        output.append("- INTMON ARP 체크 확인 - 가산U+ 정상")
                        output.append("- INTMON ARP 체크 확인 - 과천KINX 정상/가산KINX 정상")
                    else:
                        output.append("- INTMON ARP 체크 확인 - 서초U+/강남 정상")
                        
                    if target_dc == K_SC:
                        output.append("- 카버코리아 육안점검 특이사항 없음 메일 발송 완료")
                        output.append("- 씨젠 육안점검 특이사항 없음 메일 발송 완료")
                    elif target_dc == K_GS:
                        output.append("- 캘러웨이골프 코리아 특이사항 ")
                        output.append("  - 육안점검 메일 발송완료")
                    output.append("")
                in_g6 = False
                
            if not in_g3 and not in_g4:
                output.append(line)

    sys.stdout.write('\n'.join(output) + '\n')

if __name__ == '__main__':
    main()
