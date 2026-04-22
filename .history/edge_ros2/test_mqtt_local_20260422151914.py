"""
edge_ros2 Local MQTT Test Script (Windows-compatible)
======================================================
This script tests MQTT connectivity and simulates the edge_ros2 behavior
for testing purposes on Windows without ROS2.

Usage:
    python test_mqtt_local.py [--mode mock|aws]

Options:
    --mode mock: Test with simulated data (no real MQTT broker needed)
    --mode aws:  Test connection to AWS IoT Core (requires certificates)
"""

import argparse
import json
import time
import uuid
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False
    print("[WARN] paho-mqtt not installed. Run: pip install paho-mqtt")

# Configuration
AWS_IOT_ENDPOINT = "a26ix7882z43xd-ats.iot.ap-south-1.amazonaws.com"
AWS_REGION = "ap-south-1"
DEVICE_ID = "fw-edge-001"
CAMERA_ID = "FP_CAM_001"
