# pyinstaller --onefile --icon=tsui.ico --hidden-import=requests tsui.py

import os
import sys
import json
import requests
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox



### Methods ###

def browse_file():
    file_path = filedialog.asksaveasfilename(
        title="Select output file",
        defaultextension=".kml",
        filetypes=[("All Files", "*.*"), ("JSON Files", "*.json"), ("KML Files", "*.kml")]
    )
    if file_path:
        output_path.set(file_path)

def dms_to_dec(direction, deg, minutes, seconds):
    dec = float(deg) + float(minutes)/60 + float(seconds)/3600
    if direction.upper() in ['S', 'W']:
        dec = -dec
    return dec



### Run script ###

def run():
    #Ensure valid entries
    try:
        max_erp_value = float(max_erp.get())
    except ValueError:
        messagebox.showerror("Invalid input", "Maximum ERP must be a number.")
        return
    try:
        min_height_value = float(min_height.get())
    except ValueError:
        messagebox.showerror("Invalid input", "Minimum height must be a number.")
        return

    MODE = tower_type_combo.get()
    STATE = state_combo.get().split()[0].replace("All", "")
    MAX_ERP = float(max_erp.get())
    MIN_HAAT = float(min_height.get())
    OUTPUT_MODE = output_mode_combo.get()
    OUTPUT_FILE = output_path.get()
    OPEN_GOOGLE_EARTH = open_ge.get()
    
    print("Running towersort...")
    print(f"Settings:\n MODE:{MODE}\n STATE:{STATE}\n MAX_ERP:{MAX_ERP}\n MIN_HAAT:{MIN_HAAT}\n OUTPUT_MODE:{OUTPUT_MODE}\n OUTPUT_FILE:{OUTPUT_FILE}")
    
    url = ""
    BASE_PARAMS = {
        "call": "",
        "filenumber": "",
        "state": STATE,
        "city": "",
        "list": "4",
        "ThisTab": "Results to This Page/Tab",
        "dist": "",
        "dlat2": "",
        "mlat2": "",
        "slat2": "",
        "NS": "N",
        "dlon2": "",
        "mlon2": "",
        "slon2": "",
        "EW": "W",
        "size": "9",
        "facid": "",
        "class": ""
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Priority": "u=0, i",
        "Referer": "https://transition.fcc.gov/fcc-bin/fmq?x"
    }

    if MODE == "FM":
        url = "https://transition.fcc.gov/fcc-bin/fmq"
        params = BASE_PARAMS.copy()
        params.update({
            "freq": "88.1",
            "fre2": "107.9",
            "serv": "",
            "status": "",
            "asrn": ""
        })
    elif MODE == "AM":
        url = "https://transition.fcc.gov/fcc-bin/fmq"
        params = BASE_PARAMS.copy()
        params.update({
            "freq": "530",
            "fre2": "1700",
            "type": 0,
            "hours": ""
        })
    else:
        url = "https://transition.fcc.gov/fcc-bin/tvq"
        params = BASE_PARAMS.copy()
        params.update({
            "chan": "0",
            "cha2": "36",
            "serv": "",
            "status": "",
            "asrn": ""
        })
    
    response = requests.get(url, headers=headers, params=params, cookies={}, allow_redirects=True)
    data = response.text
    
    if ("|" not in data):
        messagebox.showerror("Error", "Failed to retreive station list.")
    
    lines = [line.strip() for line in data.strip().splitlines()]
    json_list = []
    count = 0
    for line in lines:
        parts = line.split("|")
        parts.pop(0)
        
        if (MODE == "FM"):
            #ERP
            def parse_erp(field):
                try:
                    parts = field.strip().split()
                    return float(parts[0]), parts[1]
                except:
                    return None, None

            erp, erp_unit = 0, "kW"

            erp1, erp1_unit = parse_erp(parts[13])
            erp2, erp2_unit = parse_erp(parts[14])

            if erp1 is not None and erp2 is not None:
                if erp1 > erp2:
                    erp, erp_unit = erp1, erp1_unit
                else:
                    erp, erp_unit = erp2, erp2_unit
            elif erp1 is not None:
                erp, erp_unit = erp1, erp1_unit
            elif erp2 is not None:
                erp, erp_unit = erp2, erp2_unit
            else:
                print(f"Skipping {parts[0].strip()} due to invalid ERP")
            
            #HAAT
            def parse_haat(field):
                try:
                    return float(field.strip())
                except:
                    return None
            
            haat = 0
            
            haat1 = parse_haat(parts[15])
            haat2 = parse_haat(parts[16])
            
            if haat1 is not None and haat2 is not None:
                if haat1 > haat2:
                    haat = haat1
                else:
                    haat = haat2
            elif haat1 is not None:
                haat = haat1
            elif haat2 is not None:
                haat = haat2
            else:
                print(f"Skipping {parts[0].strip()} due to invalid height")
            
            #Filters
            if (erp > MAX_ERP or haat < MIN_HAAT):
                continue

            record = {
                "call_sign": parts[0].strip(),
                "frequency": float(parts[1].strip().split()[0].strip()),
                "frequency_unit": parts[1].strip().split()[1].strip(),
                "service": parts[2].strip(),
                "channel": parts[3].strip(),
                "directional": parts[4].strip(),
                "digital": parts[5].strip(),
                "city": parts[9].strip(),
                "state": parts[10].strip(),
                "country": parts[11].strip(),
                "erp": erp,
                "erp_unit": erp_unit,
                "haat": haat,
                "haat_unit": "m",
                "fcc_facility_id": int(parts[17].strip()),
                "location": str(dms_to_dec(parts[18].strip(), float(parts[19]), float(parts[20]), float(parts[21]))) + " " + str(dms_to_dec(parts[22].strip(), float(parts[23]), float(parts[24]), float(parts[25]))),
                "licensee": " ".join(parts[26:])
            }
                    
            json_list.append(record)
            count += 1
            
        elif (MODE == "AM"):
            #ERP
            erp, erp_unit = 0, "kW"
            try:
                erp = float(parts[13].strip().split()[0])
                erp_unit = parts[13].strip().split()[1]
            except:
                print(f"Skipping {parts[0].strip()} due to invalid ERP")
            
            #Filters
            if (erp > MAX_ERP):
                continue

            record = {
                "call_sign": parts[0].strip(),
                "frequency": float(parts[1].strip().split()[0].strip()),
                "frequency_unit": parts[1].strip().split()[1].strip(),
                "service": parts[2].strip(),
                "hours": parts[5].strip(),
                "directional": parts[14].strip(),
                "digital": parts[15].strip(),
                "city": parts[9].strip(),
                "state": parts[10].strip(),
                "country": parts[11].strip(),
                "erp": erp,
                "erp_unit": erp_unit,
                "fcc_facility_id": int(parts[17].strip()),
                "location": str(dms_to_dec(parts[18].strip(), float(parts[19]), float(parts[20]), float(parts[21]))) + " " + str(dms_to_dec(parts[22].strip(), float(parts[23]), float(parts[24]), float(parts[25]))),
                "licensee": " ".join(parts[26:])
            }
                    
            json_list.append(record)
            count += 1
        
        elif (MODE == "TV"):
            #ERP
            erp, erp_unit = 0, "kW"
            try:
                erp = float(parts[13].strip().split()[0])
                erp_unit = parts[13].strip().split()[1]
            except:
                print(f"Skipping {parts[0].strip()} due to invalid ERP")
            
            #HAAT
            haat = 0
            try:
                haat = float(parts[15].strip())
            except:
                print(f"Skipping {parts[0].strip()} due to invalid height")
            
            #Filters
            if (erp > MAX_ERP or haat < MIN_HAAT):
                continue

            record = {
                "call_sign": parts[0].strip(),
                "service": parts[2].strip(),
                "channel": parts[3].strip(),
                "atsc3_nextgen_tv": parts[5].strip(),
                "city": parts[9].strip(),
                "state": parts[10].strip(),
                "country": parts[11].strip(),
                "erp": erp,
                "erp_unit": erp_unit,
                "haat": haat,
                "haat_unit": "m",
                "fcc_facility_id": int(parts[17].strip()),
                "location": str(dms_to_dec(parts[18].strip(), float(parts[19]), float(parts[20]), float(parts[21]))) + " " + str(dms_to_dec(parts[22].strip(), float(parts[23]), float(parts[24]), float(parts[25]))),
                "licensee": " ".join(parts[26:])
            }
                    
            json_list.append(record)
            count += 1
        
    if (MODE != "AM"):
        json_list.sort(key=lambda x: x["haat"], reverse=True)
    json_output = json.dumps(json_list, indent=4)

    print(f"Done sorting with {count} stations")
    
    try:
        if (OUTPUT_MODE == "JSON"):
            print(f"Saving output JSON to {OUTPUT_FILE}...")
            f = open(OUTPUT_FILE, "w")
            f.write(json_output)
            f.close()
            print(f"Saved output JSON to {OUTPUT_FILE}")
            messagebox.showinfo("Success", f"Saved output JSON to '{OUTPUT_FILE}'!")
        else:
            print("Generating KML...")
            
            if (MODE == "FM"):
                kml_header = """<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
            """
                kml_footer = """</Document></kml>"""
                
                placemarks = []
                for station in json_list:
                    lat, lon = map(float, station['location'].split())
                    name = f"(FM) {station['call_sign']}: {station['haat']}{station['haat_unit']}, {station['erp']}{station['erp_unit']}"
                    description = f"<br>Service: {station['service']}<br><br><b>Height: {station['haat']}{station['haat_unit']}</b><br><b>ERP: {station['erp']}{station['erp_unit']}</b><br><br>Directional: {station['directional']}<br>Digital: {station['digital']}<br><br>Frequency: {station['frequency']}{station['frequency_unit']}<br>Channel: {station['channel']}<br><br>Location: {station['city']}, {station['state']} ({station['location']})<br>FCC Facility ID: {station['fcc_facility_id']}<br>Licensee: {station['licensee']}"
                    placemark = f"""
      <Placemark>
        <name>{name}</name>
        <description><![CDATA[{description}]]></description>
        <Point>
          <coordinates>{lon},{lat},0</coordinates>
        </Point>
      </Placemark>
    """
                    placemarks.append(placemark)
            
            elif (MODE == "AM"):
                kml_header = """<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
            """
                kml_footer = """</Document></kml>"""
                
                placemarks = []
                for station in json_list:
                    lat, lon = map(float, station['location'].split())
                    name = f"(AM) {station['call_sign']}: {station['erp']}{station['erp_unit']}"
                    description = f"<br>Service: {station['service']}<br><br><b>ERP: {station['erp']}{station['erp_unit']}</b><br><b>Hours: {station['hours']}</b><br><br>Directional: {station['directional']}<br>Digital: {station['digital']}<br><br>Frequency: {station['frequency']}{station['frequency_unit']}<br><br>Location: {station['city']}, {station['state']} ({station['location']})<br>FCC Facility ID: {station['fcc_facility_id']}<br>Licensee: {station['licensee']}"
                    placemark = f"""
      <Placemark>
        <name>{name}</name>
        <description><![CDATA[{description}]]></description>
        <Point>
          <coordinates>{lon},{lat},0</coordinates>
        </Point>
      </Placemark>
    """
                    placemarks.append(placemark)
                
            elif (MODE == "TV"):
                kml_header = """<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
            """
                kml_footer = """</Document></kml>"""
                
                placemarks = []
                for station in json_list:
                    lat, lon = map(float, station['location'].split())
                    name = f"(TV) {station['call_sign']}: {station['haat']}{station['haat_unit']}, {station['erp']}{station['erp_unit']}"
                    description = f"<br>Service: {station['service']}<br><br><b>Height: {station['haat']}{station['haat_unit']}</b><br><b>ERP: {station['erp']}{station['erp_unit']}</b><br><br>Channel: {station['channel']}<br>ATSC 3 (Nextgen TV): {station['atsc3_nextgen_tv']}<br><br>Location: {station['city']}, {station['state']} ({station['location']})<br>FCC Facility ID: {station['fcc_facility_id']}<br>Licensee: {station['licensee']}"
                    placemark = f"""
      <Placemark>
        <name>{name}</name>
        <description><![CDATA[{description}]]></description>
        <Point>
          <coordinates>{lon},{lat},0</coordinates>
        </Point>
      </Placemark>
    """
                    placemarks.append(placemark)
            
            print("Generated KML")
            print(f"Saving output KML to {OUTPUT_FILE}...")
            f = open(OUTPUT_FILE, "w")
            f.write(kml_header + "".join(placemarks) + kml_footer)
            f.close()
            print(f"Saved output KML to {OUTPUT_FILE}")
            messagebox.showinfo("Success", f"Saved output KML to '{OUTPUT_FILE}'!")
    except:
        messagebox.showerror("Invalid input", f"Invalid output file path, could not save output! Given path: {OUTPUT_FILE}\nMake sure to select an output file location!")
        return
    
    if (OPEN_GOOGLE_EARTH and OUTPUT_MODE != "JSON"):
        print(f"Attempting to open Google Earth with f{OUTPUT_FILE}...")
        
        # Windows
        if sys.platform.startswith("win"):
            ge_path = r"C:\Program Files\Google\Google Earth Pro\client\googleearth.exe"
            print(f"Windows system detected, using path {ge_path}")
            subprocess.run([ge_path, OUTPUT_FILE])
            print("Attempted to open Google Earth")

        # Mac
        elif sys.platform.startswith("darwin"):
            print("MacOS system detected")
            subprocess.run(["open", "-a", "Google Earth Pro", OUTPUT_FILE])
            print("Attempted to open Google Earth")

        # Linux
        else:
            print("Linux system detected")
            subprocess.run(["google-earth-pro", OUTPUT_FILE])
            print("Attempted to open Google Earth")



