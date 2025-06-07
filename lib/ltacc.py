import can # sys and argparse are no longer needed for this library file
from lib.gui_fileprogress import FileProgress_widget # Correctly import FileProgress_widget

# Some constants
# BO_LE is kept for potential future use or if other parts of the project
# (not provided in this context) still rely on it.
BO_LE = 'little'
BO_BE = 'big'

class ECUException(Exception):
    pass

class LiveTuningAccess:
    zones = [
        # T6 (MPC5534) has 1MB flash, 64KB RAM
        ("T6: L0-L1 (Bootloader)", 0x00000000, 0x010000, "bootldr.bin"),
        ("T6: L2 (Learned)"      , 0x00010000, 0x00C000, "decram.bin"),
        ("T6: L3 (Coding)"       , 0x0001C000, 0x004000, "coding.bin"),
        ("T6: L4 (Calibration)"  , 0x00020000, 0x010000, "calrom.bin"),
        ("T6: M0-H3 (Program)"   , 0x00040000, 0x0C0000, "prog.bin"),
        ("T6: RAM (Main RAM)"    , 0x40000000, 0x010000, "calram.bin"),
        ("T6: L0-H3 (Full ROM)"  , 0x00000000, 0x100000, "dump.bin")
    ]

    def __init__(self, fp):
        self.bus = None
        # fp is now expected to be an instance of FileProgress_widget
        self.fp = fp

    def open_can(self, interface, channel, bitrate):
        if(self.bus != None): self.close_can()
        self.fp.log(f"Open CAN {interface} {channel} @ {bitrate//1000:d} kbit/s")
        self.bus = can.Bus(
            interface = interface,
            channel = channel,
            can_filters = [{
                "extended": False,
                "can_id": 0x7A0,
                "can_mask": 0x7FF
            }],
            bitrate = bitrate
        )
        # Workaround for socketcan interface.
        # The kernel filtering does not filter out the error messages.
        # So force library filtering.
        self.bus._is_filtered = False

    def close_can(self):
        if(self.bus == None): return
        self.fp.log("Close CAN")
        self.bus.shutdown()
        self.bus = None

    def read_memory(self, address, size):
        if   (size == 4):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x50,
                data = address.to_bytes(4, BO_BE)
            )
            self.bus.send(msg)
            msg = self.bus.recv(timeout=1.0)
            if(msg == None): raise ECUException("ECU Read Word failed!")
            if(msg.dlc != 4): raise ECUException("Unexpected answer!")
            data = msg.data
        elif(size == 2):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x51,
                data = address.to_bytes(4, BO_BE)
            )
            self.bus.send(msg)
            msg = self.bus.recv(timeout=1.0)
            if(msg == None): raise ECUException("ECU Read Half failed!")
            if(msg.dlc != 2): raise ECUException("Unexpected answer!")
            data = msg.data
        elif(size == 1):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x52,
                data = address.to_bytes(4, BO_BE)
            )
            self.bus.send(msg)
            msg = self.bus.recv(timeout=1.0)
            if(msg == None): raise ECUException("ECU Read Byte failed!")
            if(msg.dlc != 1): raise ECUException("Unexpected answer!")
            data = msg.data
        elif(size < 256):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x53,
                data = address.to_bytes(4, BO_BE) + size.to_bytes(1, BO_BE)
            )
            self.bus.send(msg)
            data = bytearray()
            while(size > 0):
                chunk_size = min(8, size);
                msg = self.bus.recv(timeout=1.0)
                if(msg == None): raise ECUException("ECU Read Buffer failed!")
                if(msg.dlc != chunk_size): raise ECUException("Unexpected answer!")
                data += msg.data
                size -= chunk_size
        else:
            raise ECUException("ECU Read too many bytes!")
        return data

    def write_memory(self, address, data, verify = False):
        size = len(data)
        if   (size == 4):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x54,
                data = address.to_bytes(4, BO_BE) + data
            )
            self.bus.send(msg)
        elif(size == 2):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x55,
                data = address.to_bytes(4, BO_BE) + data
            )
            self.bus.send(msg)
        elif(size == 1):
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x56,
                data = address.to_bytes(4, BO_BE) + data
            )
            self.bus.send(msg)
        elif(size < 256):
            offset = 0
            msg = can.Message(
                is_extended_id = False, arbitration_id = 0x57,
                data = address.to_bytes(4, BO_BE) + size.to_bytes(1, BO_BE)
            )
            self.bus.send(msg)
            while(size > 0):
                chunk_size = min(8, size)
                msg = can.Message(
                    is_extended_id = False, arbitration_id = 0x57,
                    data = data[offset:offset+chunk_size]
                )
                self.bus.send(msg)
                size -= chunk_size
                offset += chunk_size
        else:
            raise ECUException("ECU Write too many bytes!")
        if(verify and data != self.read_memory(address, len(data))):
            raise ECUException("ECU Write failed!")

    def download_verify(self, address, size, filename):
        self.fp.download(address, size, filename, self.read_memory, 128)
        self.fp.verify(address, filename, self.read_memory, 128)

    def upload_verify(self, address, filename):
        self.fp.upload(address, filename, self.write_memory, 128, chunk_pause=0.01)
        self.fp.verify(address, filename, self.read_memory, 128)