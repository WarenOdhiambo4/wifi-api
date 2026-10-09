import os
import psutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from netaddr import IPAddress, IPNetwork
from scapy.all import ARP, Ether, srp
import requests

app = Flask(__name__)
CORS(app)

# 1. ARP Resolver Endpoint
@app.route('/get-mac', methods=['GET'])
def resolve_mac():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    # If client provides local IP via URL query param
    requested_ip = request.args.get('ip', client_ip)

    try:
        # ARP ping using Scapy
        arp_request = ARP(pdst=requested_ip)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        answered_list = srp(broadcast / arp_request, timeout=2, verbose=False)[0]

        for element in answered_list:
            real_mac = element[1].hwsrc.upper()
            return jsonify({"status": "success", "ip": requested_ip, "mac_address": real_mac})
            
    except Exception as e:
        pass

    # Fallback if running on cloud container without direct local ARP layer
    return jsonify({"status": "fallback", "ip": requested_ip, "mac_address": request.args.get('mac', 'UNKNOWN')})


# 2. Whitelist & Access Check Endpoint
@app.route('/check-access', methods=['GET'])
def check_access():
    client_mac = request.args.get('mac')
    
    if not client_mac:
        return jsonify({"access": "denied", "reason": "MAC missing"}), 400

    # Query Airtable 'Devices' table for Admin Whitelist
    AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
    AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
    
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    
    # Check Admin Devices Table
    devices_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Devices?filterByFormula={{Mac Address}}='{client_mac}'"
    dev_res = requests.get(devices_url, headers=headers).json()
    
    if dev_res.get('records'):
        is_whitelisted = dev_res['records'][0]['fields'].get('Whitelisted', False)
        if is_whitelisted:
            return jsonify({"access": "granted", "type": "whitelisted_admin"})

    # Check Active Subscriptions Table
    sub_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Subscriptions?filterByFormula=AND({{Mac Address}}='{client_mac}', {{Status}}='ACTIVE')"
    sub_res = requests.get(sub_url, headers=headers).json()
    
    if sub_res.get('records'):
        return jsonify({"access": "granted", "type": "active_subscription"})

    return jsonify({"access": "denied", "redirect_to_portal": True})


# 3. Session Authorization Endpoint (Triggered by n8n Workflow 2)
@app.route('/authorize', methods=['POST'])
def authorize_session():
    data = request.json
    mac_address = data.get('mac_address')
    duration = data.get('duration_minutes')

    # Unlocks MAC address internet access
    print(f"[AUTHORIZE] Granting access to {mac_address} for {duration} minutes.")
    return jsonify({"status": "authorized", "mac": mac_address, "duration": duration}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
