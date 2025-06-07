import tkinter as tk
from tkinter import ttk

class FileProgress_widget(tk.Frame): # Corrected inheritance from tk.Frame
    def __init__(self, parent=None, log_size=5):
        tk.Frame.__init__(self, parent)

        # Using Text widget for log as it handles multiple lines better
        self.log_widget = tk.Text(self, state=tk.DISABLED, height=log_size, width=45)
        self.log_widget.pack(fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        self.progress_count_label = tk.Label(self, text="0/0")
        self.progress_count_label.pack(fill=tk.X)

        self.log_size = log_size # This variable is not used with the Text widget, but can be kept for consistency or removed.

    def log(self, msg):
        self.log_widget.config(state=tk.NORMAL)
        self.log_widget.insert(tk.END, msg + "\n")
        self.log_widget.see(tk.END) # Auto-scroll to the end
        self.log_widget.config(state=tk.DISABLED)
        self.update_idletasks() # Ensure GUI updates immediately

    def progress_start(self, total_steps):
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = total_steps
        self.progress_count_label.config(text=f"0/{total_steps}")
        self.update_idletasks()

    def progress(self, current_steps):
        # The 'progress' method should set the value directly, not increment
        self.progress_bar['value'] = current_steps
        self.progress_count_label.config(text=f"{current_steps}/{self.progress_bar['maximum']}")
        self.update_idletasks()

    def progress_end(self):
        self.progress_bar['value'] = self.progress_bar['maximum']
        self.progress_count_label.config(text=f"{self.progress_bar['maximum']}/{self.progress_bar['maximum']} - Complete!")
        self.update_idletasks()

    # --- Methods required by LiveTuningAccess ---

    def download(self, address, size, filename, read_fn, chunk_size):
        self.log(f"Downloading from 0x{address:08X} (size {size} bytes) to {filename}")
        self.progress_start(size)
        data = bytearray()
        bytes_read = 0
        while bytes_read < size:
            current_chunk_size = min(chunk_size, size - bytes_read)
            chunk = read_fn(address + bytes_read, current_chunk_size)
            data.extend(chunk)
            bytes_read += current_chunk_size
            self.progress(bytes_read)
        with open(filename, 'wb') as f:
            f.write(data)
        self.progress_end()
        self.log("Download complete.")

    def upload(self, address, filename, write_fn, chunk_size, use_fp=True, start_offset=0, size_to_upload=None):
        with open(filename, 'rb') as f:
            f.seek(start_offset)
            file_data = f.read()

        if size_to_upload is None:
            size_to_upload = len(file_data)
        else:
            file_data = file_data[:size_to_upload] # Ensure we only use the specified size

        self.log(f"Uploading {len(file_data)} bytes from {filename} to 0x{address:08X}")
        if use_fp:
            self.progress_start(len(file_data))

        bytes_written = 0
        while bytes_written < len(file_data):
            current_chunk = file_data[bytes_written:bytes_written + chunk_size]
            write_fn(address + bytes_written, current_chunk)
            bytes_written += len(current_chunk)
            if use_fp:
                self.progress(bytes_written)
        if use_fp:
            self.progress_end()
        self.log("Upload complete.")

    def verify(self, address, filename, read_fn, chunk_size):
        self.log(f"Verifying {filename} against 0x{address:08X}")
        with open(filename, 'rb') as f:
            file_data = f.read()

        self.progress_start(len(file_data))
        bytes_verified = 0
        from lib.ltacc import ECUException # Import ECUException here to avoid circular dependency
        while bytes_verified < len(file_data):
            current_chunk_size = min(chunk_size, len(file_data) - bytes_verified)
            ecu_chunk = read_fn(address + bytes_verified, current_chunk_size)
            file_chunk = file_data[bytes_verified : bytes_verified + current_chunk_size]

            if ecu_chunk != file_chunk:
                self.log(f"Verification FAILED at 0x{address + bytes_verified:08X}")
                raise ECUException("Verification failed!") # Re-raise the exception from ltacc
            
            bytes_verified += current_chunk_size
            self.progress(bytes_verified)
        self.log("Verification SUCCESSFUL!")
        self.progress_end()