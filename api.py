import time
import threading
from flask import Flask, render_template, request
from netmiko import ConnectHandler

app = Flask(__name__)

# Connection settings for the EVE-NG router.
ROUTER = {
    "device_type": "cisco_ios_telnet",
    "ip": "192.168.10.82",
    "port": 32770,
    "username": "admin",
    "password": "eve123",
    "secret": "eve123",
    # EVE-NG routers are slow, so give Netmiko more time.
    "global_delay_factor": 2,
    "timeout": 60,
    "session_log": "netmiko_debug.log",  # shows what the router really sent; remove once it works
}

COMMANDS = [
    "show version",
    "show ip interface brief",
    "show running-config",
]

# Only these fields are shown on the page. Credentials never reach the template.
DEVICE_INFO = {
    "name": "Cisco router in the EVE-NG lab",
    "address": ROUTER["ip"],
    "port": ROUTER["port"],
    "protocol": "Telnet",
}

# The router console allows one session at a time, so only one run at once.
run_lock = threading.Lock()


@app.route("/", methods=["GET", "POST"])
def index():
    results = {}
    timings = {}
    total = 0.0
    error = None

    if request.method == "POST":
        if not run_lock.acquire(blocking=False):
            error = "Another diagnostics run is still in progress. Wait a moment and try again."
        else:
            net_connect = None
            try:
                net_connect = ConnectHandler(**ROUTER)
                net_connect.enable()

                start = time.time()
                for cmd in COMMANDS:
                    t0 = time.time()
                    results[cmd] = net_connect.send_command(cmd, read_timeout=60)
                    timings[cmd] = round(time.time() - t0, 2)
                total = round(time.time() - start, 2)
            except Exception as e:
                error = f"Connection failed: {e}"
            finally:
                # Always release the console, even when something fails.
                if net_connect:
                    try:
                        net_connect.disconnect()
                    except Exception:
                        pass
                run_lock.release()

    return render_template(
        "index.html",
        device=DEVICE_INFO,
        commands=COMMANDS,
        results=results,
        timings=timings,
        total=total,
        error=error,
        ran=request.method == "POST",
    )


if __name__ == "__main__":
    # use_reloader=False stops debug mode from starting a second process
    # that could grab the router console twice.
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)