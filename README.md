# Hindenburg - Onboard System Server

Raspberry Pi-based onboard server for the **Hindenburg underwater ROV**.

The server handles control commands, telemetry, sensor communication, and thruster control through a hardware abstraction layer using `pigpio`.

## Architecture

```text
                     GROUND CONTROL STATION
                              │
                       Ethernet cable
                         TCP / UDP
                              │
                              ▼
                 ┌────────────────────────┐
                 │     Raspberry Pi 4B    │
                 │                        │
                 │    Onboard Server      │
                 │                        │
                 │  ┌──────────────────┐  │
                 │  │ Network / Control│  │
                 │  └────────┬─────────┘  │
                 │           │            │
                 │     Hardware Layer     │
                 │           │            │
                 │     ┌─────┴─────┐      │
                 │     │           │      │
                 │    ESCs      Sensors   │
                 │     │           │      │
                 │ Thrusters   MPU-6500   │
                 │              BME280    │
                 └────────────────────────┘
```

The server runs directly on the ROV's Raspberry Pi and acts as the interface between the Ground Control Station and the physical hardware.

## Hardware Requirements

* Raspberry Pi 4B running Raspberry Pi OS
* 4× ESC-controlled thrusters
* MPU-6500 IMU *(optional)*
* BME280 environmental sensor *(optional)*
* Direct Ethernet connection to the Ground Control Station

## Technology Stack

* **Python 3** — Server application
* **Raspberry Pi 4B** — Onboard computing platform
* **pigpio** — GPIO and PWM control
* **I2C** — Sensor communication
* **dnsmasq** — Network configuration
* **MPU-6500** — IMU *(optional)*
* **BME280** — Environmental sensing *(optional)*

## Software Requirements

* Python 3
* `pigpio`
* `dnsmasq`
* I2C support when using the optional sensors

Python dependencies are listed in `requirements.txt`.

## Installation

### 1. Configure the Network

The included script configures the Raspberry Pi for direct Ethernet communication with the Ground Control Station.

```bash
chmod +x Scripts/setup_dhcp.sh
sudo ./Scripts/setup_dhcp.sh
```

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install pigpio python3-pip python3-venv python3-smbus dnsmasq libcamera
```

### 3. Create the Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Manual Execution

### 1. Start the `pigpiod` daemon

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

The server will then wait for connections from the Ground Control Station.

## Related Repository

The Ground Control Station for the ROV is available here:
- [HindenburgDroneClient](https://github.com/LowK3/HindenburgDroneClient)
