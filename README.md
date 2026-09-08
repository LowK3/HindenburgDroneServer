# Hindenburg - Onboard System Server

Raspberry Pi-based onboard server for the **Hindenburg underwater ROV**. Handles control commands, telemetry, sensor data, and thruster control through a hardware abstraction layer using `pigpio`.

                  HINDENBURG ROV
                       │
             ┌─────────┴─────────┐
             │                   │
       Raspberry Pi 4B      Sensors / ESCs
             │
       Onboard Server
             │
        TCP / UDP
             │
             ▼
      Ground Control Station
             │
       Keyboard / Gamepad
       
## Hardware Requirements

* Raspberry Pi 4B running Raspberry Pi OS
* 4× ESC-controlled thrusters
* MPU-6500 IMU (optional)
* BME280 environmental sensor (optional)
* Direct Ethernet connection to the Ground Control Station

## Software Requirements

* Python 3
* `pigpio`
* `dnsmasq`
* I2C support - (required when using the optional sensors)

The required Python packages are listed in `requirements.txt`.

## Setup

### 1. Configure the Network

The included script configures the Raspberry Pi for direct Ethernet communication with the Ground Control Station.

```bash
chmod +x Scripts/setup_dhcp.sh
sudo ./Scripts/setup_dhcp.sh
```

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install pigpio python3-pip python3-venv python3-smbus dnsmasq
```

### 3. Create the Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Manual Execution

### 1. Start the `pigpio` daemon

```bash
sudo systemctl start pigpiod
```

### 2. Activate the virtual environment

```bash
source venv/bin/activate
```

### 3. Start the server

```bash
python main_server.py
```

## Related Repository

The drone ground control station software is maintained separately:
- [HindenburgDroneClient](https://github.com/LowK3/HindenburgDroneClient)
