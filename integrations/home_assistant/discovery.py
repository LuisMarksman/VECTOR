"""Publish Home Assistant MQTT-discovery configs for VECTOR devices.

Maps a VECTOR home device (``vector/home/<id>/{set,state}``) to a Home Assistant
``light`` entity so it shows up automatically in the HA UI.

Example::

    python discovery.py --device living-room-lamp --name "Living Room Lamp"
"""

from __future__ import annotations

import argparse
import json

import paho.mqtt.publish as publish


def build_config(device_id: str, name: str, base_topic: str) -> dict:
    """Build a Home Assistant MQTT-light discovery payload."""
    state_topic = f"{base_topic}/home/{device_id}/state"
    command_topic = f"{base_topic}/home/{device_id}/set"
    return {
        "name": name,
        "unique_id": f"vector_{device_id}",
        "command_topic": command_topic,
        "state_topic": state_topic,
        # VECTOR state: {"state": {"power": "on"|"off"}}
        "state_value_template": "{{ value_json.state.power }}",
        "payload_on": json.dumps({"action": "on"}),
        "payload_off": json.dumps({"action": "off"}),
        "state_on": "on",
        "state_off": "off",
        "device": {
            "identifiers": [f"vector_{device_id}"],
            "manufacturer": "VECTOR",
            "name": name,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, help="VECTOR device id")
    parser.add_argument("--name", required=True, help="Friendly name in Home Assistant")
    parser.add_argument("--base-topic", default="vector")
    parser.add_argument("--discovery-prefix", default="homeassistant")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()

    config = build_config(args.device, args.name, args.base_topic)
    topic = f"{args.discovery_prefix}/light/vector_{args.device}/config"
    publish.single(
        topic,
        payload=json.dumps(config),
        hostname=args.mqtt_host,
        port=args.mqtt_port,
        retain=True,
    )
    print(f"published discovery config to {topic}")


if __name__ == "__main__":
    main()
