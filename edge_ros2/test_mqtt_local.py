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
SITE_ID = "SITE-001"

# Test API endpoint
INGEST_API_URL = "https://va76meg87j.execute-api.ap-south-1.amazonaws.com"
INGEST_API_KEY = "nkTKOFu9gr70Ub3pNeEzjPBS4yHCR6LGAQwthmcM"


class MQTTTestClient:
    """Simulates the MQTT bridge behavior from edge_ros2"""
    
    def __init__(self, mode: str = "mock"):
        self.mode = mode
        self.connected = False
        self.messages_sent = 0
        self.messages_received = 0
        
        if mode == "aws" and PAHO_AVAILABLE:
            self.client = mqtt.Client(client_id=f"{DEVICE_ID}-{uuid.uuid4().hex[:8]}")
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
        else:
            self.client = None
            
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[✓] Connected to AWS IoT Core")
            self.connected = True
        else:
            print(f"[✗] Connection failed with code: {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        print(f"[!] Disconnected from AWS IoT Core (rc: {rc})")
        self.connected = False
        
    def _on_message(self, client, userdata, msg):
        self.messages_received += 1
        print(f"[MSG] Received on {msg.topic}: {msg.payload[:100]}...")
        
    def connect_aws(self) -> bool:
        """Connect to AWS IoT Core (requires certificates in certs/ folder)"""
        if not PAHO_AVAILABLE:
            print("[✗] paho-mqtt not available")
            return False
            
        cert_dir = "certs"
        import os
        ca_path = os.path.join(cert_dir, "root-CA.crt")
        cert_path = os.path.join(cert_dir, "device.cert.pem")
        key_path = os.path.join(cert_dir, "device.private.key")
        
        # Check if certificates exist
        if not all(os.path.exists(p) for p in [ca_path, cert_path, key_path]):
            print(f"[✗] AWS IoT certificates not found in {cert_dir}/")
            print(f"    Expected files: root-CA.crt, device.cert.pem, device.private.key")
            return False
            
        self.client.tls_set(ca_certs=ca_path, certfile=cert_path, keyfile=key_path)
        
        try:
            print(f"[*] Connecting to AWS IoT: {AWS_IOT_ENDPOINT}")
            self.client.connect(AWS_IOT_ENDPOINT, 8883, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[✗] Connection error: {e}")
            return False
            
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
    def publish_violation(self, payload: dict) -> bool:
        """Publish a violation event (simulates fw_ros2_mqtt_bridge)"""
        topic = f"footwatch/{SITE_ID}/{CAMERA_ID}/violation"
        
        if self.mode == "mock":
            print(f"\n[MOCK] Would publish violation to: {topic}")
            print(f"       Payload: {json.dumps(payload, indent=2)}")
            self.messages_sent += 1
            return True
        elif self.connected and self.client:
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            if result.rc == 0:
                print(f"[✓] Published violation to {topic}")
                self.messages_sent += 1
                return True
            else:
                print(f"[✗] Publish failed with rc: {result.rc}")
                return False
        else:
            print("[✗] Not connected to MQTT broker")
            return False
            
    def publish_health(self, payload: dict) -> bool:
        """Publish a health event"""
        topic = f"footwatch/{SITE_ID}/{CAMERA_ID}/health"
        
        if self.mode == "mock":
            print(f"\n[MOCK] Would publish health to: {topic}")
            print(f"       Payload: {json.dumps(payload, indent=2)}")
            self.messages_sent += 1
            return True
        elif self.connected and self.client:
            result = self.client.publish(topic, json.dumps(payload), qos=0)
            if result.rc == 0:
                print(f"[✓] Published health to {topic}")
                self.messages_sent += 1
                return True
            else:
                print(f"[✗] Publish failed with rc: {result.rc}")
                return False
        else:
            print("[✗] Not connected to MQTT broker")
            return False


def create_sample_violation() -> dict:
    """Create a sample violation payload matching edge_ros2 schema"""
    return {
        "schema_version": "v1",
        "event_id": str(uuid.uuid4()),
        "device_id": DEVICE_ID,
        "camera_id": CAMERA_ID,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": "VIOLATION_CONFIRMED",
        "speed_kmph": 45.5,
        "class_name": "two_wheeler",
        "confidence": 0.92,
        "plate_text": "DL 01 AB 1234",
        "ocr_confidence": 0.87,
        "gps_lat": 28.6139,
        "gps_lng": 77.2090,
        "location_name": "MG Road Footpath",
        "evidence_uri": f"s3://footwatch-dev-evidence-769213333967/violations/{uuid.uuid4()}.jpg",
        "pipeline_latency_ms": 125.5
    }


def create_sample_health() -> dict:
    """Create a sample health payload matching edge_ros2 schema"""
    return {
        "schema_version": "v1",
        "device_id": DEVICE_ID,
        "camera_id": CAMERA_ID,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline_running": True,
        "pipeline_fps": 24.5,
        "pipeline_latency_ms_p50": 42.3,
        "active_tracks": 3,
        "violations_session": 1,
        "mqtt_spool_depth": 0,
        "cpu_percent": 45.2,
        "memory_used_mb": 512.0,
        "cpu_temp_c": 55.0,
        "disk_free_gb": 15.2,
        "camera_connected": True,
        "camera_status": "OK",
        "frame_failures": 0,
        "reconnects": 0
    }


def test_http_ingest():
    """Test sending data to the backend HTTP API"""
    import requests
    
    print("\n" + "="*60)
    print("Testing Backend HTTP API Connection")
    print("="*60)
    
    headers = {
        "x-api-key": INGEST_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Test telemetry endpoint
    print("\n[*] Testing POST /ingest/v1/telemetry...")
    try:
        health = create_sample_health()
        health["camera_id"] = CAMERA_ID
        health["device_id"] = DEVICE_ID
        
        response = requests.post(
            f"{INGEST_API_URL}/ingest/v1/telemetry",
            json=health,
            headers=headers,
            timeout=10
        )
        print(f"    Response: {response.status_code} {response.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")
        
    # Test violation endpoint
    print("\n[*] Testing POST /ingest/v1/violations...")
    try:
        violation = create_sample_violation()
        idempotency_key = f"idem-{violation['event_id']}"
        
        response = requests.post(
            f"{INGEST_API_URL}/ingest/v1/violations",
            json=violation,
            headers={**headers, "x-idempotency-key": idempotency_key},
            timeout=10
        )
        print(f"    Response: {response.status_code} {response.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")
        
    # Test query endpoint
    print("\n[*] Testing GET /query/v1/live/cameras...")
    try:
        response = requests.get(
            f"{INGEST_API_URL}/query/v1/live/cameras",
            headers=headers,
            timeout=10
        )
        print(f"    Response: {response.status_code} {response.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")


def run_mock_test():
    """Run a mock test simulating edge_ros2 behavior"""
    print("\n" + "="*60)
    print("edge_ros2 MQTT Mock Test (No ROS2/Real MQTT Required)")
    print("="*60)
    
    client = MQTTTestClient(mode="mock")
    
    # Test 1: Create and publish sample violation
    print("\n[Test 1] Simulating violation detection from sensor bridge...")
    violation = create_sample_violation()
    success = client.publish_violation(violation)
    print(f"    Result: {'PASS' if success else 'FAIL'}")
    
    # Test 2: Create and publish sample health message
    print("\n[Test 2] Simulating health report from health node...")
    health = create_sample_health()
    success = client.publish_health(health)
    print(f"    Result: {'PASS' if success else 'FAIL'}")
    
    # Test 3: Simulate multiple violations
    print("\n[Test 3] Simulating batch violation detection...")
    for i in range(3):
        v = create_sample_violation()
        v["plate_text"] = f"DL {i:02d} AB {1234+i}"
        client.publish_violation(v)
        time.sleep(0.5)
    
    # Summary
    print("\n" + "="*60)
    print("Mock Test Summary")
    print("="*60)
    print(f"  Mode: Mock (no real MQTT broker)")
    print(f"  Messages that would be sent: {client.messages_sent}")
    print(f"  Messages received: {client.messages_received}")
    print("\n  For real MQTT testing on Linux/Raspberry Pi:")
    print("    1. Install ROS2 Humble")
    print("    2. Run: bash scripts/setup.sh")
    print("    3. Run: bash scripts/start.sh all")
    print("="*60)


def run_aws_test():
    """Run a real test against AWS IoT Core"""
    print("\n" + "="*60)
    print("edge_ros2 AWS IoT Core Test")
    print("="*60)
    
    client = MQTTTestClient(mode="aws")
    
    # Try to connect to AWS IoT
    if not client.connect_aws():
        print("\n[!] Could not connect to AWS IoT Core")
        print("    Make sure certificates are in certs/ folder:")
        print("    - root-CA.crt")
        print("    - device.cert.pem")
        print("    - device.private.key")
        return
        
    # Wait for connection
    print("[*] Waiting for connection...")
    timeout = 10
    start = time.time()
    while not client.connected and time.time() - start < timeout:
        time.sleep(0.5)
        
    if not client.connected:
        print("[✗] Connection timeout")
        client.disconnect()
        return
        
    # Subscribe to topics
    print("[*] Subscribing to violation topic...")
    client.client.subscribe(f"footwatch/{SITE_ID}/{CAMERA_ID}/violation", qos=1)
    
    # Test 1: Publish violation
    print("\n[Test 1] Publishing violation to AWS IoT...")
    violation = create_sample_violation()
    success = client.publish_violation(violation)
    print(f"    Result: {'PASS' if success else 'FAIL'}")
    
    # Test 2: Publish health
    print("\n[Test 2] Publishing health to AWS IoT...")
    health = create_sample_health()
    success = client.publish_health(health)
    print(f"    Result: {'PASS' if success else 'FAIL'}")
    
    # Wait for any incoming messages
    print("\n[*] Listening for messages (10 seconds)...")
    time.sleep(10)
    
    # Cleanup
    print("\n[*] Disconnecting from AWS IoT Core...")
    client.disconnect()
    
    # Summary
    print("\n" + "="*60)
    print("AWS IoT Test Summary")
    print("="*60)
    print(f"  Endpoint: {AWS_IOT_ENDPOINT}")
    print(f"  Device ID: {DEVICE_ID}")
    print(f"  Messages sent: {client.messages_sent}")
    print(f"  Messages received: {client.messages_received}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="edge_ros2 MQTT Test Script")
    parser.add_argument(
        "--mode", 
        choices=["mock", "aws"], 
        default="mock",
        help="Test mode: mock (simulated) or aws (real AWS IoT)"
    )
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("Footwatch Edge ROS2 - MQTT Connection Test")
    print("="*60)
    print(f"Device ID: {DEVICE_ID}")
    print(f"Camera ID: {CAMERA_ID}")
    print(f"Site ID: {SITE_ID}")
    print(f"Mode: {args.mode}")
    print("="*60)
    
    # Test HTTP API first
    test_http_ingest()
    
    # Run MQTT test
    if args.mode == "mock":
        run_mock_test()
    else:
        run_aws_test()


if __name__ == "__main__":
    main()
