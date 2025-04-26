import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, Menu
import serial
import serial.tools.list_ports
import threading
import time
import binascii

class SerialTermite:
    def __init__(self, master):
        self.master = master
        self.master.title("Python Termite")
        self.serial_port = None
        self.alive = False
        self.hex_view = True  # Default to hex view like Termite
        self.line_ending = "\n"  # Default to LF
        self.pending_response = False  # Track if we're waiting for a response
        self.current_command = ""
        self.response_buffer = ""  # To accumulate multi-part responses

        
       # --- Top control frame ---
        top_frame = ttk.Frame(master)
        top_frame.pack(side="top", fill="x", padx=5, pady=5)

        # Port selection
        self.port_label = ttk.Label(top_frame, text="Port:")
        self.port_label.pack(side="left", padx=(0, 8))
        
        self.port_box = ttk.Combobox(top_frame, values=self.get_ports(), width=10)
        self.port_box.pack(side="left", padx=(0, 10))
    
        
        ports = self.get_ports()
        if ports:
            self.port_box.set(ports[0])

        # Baud rate selection
        self.baud_label = ttk.Label(top_frame, text="Baud:")
        self.baud_label.pack(side="left", padx=(10, 8))
        
        self.baud_box = ttk.Combobox(top_frame, values=[
            300, 600, 1200, 2400, 4800, 9600, 14400], width=10)
        self.baud_box.current(5)  # 9600
        self.baud_box.pack(side="left", padx=(0, 10))

        # Connect button
        self.connect_btn = ttk.Button(top_frame, text="Connect", command=self.connect)
        self.connect_btn.pack(side="left", padx=(10, 5))

        # Clear button
        self.clear_btn = ttk.Button(top_frame, text="Clear", command=self.clear_output)
        self.clear_btn.pack(side="left", padx=(10, 5))

        # Output area - using fixed width font for alignment
        self.output = scrolledtext.ScrolledText(master, height=20, width=70, state="disabled", wrap="none",font=('Courier New', 12))
        self.output.tag_config("red_text", foreground="red")
        self.output.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # --- Bottom input frame ---
        bottom_frame = ttk.Frame(master)
        bottom_frame.pack(side="top", fill="x", padx=5, pady=5)

        # Input field and send button
        self.input_field = tk.Entry(bottom_frame, width=60, font=('Courier New', 12))
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=2)
        self.input_field.bind("<Return>", self.send_data)

        self.send_btn = ttk.Button(bottom_frame, text="Send", command=self.send_data)
        self.send_btn.pack(side="right", ipady=3)
        

    def get_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]


    def connect(self):
        if self.serial_port and self.serial_port.is_open:
            self.disconnect()
            return

        port = self.port_box.get()
        if not port:
            messagebox.showerror("Error", "No port selected!")
            return

        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=int(self.baud_box.get()),
                timeout=0.1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                rtscts=False,
                dsrdtr=False,
                xonxoff=False
            )
            
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

            self.alive = True
            self.connect_btn.config(text="Disconnect")
            self.write_to_output(f"Connected to {self.serial_port.port} @ {self.serial_port.baudrate} bps\n")
            
            threading.Thread(target=self.read_from_port, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.write_red_output(f"Connection error: {e}\n")

    def disconnect(self):
        self.alive = False
        if self.serial_port and self.serial_port.is_open:
            time.sleep(0.1)
            self.serial_port.close()
        self.connect_btn.config(text="Connect")
        self.write_red_output("Disconnected.\n")

    def send_data(self, event=None):
        data = self.input_field.get()
        if not data:
            return
        
        if self.serial_port and self.serial_port.is_open:
            try:
                # Clean the input data
                clean_data = data.replace(" ", "").replace("\n", "").replace("\r", "")
            
                # Convert to bytes and add line ending
                data_to_send = binascii.unhexlify(clean_data) + self.line_ending.encode()
            
                self.serial_port.write(data_to_send)
                self.serial_port.flush()

                # If we were waiting for a previous response, complete that line
                if self.pending_response:
                    self.write_to_output(f"{self.response_buffer}\n")
                    self.response_buffer = ""
            
                # Store the command and display with arrow
                self.current_command = clean_data.lower()
                self.write_to_output(f"{self.current_command} -> ")
                self.pending_response = True

                # Set expected response length based on command
                if self.current_command.startswith("ff"):
                    self.expected_length = 20
                elif self.current_command.startswith("20") or self.current_command.startswith("30"):
                    self.expected_length = 10
                else:
                    self.expected_length = 0  # fallback

                self.response_bytes = b""
                self.waiting_for_response = True

            
                self.input_field.delete(0, tk.END)
            
            except Exception as e:
                self.write_red_output(f"\nError: {e}\n")
        else:
            self.write_red_output("Not connected.\n")
            
    def read_from_port(self):
        while self.alive and self.serial_port and self.serial_port.is_open:
            try:
                data = self.serial_port.read(self.serial_port.in_waiting or 1)
                if data:
                    self.process_received_data(data)
            except Exception as e:
                self.write_to_output(f"\nRead error: {e}\n")
                break

    def process_received_data(self, data):
        if data and self.pending_response:
            # Convert bytes to continuous hex
            hex_str = "".join(f"{b:02x}" for b in data)
            self.response_buffer += hex_str
        
            # Get the current line content
            self.output.config(state="normal")
            lines = self.output.get("1.0", "end-1c").splitlines()
        
            if lines:
                # Replace the last line with command -> accumulated response
                self.output.delete("end-2l linestart", "end-1c")
                
                # Insert command with red tag
                self.output.insert("end-1c", self.current_command, "red_text")

                # Insert arrow and response as normal white text
                self.output.insert("end-1c", f" -> {self.response_buffer}")

        
            self.output.see(tk.END)
            self.output.config(state="disabled")
    
        
    def write_to_output(self, text):
        self.output.config(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def write_red_output(self, text):
        self.output.config(state="normal")
        self.output.insert(tk.END, text, "red_text")
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def clear_output(self):
        self.output.config(state="normal")
        self.output.delete(1.0, tk.END)
        self.output.config(state="disabled")

    def on_closing(self):
        self.disconnect()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTermite(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
