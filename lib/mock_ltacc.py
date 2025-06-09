# lib/mock_ltacc.py

import random
import os # Import os for path handling and file existence check

# Some constants
BO_BE = 'big'

class ECUException(Exception):
    pass

class MockLiveTuningAccess:
    """
    A mock class for LiveTuningAccess to simulate ECU communication
    without a physical CAN device.
    """
    def __init__(self, fp):
        self.fp = fp
        self.mock_memory = {}
        self.sym_map = None
        self.sram_content = None # New: To store loaded SRAM content
        self.sram_base_addr = 0x40000000 # Base address for simulated SRAM

    def set_sym_map(self, sym_map_obj):
        self.sym_map = sym_map_obj

    def load_sram_content(self, filepath):
        """Loads a binary file into mock SRAM content."""
        if not os.path.exists(filepath):
            self.fp.log(f"DEBUG MODE: SRAM file not found at {filepath}. SRAM emulation will not use file content.")
            self.sram_content = None
            return

        try:
            with open(filepath, 'rb') as f:
                self.sram_content = f.read()
            self.fp.log(f"DEBUG MODE: Loaded {len(self.sram_content)} bytes of SRAM content from {filepath}.")
        except Exception as e:
            self.fp.log(f"DEBUG MODE: Error loading SRAM content from {filepath}: {e}")
            self.sram_content = None

    def open_can(self, interface, channel, bitrate):
        self.fp.log(f"DEBUG MODE: Simulating CAN device connection (Interface: {interface}, Channel: {channel}, Bitrate: {bitrate})")

    def close_can(self):
        self.fp.log("DEBUG MODE: Simulating CAN device disconnection.")

    def read_memory(self, address, size):
        self.fp.log(f"DEBUG MODE: Simulating read from 0x{address:08X} with size {size}")

        # Check for SRAM content first if loaded
        if self.sram_content is not None:
            sram_end_addr = self.sram_base_addr + len(self.sram_content)
            # Check if the requested address range overlaps with loaded SRAM content
            if address >= self.sram_base_addr and address < sram_end_addr:
                offset = address - self.sram_base_addr
                # Determine how much data can actually be read from the loaded content
                available_bytes = max(0, len(self.sram_content) - offset)
                bytes_to_read = min(size, available_bytes)

                if bytes_to_read > 0:
                    read_data = self.sram_content[offset : offset + bytes_to_read]
                    # If the requested size is larger than available, pad with zeros
                    if len(read_data) < size:
                        self.fp.log(f"DEBUG MODE: Read from SRAM (0x{address:08X}) requested {size} bytes, but only {len(read_data)} bytes available from file. Padding with zeros.")
                        read_data += b'\x00' * (size - len(read_data))
                    return read_data
                else:
                    self.fp.log(f"DEBUG MODE: Read from SRAM (0x{address:08X}) falls outside loaded content. Returning random bytes.")
                    return bytes([random.randint(0, 255) for _ in range(size)]) # Fallback for out of bounds reads within SRAM zone


        # Use the provided sym_map to get the actual address for "cal_base"
        cal_base_addr = None
        if self.sym_map:
            try:
                cal_base_addr = self.sym_map.get_sym_addr("cal_base")
            except KeyError:
                pass

        if cal_base_addr is not None and address == cal_base_addr and size == 4:
            return b"P138" # Simulate the correct ECU firmware

        # Simulate sensor readings with random but plausible values using sym_map
        if self.sym_map:
            try:
                if address == self.sym_map.get_sym_addr("engine_speed"):
                    return int(random.uniform(700, 6000)).to_bytes(2, BO_BE) # Random RPM
                if address == self.sym_map.get_sym_addr("engine_load"):
                    return int(random.uniform(100, 800)).to_bytes(2, BO_BE) # Random Load
                if address == self.sym_map.get_sym_addr("coolant"):
                    return int(random.uniform(80, 100) * 8 / 5 + 40 * 8 / 5).to_bytes(1, BO_BE) # Random Coolant (approx 80-100C)
                if address == self.sym_map.get_sym_addr("air"):
                    return int(random.uniform(20, 50) * 8 / 5 + 40 * 8 / 5).to_bytes(1, BO_BE) # Random IAT (approx 20-50C)
                # ... add more specific symbol-based mock data as needed
            except KeyError:
                pass

        # For any other address (not SRAM and not a known symbol), return random bytes
        return bytes([random.randint(0, 255) for _ in range(size)])

    def write_memory(self, address, data, verify=False):
        self.fp.log(f"DEBUG MODE: Simulating write to 0x{address:08X} with data {data.hex()}")
        # If you want to simulate writes to SRAM, you'd update self.sram_content here
        if self.sram_content is not None:
            sram_end_addr = self.sram_base_addr + len(self.sram_content)
            if address >= self.sram_base_addr and address < sram_end_addr:
                offset = address - self.sram_base_addr
                # This simple mock doesn't handle writing beyond the loaded content
                # or resizing it. It just updates within the loaded bounds.
                if offset + len(data) <= len(self.sram_content):
                    self.sram_content = bytearray(self.sram_content)
                    self.sram_content[offset : offset + len(data)] = data
                    self.sram_content = bytes(self.sram_content) # Convert back to bytes if immutable is preferred
                    self.fp.log(f"DEBUG MODE: Simulated write to SRAM at 0x{address:08X}.")
                else:
                    self.fp.log(f"DEBUG MODE: Simulated write to SRAM at 0x{address:08X} ignored (out of loaded SRAM bounds).")

        if verify:
            self.fp.log("DEBUG MODE: Write verification skipped in mock mode.")

    def upload_verify(self, address, filename):
        self.fp.log(f"DEBUG MODE: Simulating upload of {filename} to 0x{address:08X}")

    def download_verify(self, address, size, filename):
        self.fp.log(f"DEBUG MODE: Simulating download of {size} bytes from 0x{address:08X} to {filename}")