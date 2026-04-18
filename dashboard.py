import customtkinter as ctk
import serial
import threading
import math

SERIAL_PORT = '/dev/tty.usbserial-21402'
BAUD_RATE = 115200

class TrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Spatial Tracker")
        self.geometry("500x600")
        ctk.set_appearance_mode("dark")
        
        self.header = ctk.CTkLabel(self, text="TARGET ACQUISITION", font=("Helvetica", 12, "bold"), text_color="#555555")
        self.header.pack(pady=(30, 0))
        
        self.readout = ctk.CTkLabel(self, text="SEARCHING...", font=("Helvetica", 24))
        self.readout.pack(pady=10)
        
        self.canvas = ctk.CTkCanvas(self, width=400, height=400, bg="#111111", highlightthickness=0)
        self.canvas.pack(pady=20)
        
        self.center_x = 200
        self.center_y = 200
        self.radius = 150
        
        # Start background task to read hardware data
        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()

    def read_serial(self):
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('+UUDF'):
                    parts = line.split(',')
                    if len(parts) > 4:
                        mac = parts[1]
                        az = int(parts[2])
                        el = int(parts[3])
                        # Push updates to the main UI thread safely
                        self.after(0, self.update_display, mac, az, el)
        except Exception as e:
            self.after(0, self.update_display, "ERROR", 0, 0)

    def update_display(self, mac, az, el):
        self.readout.configure(text=f"ID {mac}  |  AZ {az}°  |  EL {el}°")
        self.canvas.delete("all")
        
        # Draw clean reference geometry
        self.canvas.create_oval(self.center_x - self.radius, self.center_y - self.radius,
                                self.center_x + self.radius, self.center_y + self.radius,
                                outline="#333333", width=2)
        
        # Convert to radians for math operations
        az_rad = math.radians(az)
        el_rad = math.radians(el)
        
        # Calculate 3D to 2D projection
        x = self.radius * math.sin(az_rad) * math.cos(el_rad)
        z = self.radius * math.sin(el_rad)
        
        end_x = self.center_x - x
        end_y = self.center_y - z
        
        # Render the tracking line and node
        self.canvas.create_line(self.center_x, self.center_y, end_x, end_y, fill="#007AFF", width=4)
        self.canvas.create_oval(end_x - 6, end_y - 6, end_x + 6, end_y + 6, fill="#FFFFFF", outline="#007AFF", width=2)

if __name__ == "__main__":
    app = TrackerApp()
    app.mainloop()