### UI ###

root = tk.Tk()
root.title("TSUI - Tower Sort UI")

PADX = 5
PADY = 5

# Tower type
tk.Label(root, text="Tower type:").grid(row=0, column=0, sticky="e", padx=PADX, pady=PADY)
tower_type_combo = ttk.Combobox(root, values=["AM", "FM", "TV"], state="readonly")
tower_type_combo.current(1)
tower_type_combo.grid(row=0, column=1, sticky="w", padx=PADX, pady=PADY)

# State
tk.Label(root, text="State:").grid(row=1, column=0, sticky="e", padx=PADX, pady=PADY)
state_options = ["All States", "AK - Alaska", "AL - Alabama", "AR - Arkansas", "AS - American Samoa",
                 "AZ - Arizona", "CA - California", "CO - Colorado", "CT - Connecticut", "DC - District of Columbia",
                 "DE - Delaware", "FL - Florida", "GA - Georgia", "GU - Guam", "HI - Hawaii", "IA - Iowa",
                 "ID - Idaho", "IL - Illinois", "IN - Indiana", "KS - Kansas", "KY - Kentucky", "LA - Louisiana",
                 "MA - Massachusetts", "MD - Maryland", "ME - Maine", "MI - Michigan", "MN - Minnesota",
                 "MO - Missouri", "MP - Mariana Islands", "MS - Mississippi", "MT - Montana", "NC - North Carolina",
                 "ND - North Dakota", "NE - Nebraska", "NH - New Hampshire", "NJ - New Jersey", "NM - New Mexico",
                 "NV - Nevada", "NY - New York", "OH - Ohio", "OK - Oklahoma", "OR - Oregon", "PA - Pennsylvania",
                 "PR - Puerto Rico", "RI - Rhode Island", "SC - South Carolina", "SD - South Dakota", "TN - Tennessee",
                 "TX - Texas", "UT - Utah", "VA - Virginia", "VI - Virgin Islands (U.S.)", "VT - Vermont",
                 "WA - Washington", "WI - Wisconsin", "WV - West Virginia", "WY - Wyoming"]
