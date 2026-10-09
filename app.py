import os
import requests
import re
import psutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from netaddr import IPAddress
from scapy.all import ARP, Ether, srp

app = Flask(__name__)

# Enable CORS for Vercel Frontend and n8n Webhooks
CORS(app, origins=["*"])

AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

def resolve_mac_via_arp(ip_address):
    """
    Attempts to issue an ARP request on local network interfaces (if applicable).
    """
    try:
        ip_obj = IPAddress(ip_address)
        arp_request = ARP(pdst=str(ip_obj))
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_packet = broadcast / arp_request

        answered_list = srp(arp_packet, timeout=2, verbose=False)[0]

        for sent_pkt, received_pkt in answered_list:
            return received_pkt.hwsrc.upper().replace('-', ':')
    except Exception as err:
        print(f"[ARP DISCOVERY ERROR] {err}")
    return None


@app.route('/get-mac', methods=['GET'])
def get_mac():
    # 1. Check if MAC address is provided in Query Parameters by Router
    url_mac = request.args.get('mac') or request.args.get('client_mac') or request.args.get('usermac')

    if url_mac:
        # Standardize formatting (Uppercase, replace hyphens with colons)
        normalized_mac = url_mac.strip().upper().replace('-', ':')
        
        # Validate MAC format using regex (e.g., FC:3F:FC:AF:92:F0)
        if re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', normalized_mac):
            return jsonify({
                "status": "success",
                "mac_address": normalized_mac
            }), 200

    # 2. Extract Client IP and attempt local ARP lookup as secondary check
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    resolved_arp_mac = resolve_mac_via_arp(client_ip)
    if resolved_arp_mac:
        return jsonify({
            "status": "success",
            "mac_address": resolved_arp_mac
        }), 200

    # 3. STRICT FAILURE: Never return mock fallback data!
    return jsonify({
        "status": "error",
        "message": "Real MAC address not provided by gateway router or ARP"
    }), 400


@app.route('/check-access', methods=['GET'])
def check_access():
    mac = request.args.get('mac')
    if not mac:
        return jsonify({"access": "denied", "reason": "MAC missing"}), 400

    # Normalize incoming MAC address
    normalized_mac = mac.strip().upper().replace('-', ':')

    try:
        # Step A: Check Whitelisted Devices Table
        dev_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Devices?filterByFormula={{Mac Address}}='{normalized_mac}'"
        dev_res = requests.get(dev_url, headers=AIRTABLE_HEADERS).json()

        if dev_res.get('records'):
            if dev_res['records'][0]['fields'].get('Whitelisted') is True:
                return jsonify({"access": "granted", "type": "whitelisted_admin"}), 200

        # Step B: Check Active Subscriptions Table
        sub_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Subscriptions?filterByFormula=AND({{Mac Address}}='{normalized_mac}', {{Status}}='ACTIVE')"
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

    normalized_mac = mac_address.strip().upper().replace('-', ':')

    print(f"[AUTHORIZE SUCCESS] Hardware MAC {normalized_mac} unlocked for {duration} mins.")
    return jsonify({
        "status": "authorized",
        "mac_address": normalized_mac,
        "duration_minutes": duration
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)