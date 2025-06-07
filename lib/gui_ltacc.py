import os, re
import tkinter as tk
import builtins
from tkinter import ttk, filedialog, simpledialog
from lib.ltacc import LiveTuningAccess
from lib.gui_common import SelectCAN_widget, try_msgbox_decorator, bin_file
from lib.gui_fileprogress import FileProgress_widget
from lib.gui_tkmaptable import MapTableEditor, SimpleGauge
import csv

# Some constants for calculated values
BO_BE = 'big'
LSB_WEIGHT_FOR_RAW_MAF_TO_MG_STROKE = 0.25
NUMBER_OF_CYLINDERS = 6
CONVERSION_DIVISOR_FOR_GS = 120000.0

CHARSET = 'ISO-8859-15'

class LiveTuningAccess_win(tk.Toplevel):
    def __init__(self, config, parent=None, tuner_script_dir=None):
        tk.Toplevel.__init__(self, parent)
        self.title('Live-Tuning Access')
        self.resizable(0, 0)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.run_task = False
        self.config = config
        self.tuner_script_dir = tuner_script_dir

        self.can_device = SelectCAN_widget(config, self)
        self.can_device.pack(fill=tk.X)

        lta_frame = tk.LabelFrame(self, text="Dump")
        lta_frame.pack(fill=tk.X)

        self.fp = FileProgress_widget(lta_frame)

        btn_frame = tk.Frame(lta_frame)
        btn_frame.pack(fill=tk.X)

        self.button_tune = tk.Button(lta_frame, text="Tuner (T6E, P calibration)", command=self.tuner)
        self.button_tune.pack(fill=tk.X)

    def lock_buttons_decorator(func):
        def wrapper(self):
            self.button_tune['state'] = tk.DISABLED
            func(self)
            self.button_tune['state'] = tk.NORMAL
        return wrapper

    def lta_decorator(func):
        def wrapper(self):
            lta = LiveTuningAccess(self.fp)

            lta.open_can(
                self.can_device.get_interface(),
                self.can_device.get_channel(),
                self.can_device.get_bitrate(),
            )
            try:
                func(self, lta)
            finally:
                lta.close_can()
        return wrapper

    def on_closing(self):
        self.destroy()

    @lock_buttons_decorator
    @try_msgbox_decorator
    @lta_decorator
    def tuner(self, lta):
        sym = SYMMap("patch/t6eP138.sym") # Path to live tuner definition
        if(lta.read_memory(sym.get_sym_addr("cal_base"), 4) != b"P138"): # Checks vehicle FW version before allowing access to tuner
            raise Exception("Unsupported ECU! Contact me!")
        speed = 0
        load = 0
        tunable = ({
            'xname': "rpm", # Axis name
            'read_xdata': lambda: [
                int(v)*125//4+500 for v in lta.read_memory( # Axis scaling
                    sym.get_sym_addr("cal_Fuel_VolumetricEfficiencyBase_X_RPM"), 32 # Axis address identifier (named in definition file), number of cells in axis
                )
            ], 
            'get_xvalue': lambda: speed,
            'yname': "load",
            'read_ydata': lambda: [
                int(v)*4 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Fuel_VolumetricEfficiencyBase_Y_Load"), 32 # For Y axis
                )
            ],
            'get_yvalue': lambda: load,
            'name': "Efficiency",
            'read_data': lambda: [
                [int(v)/2 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Fuel_VolumetricEfficiencyBase")+(i*32), 32 # For display of data
                )] for i in range(0,32)
            ],
            'datafmt': "{:.1f}",
            'step': 0.5,
            'write_cell': lambda x,y,value:lta.write_memory(
                sym.get_sym_addr("cal_Fuel_VolumetricEfficiencyBase")+(y*32)+x, # As above for writing back to SRAM. REVERSE EQUATION MUST BE ACCURATE
                int(value*2).to_bytes(1, BO_BE)
            ),
            'xfmt': "{:.0f}",
            'yfmt': "{:.0f}" 
        },{
            'xname': "rpm",
            'read_xdata': lambda: [
                int(v)*125//4+500 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Load_AirmassTargetInitial_X_RPM"), 16
                )
            ],
            'get_xvalue': lambda: speed,
            'yname': "throttle",
            'read_ydata': lambda: [
                int(v)*4 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Load_AirmassTargetInitial_Y_Load"), 16
                )
            ],
            'get_yvalue': lambda: load,
            'name': "Airmass",
            'read_data': lambda: [
                [int(v)*4 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Load_AirmassTargetInitial")+(i*16), 16
                )] for i in range(0,16)
            ],
            'datafmt': "{:.1f}",
            'step': 0.5,
            'write_cell': lambda x,y,value:lta.write_memory(
                sym.get_sym_addr("cal_Load_AirmassTargetInitial")+(y*16)+x,
                int(value/4).to_bytes(1, BO_BE)
            ),
            'xfmt': "{:.0f}", 
            'yfmt': "{:.0f}" 
        },{
            'xname': "rpm",
            'read_xdata': lambda: [
                int(v)*125//4+500 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Ignition_TimingBaseSafetyManual_X_RPM"), 20
                )
            ], 
            'get_xvalue': lambda: speed,
            'yname': "load",
            'read_ydata': lambda: [
                int(v)*4 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Ignition_TimingBaseSafetyManual_Y_Load"), 20
                )
            ],
            'get_yvalue': lambda: load,
            'name': "Ignition Safety",
            'read_data': lambda: [
                [int(v)/4-10 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Ignition_TimingBaseSafetyManual")+(i*20), 20
                )] for i in range(0,20)
            ],
            'datafmt': "{:.1f}",
            'step': 0.25,
            'write_cell': lambda x,y,value:lta.write_memory(
                sym.get_sym_addr("cal_Ignition_TimingBaseSafetyManual")+(y*20)+x,
                int((value+10)*4).to_bytes(1, BO_BE)
            ),
            'xfmt': "{:.0f}",
            'yfmt': "{:.0f}" 
        },{
            'xname': "rpm",
            'read_xdata': lambda: [
                int(v)*125//4+500 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Ignition_TimingBaseMainManual_X_RPM"), 20
                )
            ], 
            'get_xvalue': lambda: speed,
            'yname': "load",
            'read_ydata': lambda: [
                int(v)*4 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Ignition_TimingBaseMainManual_Y_Load"), 20
                )
            ],
            'get_yvalue': lambda: load,
            'name': "Ignition Main",
            'read_data': lambda: [
                [int(v)/4-10 for v in lta.read_memory(
                    sym.get_sym_addr("cal_Ignition_TimingBaseMainManual")+(i*20), 20
                )] for i in range(0,20)
            ],
            'datafmt': "{:.1f}",
            'step': 0.25,
            'write_cell': lambda x,y,value:lta.write_memory(
                sym.get_sym_addr("cal_Ignition_TimingBaseMainManual")+(y*20)+x,
                int((value+10)*4).to_bytes(1, BO_BE)
            ),
            'xfmt': "{:.0f}",
            'yfmt': "{:.0f}" 
        })
        gauges = ({
            'name': "Engine Speed",
            'fmt': "{:.0f} rpm",
            'low': 0,
            'high': 7500,
            'read_data': lambda: speed
        },{
            'name': "Engine Load",
            'fmt': "{:.0f} mg/str.",
            'low': 60,
            'high': 864,
            'read_data': lambda: load
        },{
            'name': "Coolant",
            'fmt': "{:.1f} °C",
            'low': 20,
            'high': 110,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("coolant"), 1), BO_BE)*5/8-40
        },{
            'name': "Intake Air",
            'fmt': "{:.1f} °C",
            'low': 20,
            'high': 70,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("air"), 1), BO_BE)*5/8-40
        },{
            'name': "MAF", # MAF is calculated live based on RPM
            'fmt': "{:.1f} g/s",
            'low': 0,
            'high': 300,
            'read_data': lambda: (
                (
                    int.from_bytes(lta.read_memory(sym.get_sym_addr("MAF"), 2), BO_BE)
                    * LSB_WEIGHT_FOR_RAW_MAF_TO_MG_STROKE
                )
                * speed # Current RPM
                * NUMBER_OF_CYLINDERS
            ) / CONVERSION_DIVISOR_FOR_GS
        },{
            'name': "TPS",
            'fmt': "{:.1f} %",
            'low': 0,
            'high': 100,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("TPS"), 2), BO_BE)*100/1023
        },{
            'name': "Pedal",
            'fmt': "{:.1f} %",
            'low': 0,
            'high': 100,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("PPS"), 2), BO_BE)*100/1023
        },{
            'name': "Tip In",
            'fmt': "{:.1f} us",
            'low': 0,
            'high': 900,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("tipin"), 1), BO_BE)/255
        },{
            'name': "Pulse Width Bank 1",
            'fmt': "{:d} us",
            'low': 0,
            'high': 15000,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("pulsewidth_b1"), 2), BO_BE)
        },{
            'name': "Pulse Width Bank 2",
            'fmt': "{:d} us",
            'low': 0,
            'high': 15000,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("pulsewidth_b2"), 2), BO_BE)
        },{
            'name': "STFT Bank 1",
            'fmt': "{:.1f} %",
            'low': -10,
            'high': 10,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("stft_b1"), 2), BO_BE, signed=True)/20
        },{
            'name': "STFT Bank 2",
            'fmt': "{:.1f} %",
            'low': -10,
            'high': 10,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("stft_b2"), 2), BO_BE, signed=True)/20
        },{
            'name': "LTFT Bank 1",
            'fmt': "{:.1f} %",
            'low': -10,
            'high': 10,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("ltft_b1"), 2), BO_BE, signed=True)/20
        },{
            'name': "LTFT Bank 2",
            'fmt': "{:.1f} %",
            'low': -10,
            'high': 10,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("ltft_b2"), 2), BO_BE, signed=True)/20
        },{
            'name': "Target AFR",
            'fmt': "{:.2f} AFR",
            'low': 10,
            'high': 20,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("afr_target"), 2), BO_BE)/100
        },{
            'name': "Gear",
            'fmt': "{:d} #",
            'low': 0,
            'high': 6,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("gear"), 2), BO_BE)
        },{
            'name': "Ign 1",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: 387.5 - int.from_bytes(lta.read_memory(sym.get_sym_addr("ign_1"), 2), 'big', signed=True) / 4.0
        },{
            'name': "Ign 2",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: 687.5 - int.from_bytes(lta.read_memory(sym.get_sym_addr("ign_2"), 2), BO_BE, signed=True) / 4.0
        },{
            'name': "Ign 3",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: 987.5 - int.from_bytes(lta.read_memory(sym.get_sym_addr("ign_3"), 2), 'big', signed=True) / 4.0
        },{
            'name': "Ign 4",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: 1287.5 - int.from_bytes(lta.read_memory(sym.get_sym_addr("ign_4"), 2), 'big', signed=True) / 4.0
        },{
            'name': "Ign 5",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: 1587.5 - int.from_bytes(lta.read_memory(sym.get_sym_addr("ign_5"), 2), 'big', signed=True) / 4.0
        },{
            'name': "Ign 6",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: 87.5 - int.from_bytes(lta.read_memory(sym.get_sym_addr("ign_6"), 2), 'big', signed=True) / 4.0
        },{
            'name': "KR 1",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("kr_1"), 1), BO_BE, signed=True)/4
        },{
            'name': "KR 2",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("kr_2"), 1), BO_BE, signed=True)/4
        },{
            'name': "KR 3",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("kr_3"), 1), BO_BE, signed=True)/4
        },{
            'name': "KR 4",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("kr_4"), 1), BO_BE, signed=True)/4
        },{
            'name': "KR 5",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("kr_5"), 1), BO_BE, signed=True)/4
        },{
            'name': "KR 6",
            'fmt': "{:.2f} °",
            'low': -10,
            'high': 50,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("kr_6"), 1), BO_BE, signed=True)/4
        },{
            'name': "Battery Voltage",
            'fmt': "{:.2f} v",
            'low': 8,
            'high': 18,
            'read_data': lambda: int.from_bytes(lta.read_memory(sym.get_sym_addr("vbat"), 1), BO_BE)*7/64
        })
        tw = TunerWin(
            self.config, tunable, gauges,
            lambda: lta.write_memory(sym.get_sym_addr("rt_PerCylinder_AdaptiveTimingTrim"), b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            lambda f: lta.upload_verify(sym.get_sym_addr("cal_base"), f),
            lambda f: lta.download_verify(sym.get_sym_addr("cal_base"), 0x3CB4, f),
            self.fp, 
            self, 
            self.tuner_script_dir
        )
        while(tw.is_running):
            # Cache speed and load here - There are used mutiple times!
            speed = int.from_bytes(lta.read_memory(sym.get_sym_addr("engine_speed"), 2), BO_BE)/4
            load = int.from_bytes(lta.read_memory(sym.get_sym_addr("engine_load"), 2), BO_BE)
            tw.update()
            if(tw.force_ft0.get()):
                lta.write_memory(sym.get_sym_addr("fueladaptB1A"), b'\x00\x00\x00\x00\x00\x00\x00\x00')
                lta.write_memory(sym.get_sym_addr("fueladaptB1B"), b'\x00\x00\x00\x00\x00\x00\x00\x00')
                lta.write_memory(sym.get_sym_addr("fueladaptB2A"), b'\x00\x00\x00\x00\x00\x00\x00\x00')
                lta.write_memory(sym.get_sym_addr("fueladaptB2B"), b'\x00\x00\x00\x00\x00\x00\x00\x00')
                lta.write_memory(sym.get_sym_addr("stft_integratorB1"), b'\x00\x00')
                lta.write_memory(sym.get_sym_addr("stft_integratorB2"), b'\x00\x00')
            if(tw.force_dt0.get()):
                lta.write_memory(sym.get_sym_addr("LEA_ltft_idle_adj"), b'')
            self.update()

class SYMMap:
    def __init__(self, file):
        self.syms = {}
        r = re.compile("^(.*) = (0x[0-9a-f]*);")
        with open(file,'r') as f:
            for line in f.readlines():
                m = r.match(line)
                if(m): self.syms[m.group(1)] = int(m.group(2), 16)

    def get_sym_addr(self, symbol):
        return self.syms[symbol]

class TunerWin(tk.Toplevel):
    def __init__(self, config, tunable, gauges, zeroscaler, impfn, expfn, fp_widget, parent=None, tuner_script_dir=None):
        tk.Toplevel.__init__(self, parent)
        self.title('Tuner')
        self.resizable(0, 0)
        self.grab_set()
        self.bind('<KeyPress>', self.onKeyPress)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.is_running = True
        self.config = config
        self.fp_widget = fp_widget
        f_vertical = tk.Frame(self)
        f_vertical.pack(side=tk.LEFT)
        self.tabControl = ttk.Notebook(f_vertical)
        self.m = []
        for t in tunable:
            m = MapTableEditor(self.tabControl, **t)
            m.pack()
            self.m.append(m)
            self.tabControl.add(m, text=t['name'])
        self.tabControl.pack()

        # Actions
        f_action = tk.LabelFrame(f_vertical, highlightthickness=2, text="Actions")
        f_action.pack(fill=tk.X)
        self.force_ft0 = tk.IntVar()
        tk.Checkbutton(f_action, text='Zero STFT/LTFT',variable=self.force_ft0).pack(side=tk.LEFT)
        self.force_dt0 = tk.IntVar()
        tk.Checkbutton(f_action, text='Zero dead time',variable=self.force_dt0).pack(side=tk.LEFT)
        tk.Button(f_action, text="Zero Ign. Scaler", command=zeroscaler).pack(side=tk.LEFT)
        tk.Button(f_action, text="Import", command=self.impcal).pack(side=tk.LEFT)
        tk.Button(f_action, text="Export", command=self.expcal).pack(side=tk.LEFT)
        self.impfn = impfn
        self.expfn = expfn

        # LOGGING BUTTON AND VARIABLES
        self.is_logging_active = False
        self.log_file = None
        self.csv_writer = None
        self.log_directory = tuner_script_dir
        os.makedirs(self.log_directory, exist_ok=True)

        self.log_button = tk.Button(f_action, text="Log", command=self.toggle_logging)
        self.log_button.pack(side=tk.LEFT)
        self.default_button_color = self.log_button.cget('bg') # Store default button color

        # Live Variables
        f_live_container = tk.LabelFrame(self, highlightthickness=2, text="Live-Data")
        f_live_container.pack(side=tk.LEFT, fill=tk.Y, padx=(5,0), anchor='nw')

        self.l = [] 
        self.gauges_info = gauges

        num_gauges = len(gauges)
        gauges_in_first_column = (num_gauges + 1) // 2

        column1_frame = tk.Frame(f_live_container)
        column1_frame.pack(side=tk.LEFT, fill=tk.Y, anchor='nw', padx=2, pady=2)

        column2_frame = tk.Frame(f_live_container)
        column2_frame.pack(side=tk.LEFT, fill=tk.Y, anchor='nw', padx=2, pady=2)

        for i, g_props in builtins.enumerate(gauges):
            if i < gauges_in_first_column:
                parent_frame_for_gauge = column1_frame
            else:
                parent_frame_for_gauge = column2_frame

            gauge_widget = SimpleGauge(parent_frame_for_gauge, **g_props)
            gauge_widget.pack(fill=tk.X, expand=False, pady=1)
            self.l.append(gauge_widget)

    def _get_unique_log_filename(self, base_name="live_data"):
        """Generates a unique filename for the log CSV."""
        i = 1
        while True:
            filename = os.path.join(self.log_directory, f"{base_name}_{i:03d}.csv")
            if not os.path.exists(filename):
                return filename
            i += 1

    @try_msgbox_decorator
    def toggle_logging(self):
        """Toggles logging of gauge data to a CSV file."""
        if not self.is_logging_active:
            try:
                log_filename = self._get_unique_log_filename()
                self.log_file = open(log_filename, 'w', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.log_file)

                # Write header row
                header = [g['name'] for g in self.gauges_info]
                self.csv_writer.writerow(header)

                self.is_logging_active = True
                self.log_button.config(bg='green', text="Stop Log")
                self.title(f"Tuner - Logging to {os.path.basename(log_filename)}") 
                self.fp_widget.log(f"Started logging to {log_filename}")
            except Exception as e:
                self.log_button.config(bg=self.default_button_color, text="Log")
                self.is_logging_active = False
                self.fp_widget.log(f"Error starting log: {e}")
                raise 
        else:
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self.csv_writer = None
            self.is_logging_active = False
            self.log_button.config(bg=self.default_button_color, text="Log")
            self.title("Tuner") 
            self.fp_widget.log("Stopped logging.")

    def update(self):
        for m in self.m: m.update()
        for l in self.l: l.update()

        if self.is_logging_active and self.csv_writer:
            row_data = []
            for gauge_widget in self.l: 
                try:
                    row_data.append(gauge_widget.get_value()) 
                except Exception as e:
                    print(f"Error reading gauge data for logging: {gauge_widget.cget('text')}: {e}")
                    row_data.append(None)

            try:
                self.csv_writer.writerow(row_data)
            except Exception as e:
                self.fp_widget.log(f"Error writing to log file: {e}. Stopping logging.")
                self.toggle_logging()

    @try_msgbox_decorator
    def impcal(self):
        answer = filedialog.askopenfilename(
            parent = self,
            initialdir = self.config['PATH']['bin'],
            initialfile = "calrom-tuner.bin",
            title = "Please select a file:",
            filetypes = bin_file
        )
        if(answer):
            self.config['PATH']['bin'] = os.path.dirname(answer)
            self.impfn(answer)
            for m in self.m: m.reload()

    @try_msgbox_decorator
    def expcal(self):
        answer = filedialog.asksaveasfilename(
            parent = self,
            initialdir = self.config['PATH']['bin'],
            initialfile = "calrom-tuner.bin",
            title = "Please select a file:",
            filetypes = bin_file
        )
        if(answer):
            self.config['PATH']['bin'] = os.path.dirname(answer)
            self.expfn(answer)

    @try_msgbox_decorator
    def onKeyPress(self, event):
        i = self.tabControl.index('current')
        if  (event.char == 'q'): self.m[i].inc_cur()
        elif(event.char == 'a'): self.m[i].dec_cur()
        elif(event.char == '+'): self.m[i].inc_sel()
        elif(event.char == '-'): self.m[i].dec_sel()
        elif(event.char == 'e'): self.tabControl.select(0)
        elif(event.char == 'h'): self.tabControl.select(1)
        elif(event.char == 'l'): self.tabControl.select(2)
        else: return
        self.m[i].table.focus_set()

    def on_closing(self):
        if hasattr(self, 'can_device'):
            self.can_device.get_interface()
            self.can_device.get_channel()

        if hasattr(self, 'update_thread_task') and self.update_thread_task is not None:
            self.after_cancel(self.update_thread_task)
            self.update_thread_task = None

        if hasattr(self, 'is_logging_active') and self.is_logging_active and self.log_file:
            self.log_file.close()
            self.is_logging_active = False
            self.log_file = None
            self.csv_writer = None

        self.destroy()