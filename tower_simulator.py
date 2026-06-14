import json
import random
import time
import argparse
from datetime import datetime
from paho.mqtt import client as mqtt


class TowerSimulator:
    def __init__(self, broker, port, tower_id, interval):
        self.broker = broker
        self.port = port
        self.tower_id = tower_id
        self.interval = interval

        self.base_topic = f"starhub/tower/{self.tower_id}"

        self.telemetry_topic = f"{self.base_topic}/telemetry"
        self.alarm_topic = f"{self.base_topic}/alarm"
        self.status_topic = f"{self.base_topic}/status"
        self.command_topic = f"{self.base_topic}/command"
        self.command_ack_topic = f"{self.base_topic}/command/ack"

        self.state = {
            "mainsAvailable": True,
            "batteryLevel": 95,
            "generatorRunning": False,
            "fuelPercent": 80,
            "doorOpen": False,
            "routerOnline": True
        }

        self.client = mqtt.Client(
            client_id=f"SIM_{self.tower_id}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )

        last_will_payload = {
            "towerId": self.tower_id,
            "status": "OFFLINE",
            "message": "Tower simulator disconnected unexpectedly",
            "timestamp": self.now()
        }

        self.client.will_set(
            self.status_topic,
            payload=json.dumps(last_will_payload),
            qos=1,
            retain=True
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def now(self):
        return datetime.now().isoformat(timespec="seconds")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"[CONNECTED] Tower {self.tower_id} connected to MQTT broker")

        online_payload = {
            "towerId": self.tower_id,
            "status": "ONLINE",
            "message": "Tower simulator connected",
            "timestamp": self.now()
        }

        client.publish(
            self.status_topic,
            json.dumps(online_payload),
            qos=1,
            retain=True
        )

        client.subscribe(self.command_topic, qos=1)
        print(f"[SUBSCRIBED] {self.command_topic}")

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            command = payload.get("command")
            command_id = payload.get("commandId", "UNKNOWN")

            print(f"[COMMAND RECEIVED] {command}")

            result = self.execute_command(command)

            ack_payload = {
                "towerId": self.tower_id,
                "commandId": command_id,
                "command": command,
                "result": result,
                "timestamp": self.now()
            }

            client.publish(
                self.command_ack_topic,
                json.dumps(ack_payload),
                qos=1
            )

        except Exception as error:
            print(f"[ERROR] Failed to process command: {error}")

    def execute_command(self, command):
        if command == "REBOOT_ROUTER":
            self.state["routerOnline"] = False
            time.sleep(2)
            self.state["routerOnline"] = True
            return "Router rebooted successfully"

        elif command == "START_GENERATOR":
            self.state["generatorRunning"] = True
            return "Generator started"

        elif command == "STOP_GENERATOR":
            self.state["generatorRunning"] = False
            return "Generator stopped"

        elif command == "OPEN_DOOR_TEST":
            self.state["doorOpen"] = True
            return "Door opened for testing"

        elif command == "CLOSE_DOOR_TEST":
            self.state["doorOpen"] = False
            return "Door closed"

        elif command == "SET_MAINS_OFF":
            self.state["mainsAvailable"] = False
            self.state["generatorRunning"] = True
            return "Mains power switched OFF. Generator started."

        elif command == "SET_MAINS_ON":
            self.state["mainsAvailable"] = True
            self.state["generatorRunning"] = False
            return "Mains power restored. Generator stopped."

        else:
            return "Unsupported command"

    def generate_telemetry(self):

        mains = self.state["mainsAvailable"]

        if mains:
            voltage = round(random.uniform(225, 235), 2)
            self.state["batteryLevel"] = min(
                100,
                self.state["batteryLevel"] + 1
            )
        else:
            voltage = round(random.uniform(210, 220), 2)
            self.state["batteryLevel"] = max(
                0,
                self.state["batteryLevel"] - random.randint(1, 3)
            )

        if self.state["generatorRunning"]:
            self.state["fuelPercent"] = max(
                0,
                self.state["fuelPercent"] - random.randint(0, 1)
            )

        temperature = round(random.uniform(26, 42), 2)

        if self.state["routerOnline"]:
            signal = random.randint(-75, -55)
            latency = random.randint(15, 80)
            packet_loss = round(random.uniform(0.0, 1.5), 2)
            network_status = 1
        else:
            signal = -999
            latency = 999
            packet_loss = 100
            network_status = 0

        payload = {
            "towerId": self.tower_id,
            "timestamp": self.now(),

            # Power
            "mainsAvailable": int(mains),
            "voltage": voltage,

            # Battery
            "batteryPercent": self.state["batteryLevel"],
            "batteryVoltage": round(
                random.uniform(48, 54),
                2
            ),

            # Generator
            "generatorRunning": int(
                self.state["generatorRunning"]
            ),
            "fuelPercent": self.state["fuelPercent"],
            "generatorRuntimeMinutes":
                random.randint(0, 300)
                if self.state["generatorRunning"]
                else 0,

            # Environment
            "temperatureC": temperature,
            "doorOpen": int(
                self.state["doorOpen"]
            ),

            # Network
            "networkStatus": network_status,
            "signalDbm": signal,
            "latencyMs": latency,
            "packetLossPercent": packet_loss
        }

        return payload

    def check_alarms(self, telemetry):

        alarms = []

        if telemetry["mainsAvailable"] == 0:
            alarms.append({
                "severity": "CRITICAL",
                "alarmCode": "MAINS_POWER_FAILURE",
                "message": "Mains power failed."
            })

        if telemetry["batteryPercent"] < 30:
            alarms.append({
                "severity": "CRITICAL",
                "alarmCode": "LOW_BATTERY",
                "message": "Battery level below 30%."
            })

        if telemetry["fuelPercent"] < 20:
            alarms.append({
                "severity": "MAJOR",
                "alarmCode": "LOW_GENERATOR_FUEL",
                "message": "Generator fuel below 20%."
            })

        if telemetry["temperatureC"] > 38:
            alarms.append({
                "severity": "MAJOR",
                "alarmCode": "HIGH_TEMPERATURE",
                "message": "Tower shelter temperature high."
            })

        if telemetry["doorOpen"] == 1:
            alarms.append({
                "severity": "MAJOR",
                "alarmCode": "DOOR_OPEN",
                "message": "Tower door is open."
            })

        if telemetry["networkStatus"] == 0:
            alarms.append({
                "severity": "CRITICAL",
                "alarmCode": "NETWORK_DEVICE_OFFLINE",
                "message": "Router offline."
            })

        return alarms

    def start(self):
        self.client.connect(self.broker, self.port, keepalive=30)
        self.client.loop_start()

        try:
            while True:
                telemetry = self.generate_telemetry()

                self.client.publish(
                    self.telemetry_topic,
                    json.dumps(telemetry),
                    qos=1
                )

                print(f"[TELEMETRY] {self.tower_id} published telemetry")

                alarms = self.check_alarms(telemetry)

                for alarm in alarms:
                    alarm_payload = {
                        "towerId": self.tower_id,
                        "timestamp": self.now(),
                        **alarm
                    }

                    self.client.publish(
                        self.alarm_topic,
                        json.dumps(alarm_payload),
                        qos=1
                    )

                    print(f"[ALARM] {alarm_payload['alarmCode']} - {alarm_payload['severity']}")

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n[STOPPING] Simulator stopped by user")

            offline_payload = {
                "towerId": self.tower_id,
                "status": "OFFLINE",
                "message": "Tower simulator stopped normally",
                "timestamp": self.now()
            }

            self.client.publish(
                self.status_topic,
                json.dumps(offline_payload),
                qos=1,
                retain=True
            )

            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telecom Tower MQTT Simulator")

    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--tower", default="TOWER001")
    parser.add_argument("--interval", type=int, default=5)

    args = parser.parse_args()

    simulator = TowerSimulator(
        broker=args.broker,
        port=args.port,
        tower_id=args.tower,
        interval=args.interval
    )

    simulator.start()