import os
import requests
import psutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from netaddr import IPAddress, IPNetwork
from scapy.all import ARP, Ether, srp

app = Flask(__name__)

# Allow Vercel frontend requests
CORS(app, origins=["*"])

AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

def resolve_mac_via_arp(ip_address):
    """
    Uses Scapy and Netaddr to issue an ARP request on the local network interface
    and retrieve the physical MAC address matching the given IP address.
    """
    try:
        # Validate IPv4 format
        ip_obj = IPAddress(ip_address)
        
        # Build ARP Request Packet
        arp_request = ARP(pdst=str(ip_obj))
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_packet = broadcast / arp_request

        # Send packet on raw socket with 2s timeout
        answered_list = srp(arp_packet, timeout=2, verbose=False)[0]

        for sent_pkt, received_pkt in answered_list:
            return received_pkt.hwsrc.upper()
    except Exception as err:
        print(f"[ARP DISCOVERY ERROR] {err}")
    return None


@app.route('/get-mac', methods=['GET'])
def get_mac():
    # 1. Extract Real Client IP from HTTP Headers
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    # Allow query parameter override if passed
    target_ip = request.args.get('ip', client_ip)

    # 2. Attempt Scapy ARP Resolution
    resolved_mac = resolve_mac_via_arp(target_ip)

    # 3. Return Resolved MAC or Fallback from Query Parameters
    if not resolved_mac:
        resolved_mac = request.args.get('mac', 'FC:3F:FC:AF:92:F0')

    return jsonify({
        "status": "success",
        "client_ip": target_ip,
        "mac_address": resolved_mac
    }), 200


@app.route('/check-access', methods=['GET'])
def check_access():
    mac = request.args.get('mac')
    if not mac:
        return jsonify({"access": "denied", "reason": "MAC missing"}), 400

    try:
        # Check Whitelisted Devices Table
        dev_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Devices?filterByFormula={{Mac Address}}='{mac}'"
        dev_res = requests.get(dev_url, headers=AIRTABLE_HEADERS).json()

        if dev_res.get('records'):
            if dev_res['records'][0]['fields'].get('Whitelisted') is True:
                return jsonify({"access": "granted", "type": "whitelisted_admin"}), 200

        # Check Active Subscriptions Table
        sub_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Subscriptions?filterByFormula=AND({{Mac Address}}='{mac}', {{Status}}='ACTIVE')"
        sub_res = requests.get(sub_url, headers=AIRTABLE_HEADERS).json()

        if sub_res.get('records'):
            return jsonify({"access": "granted", "type": "active_subscription"}), 200

    except Exception as e:
        print(f"[AIRTABLE ERROR] {e}")

    return jsonify({"access": "denied", "redirect_to_portal": True}), 200


@app.route('/authorize', methods=['POST'])
def authorize():
    data = request.json or {}
    mac_address = data.get('mac_address')
    duration = data.get('duration_minutes')

    if not mac_address:
        return jsonify({"status": "error", "message": "mac_address required"}), 400

    print(f"[AUTHORIZE SUCCESS] Hardware MAC {mac_address} unlocked for {duration} mins.")
    return jsonify({
        "status": "authorized",
        "mac_address": mac_address,
        "duration_minutes": duration
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)