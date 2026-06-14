import json
import argparse
from paho.mqtt import client as mqtt


class NocMonitor:
    def __init__(self, broker, port):
        self.broker = broker
        self.port = port

        self.client = mqtt.Client(
            client_id="STARHUB_NOC_MONITOR",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print("[CONNECTED] NOC Monitor connected")

        client.subscribe("starhub/tower/+/telemetry", qos=1)
        client.subscribe("starhub/tower/+/alarm", qos=1)
        client.subscribe("starhub/tower/+/status", qos=1)
        client.subscribe("starhub/tower/+/command/ack", qos=1)

        print("[SUBSCRIBED] starhub/tower/+/telemetry")
        print("[SUBSCRIBED] starhub/tower/+/alarm")
        print("[SUBSCRIBED] starhub/tower/+/status")
        print("[SUBSCRIBED] starhub/tower/+/command/ack")

    def on_message(self, client, userdata, message):
        topic = message.topic

        try:
            payload = json.loads(message.payload.decode())

            print("\n================ MQTT MESSAGE ================")
            print(f"Topic: {topic}")
            print(json.dumps(payload, indent=2))
            print("==============================================")

        except Exception:
            print(f"[RAW MESSAGE] {topic}: {message.payload.decode()}")

    def start(self):
        self.client.connect(self.broker, self.port, keepalive=30)
        self.client.loop_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StarHub NOC MQTT Monitor")

    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)

    args = parser.parse_args()

    monitor = NocMonitor(args.broker, args.port)
    monitor.start()