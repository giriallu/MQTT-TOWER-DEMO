import json
import argparse
from datetime import datetime
from paho.mqtt import client as mqtt


def now():
    return datetime.now().isoformat(timespec="seconds")


def send_command(broker, port, tower_id, command):
    client = mqtt.Client(
        client_id="STARHUB_COMMAND_CLIENT",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    client.connect(broker, port, keepalive=30)

    topic = f"starhub/tower/{tower_id}/command"

    payload = {
        "commandId": f"CMD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "command": command,
        "requestedBy": "NOC_OPERATOR",
        "timestamp": now()
    }

    client.publish(topic, json.dumps(payload), qos=1)

    print("[COMMAND SENT]")
    print(f"Topic: {topic}")
    print(json.dumps(payload, indent=2))

    client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send command to telecom tower simulator")

    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--tower", default="TOWER001")
    parser.add_argument("--command", required=True)

    args = parser.parse_args()

    send_command(
        broker=args.broker,
        port=args.port,
        tower_id=args.tower,
        command=args.command
    )