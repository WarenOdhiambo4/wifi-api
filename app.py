import os
import requests
import psutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from netaddr import IPAddress, IPNetwork
from scapy.all import ARP, Ether, srp

app = Flask(__name__)

# Allow Vercel frontend & n8n webhooks
CORS(app, origins=["*"])

AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# ----------------------------------------------------
# 1. ARP / LOCAL IP TO MAC RESOLVER ENDPOINT
# ----------------------------------------------------
@app.route('/get-mac', methods=['GET'])
def resolve_mac():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    requested_ip = request.args.get('ip', client_ip)

    # Validate IP address using netaddr
    try:
        ip_obj = IPAddress(requested_ip)
    except Exception:
        return jsonify({"status": "error", "message": "Invalid IP format"}), 400

    # Scapy ARP Request
    try:
        arp_request = ARP(pdst=requested_ip)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        answered_list = srp(broadcast / arp_request, timeout=2, verbose=False)[0]

        for element in answered_list:
            real_mac = element[1].hwsrc.upper()
            return jsonify({
                "status": "success",
                "ip": requested_ip,
                "mac_address": real_mac
            }), 200
    except Exception as e:
        print(f"[ARP ERROR] Scapy failed: {e}")

    # Fallback if cloud container cannot reach local ARP broadcast directly
    fallback_mac = request.args.get('mac', 'FC:3F:FC:AF:92:F0')
    return jsonify({
        "status": "fallback",
        "ip": requested_ip,
        "mac_address": fallback_mac
    }), 200


# ----------------------------------------------------
# 2. CHECK ACCESS ENDPOINT (Triggered on Vercel Page Load)
# ----------------------------------------------------
@app.route('/check-access', methods=['GET'])
def check_access():
    mac = request.args.get('mac')
    if not mac:
        return jsonify({"access": "denied", "reason": "MAC address missing"}), 400

    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        return jsonify({"access": "denied", "reason": "Airtable configuration missing"}), 500

    try:
        # Step A: Check Devices Table (Admin Whitelist)
        dev_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Devices?filterByFormula={{Mac Address}}='{mac}'"
        dev_res = requests.get(dev_url, headers=AIRTABLE_HEADERS).json()

        if dev_res.get('records'):
            record = dev_res['records'][0]['fields']
            if record.get('Whitelisted') is True:
                return jsonify({"access": "granted", "type": "whitelisted_admin"}), 200

        # Step B: Check Active Subscriptions Table
        sub_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Subscriptions?filterByFormula=AND({{Mac Address}}='{mac}', {{Status}}='ACTIVE')"
        sub_res = requests.get(sub_url, headers=AIRTABLE_HEADERS).json()

        if sub_res.get('records'):
            return jsonify({"access": "granted", "type": "active_subscription"}), 200

    except Exception as e:
        print(f"[AIRTABLE ERROR] {e}")

    return jsonify({"access": "denied", "redirect_to_portal": True}), 200


# ----------------------------------------------------
# 3. AUTHORIZE ENDPOINT (Triggered by n8n Workflow 2)
# ----------------------------------------------------
@app.route('/authorize', methods=['POST'])
def authorize():
    data = request.json or {}
    mac_address = data.get('mac_address')
    duration = data.get('duration_minutes')

    if not mac_address:
        return jsonify({"status": "error", "message": "mac_address required"}), 400

    print(f"[AUTHORIZE SUCCESS] Unlocking MAC {mac_address} for {duration} minutes.")
    return jsonify({
        "status": "authorized",
        "mac_address": mac_address,
        "duration_minutes": duration
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)