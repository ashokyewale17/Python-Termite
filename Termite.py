import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Entry, Button, Combobox
from tkinter import scrolledtext
from ttkbootstrap import Style
from ttkbootstrap import ttk
import serial
import serial.tools.list_ports
import threading

class ModernSerialTermite:
    def __init__(self, root):
        self.root = root
        self.style = Style("flatly")  # Choose from: darkly, flatly, morph, etc.
        self.root.title("Python Termite")
        self.serial_port = None
        self.alive = False

        self.build_ui()

    def build_ui(self):
        # Top Frame 
        top_frame = ttk.Frame(self.root, padding=15)
        top_frame.pack(fill="x")

        self.port_combo = Combobox(top_frame, values=self.get_ports(), width=20, bootstyle="primary")
        self.port_combo.set("Select Port")
        self.port_combo.pack(side="left", padx=(0, 15))

        self.baud_combo = Combobox(top_frame, values=[9600, 115200, 230400], width=15, bootstyle="info")
        self.baud_combo.set("Baud Rate")
        self.baud_combo.pack(side="left", padx=(0, 20))

        self.connect_btn = Button(top_frame, text="Connect", bootstyle="success", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=(0, 25))

        self.clear_btn = Button(top_frame, text="Clear", bootstyle="warning", command=self.clear_output)
        self.clear_btn.pack(side="left")

        # Terminal Output 
        self.output = scrolledtext.ScrolledText(self.root, height=20, bg="#121212", fg="#00ff88",
                                                insertbackground="white", font=("Consolas", 10), wrap="word",
                                                borderwidth=1, relief="flat")
        self.output.pack(padx=15, pady=(5, 10), fill="both", expand=True)

        # Bottom Frame 
        bottom_frame = ttk.Frame(self.root, padding=15)
        bottom_frame.pack(fill="x")

        self.input_entry = Entry(bottom_frame, width=80)
        self.input_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.input_entry.bind("<Return>", self.send_data)

        self.send_btn = Button(bottom_frame, text="Send", bootstyle="primary", command=self.send_data)
        self.send_btn.pack(side="left")

    def get_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.alive = False
            self.serial_port.close()
            self.connect_btn.config(text="Connect", bootstyle="success")
            self.write_to_output("[Disconnected]\n", "info")
        else:
            try:
                self.serial_port = serial.Serial(
                    self.port_combo.get(),
                    baudrate=int(self.baud_combo.get()),
                    timeout=0.1
                )
                self.alive = True
                self.connect_btn.config(text="Disconnect", bootstyle="danger")
                self.write_to_output(f"[Connected to {self.port_combo.get()} @ {self.baud_combo.get()} baud]\n", "success")
                threading.Thread(target=self.read_from_port, daemon=True).start()
            except Exception as e:
                self.write_to_output(f"[Error] {e}\n", "error")

    def read_from_port(self):
        while self.alive:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    self.write_to_output(data.decode(errors="replace"))
            except Exception as e:
                self.write_to_output(f"[Read Error] {e}\n", "error")
                break

    def send_data(self, event=None):
        data = self.input_entry.get()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write(data.encode())
            self.input_entry.delete(0, tk.END)
        else:
            self.write_to_output("[Not connected]\n", "warning")

    def write_to_output(self, text, tag=None):
        self.output.config(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTermite(root)
    root.mainloop()