state_combo = ttk.Combobox(root, values=state_options, state="readonly")
state_combo.current(0)
state_combo.grid(row=1, column=1, sticky="w", padx=PADX, pady=PADY)

# Maximum ERP
tk.Label(root, text="Maximum ERP:").grid(row=2, column=0, sticky="e", padx=PADX, pady=PADY)
frame_erp = tk.Frame(root)
frame_erp.grid(row=2, column=1, sticky="w", padx=PADX, pady=PADY)
max_erp = tk.Entry(frame_erp, width=10)
max_erp.pack(side=tk.LEFT)
max_erp.insert(0, "50")
tk.Label(frame_erp, text="kW").pack(side=tk.LEFT, padx=5)  # unit label

# Minimum height
tk.Label(root, text="Minimum height:").grid(row=3, column=0, sticky="e", padx=PADX, pady=PADY)
frame_height = tk.Frame(root)
frame_height.grid(row=3, column=1, sticky="w", padx=PADX, pady=PADY)
min_height = tk.Entry(frame_height, width=10)
min_height.pack(side=tk.LEFT)
min_height.insert(0, "50")
tk.Label(frame_height, text="m").pack(side=tk.LEFT, padx=5)  # unit label

# Output mode
tk.Label(root, text="Output mode:").grid(row=4, column=0, sticky="e", padx=PADX, pady=PADY)
output_mode_combo = ttk.Combobox(root, values=["JSON", "KML (Google Earth)"], state="readonly")
output_mode_combo.current(1)
output_mode_combo.grid(row=4, column=1, sticky="w", padx=PADX, pady=PADY)

# Output file location
tk.Label(root, text="Output file location:").grid(row=5, column=0, sticky="e", padx=PADX, pady=PADY)
output_path = tk.StringVar()
file_frame = tk.Frame(root)
file_frame.grid(row=5, column=1, sticky="w", padx=PADX, pady=PADY)
tk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.LEFT)
tk.Label(file_frame, textvariable=output_path).pack(side=tk.LEFT, padx=10)

# Open Google Earth
open_ge = tk.BooleanVar()
open_ge_check = tk.Checkbutton(root, text="Open Google Earth (Only if KML output mode is selected)", variable=open_ge)
open_ge_check.grid(row=6, column=1, sticky="w", padx=PADX, pady=PADY)

# Run button
tk.Button(root, text="Run", command=run, width=20).grid(row=7, column=0, columnspan=2, pady=PADY)

root.mainloop()
