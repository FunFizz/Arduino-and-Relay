import os
os.environ['TCL_LIBRARY'] = r"C:\Users\user\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
os.environ['TK_LIBRARY'] = r"C:\Users\user\AppData\Local\Programs\Python\Python313\tcl\tk8.6"


import tkinter as tk
from tkinter import ttk, messagebox
import serial, serial.tools.list_ports, time, threading

BAUD = 9600
DEFAULT_PORT = None  # e.g. "COM3" on Windows, "/dev/ttyACM0" on Linux, "/dev/cu.usbmodemXXXX" on macOS

class RelayGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Arduino Relay Control")
        self.geometry("420x300")
        self.resizable(False, False)

        self.ser = None
        self.connected = False
        self.stop_threads = False

        # Top: Port selector + Connect button
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Serial Port:").pack(side="left", padx=(0,6))
        self.port_var = tk.StringVar(value=DEFAULT_PORT or "")
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var, width=28, state="readonly")
        self.port_combo.pack(side="left", padx=(0,6))
        ttk.Button(top, text="Refresh", command=self.refresh_ports).pack(side="left", padx=4)
        self.connect_btn = ttk.Button(top, text="Connect", command=self.toggle_connect)
        self.connect_btn.pack(side="left", padx=4)

        # Status frame
        status = ttk.LabelFrame(self, text="Status", padding=10)
        status.pack(fill="x", padx=10, pady=(0,10))

        self.fan_state = tk.StringVar(value="OFF")
        self.pump_state = tk.StringVar(value="OFF")

        self.fan_indicator = tk.Label(status, text="FAN: OFF", width=12, relief="groove")
        self.fan_indicator.grid(row=0, column=0, padx=6, pady=6)
        self.pump_indicator = tk.Label(status, text="PUMP: OFF", width=12, relief="groove")
        self.pump_indicator.grid(row=0, column=1, padx=6, pady=6)

        # Controls
        controls = ttk.LabelFrame(self, text="Controls", padding=10)
        controls.pack(fill="x", padx=10, pady=(0,10))

        ttk.Button(controls, text="Fan ON",  command=lambda: self.send_cmd('f')).grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Fan OFF", command=lambda: self.send_cmd('F')).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Pump ON", command=lambda: self.send_cmd('p')).grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Pump OFF",command=lambda: self.send_cmd('P')).grid(row=1, column=1, padx=6, pady=6, sticky="ew")

        ttk.Button(controls, text="All OFF", command=lambda: self.send_cmd('a')).grid(row=2, column=0, columnspan=2, padx=6, pady=6, sticky="ew")

        # Bottom log
        self.log = tk.Text(self, height=6, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Init
        self.refresh_ports()
        self.after(500, self.poll_status_ui)

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if DEFAULT_PORT and DEFAULT_PORT in ports:
            self.port_var.set(DEFAULT_PORT)
        elif ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def toggle_connect(self):
        if not self.connected:
            port = self.port_var.get()
            if not port:
                messagebox.showerror("Error", "Select a serial port.")
                return
            try:
                self.ser = serial.Serial(port, BAUD, timeout=0.2)
                time.sleep(2)  # wait for Arduino reset
                self.connected = True
                self.connect_btn.config(text="Disconnect")
                self.log_line(f"Connected to {port}")
                self.send_cmd('a')  # all OFF on connect
                # start background reader
                self.stop_threads = False
                threading.Thread(target=self.reader_thread, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open {port}\n{e}")
        else:
            self.disconnect()

    def disconnect(self):
        self.stop_threads = True
        if self.ser and self.ser.is_open:
            try:
                self.send_cmd('a')  # safe off
            except Exception:
                pass
            self.ser.close()
        self.connected = False
        self.connect_btn.config(text="Connect")
        self.log_line("Disconnected.")

    def reader_thread(self):
        # Read lines from Arduino and update status if we see "FAN:...,PUMP:..."
        buf = ""
        while not self.stop_threads and self.connected and self.ser and self.ser.is_open:
            try:
                chunk = self.ser.read(128).decode(errors="ignore")
                if chunk:
                    buf += chunk
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line:
                            self.handle_line(line)
            except Exception:
                break

    def handle_line(self, line):
        self.log_line(f"[Arduino] {line}")
        if "FAN:" in line and "PUMP:" in line:
            # Expected format: FAN:ON,PUMP:OFF
            try:
                parts = dict(x.split(":") for x in line.split(","))
                self.update_indicators(parts.get("FAN","OFF"), parts.get("PUMP","OFF"))
            except Exception:
                pass

    def update_indicators(self, fan, pump):
        # Visual indicators: green when ON, default when OFF
        self.fan_indicator.config(text=f"FAN: {fan}")
        self.pump_indicator.config(text=f"PUMP: {pump}")
        self.fan_indicator.config(bg=("lightgreen" if fan.upper()=="ON" else self.cget("bg")))
        self.pump_indicator.config(bg=("lightgreen" if pump.upper()=="ON" else self.cget("bg")))

    def send_cmd(self, c):
        if not self.connected or not self.ser:
            self.log_line("Not connected.")
            return
        try:
            self.ser.write(c.encode("ascii"))
            # Ask for status after each command
            self.ser.write(b's')
        except Exception as e:
            self.log_line(f"Write error: {e}")

    def log_line(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def poll_status_ui(self):
        # Periodically request status so indicators stay in sync (every 1.5s)
        if self.connected:
            try:
                self.ser.write(b's')
            except Exception:
                pass
        self.after(1500, self.poll_status_ui)

    def on_close(self):
        self.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = RelayGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

