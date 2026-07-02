# APP.ping Python Worker

This is a lightweight, cross-platform Python worker service that implements asynchronous ping measurements using Python's **raw sockets**. It serves as the backend for the "비동기 대용량 핑" dashboard.

## Requirements

The worker requires Python 3.8+ and Flask.

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Worker

Since raw sockets (`socket.SOCK_RAW`) require administrator/root privileges, you must run the server with elevated permissions:

### macOS / Linux
Run the server with `sudo`:
```bash
sudo python worker.py --port 5000
```

### Windows
Open a command prompt (cmd) or PowerShell as **Administrator** and run:
```cmd
python worker.py --port 5000
```

### Running without privileges (Fallback Mode)
If you run the worker without administrator/root privileges:
```bash
python worker.py --port 5000
```
It will start successfully but raise a warning that raw sockets are unavailable. The worker will automatically fall back to:
1. Executing the **System Ping Command** (e.g. `ping -c 1` or `ping -n 1` via `subprocess`).
2. Checking **TCP Ports (80 & 443)** if the ping CLI fails.

---

## API Endpoints

### 1. `GET /status`
Checks the worker's status and whether it has raw socket privileges.
* **Response**:
  ```json
  {
    "status": "online",
    "platform": "Darwin",
    "has_raw_privilege": true
  }
  ```

### 2. `POST /ping`
Checks the state of a batch of IPs concurrently.
* **Payload**:
  ```json
  {
    "server_ips": ["1.1.1.1", "8.8.8.8", "invalid_ip_or_host"],
    "use_raw": true
  }
  ```
* **Response**:
  ```json
  {
    "results": [
      {
        "ip": "1.1.1.1",
        "alive": true,
        "latency": 15.2,
        "method": "raw_socket"
      },
      {
        "ip": "8.8.8.8",
        "alive": true,
        "latency": 32.1,
        "method": "raw_socket"
      },
      {
        "ip": "invalid_ip_or_host",
        "alive": false,
        "latency": null,
        "method": "raw_socket"
      }
    ]
  }
  ```
