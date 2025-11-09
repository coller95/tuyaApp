import os
import asyncio
from flask import Flask, render_template, request, jsonify, redirect, url_for
from tuyaApi import TuyaApi

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Tuya API client
tuya = TuyaApi()

@app.route('/')
def index():
    """Render main control interface"""
    if not tuya.is_authenticated():
        return redirect(url_for('login_page'))
    
    # Get devices with lock states
    devices_with_locks = []
    for device in tuya.get_devices():
        device_data = device.copy()
        device_data['locked'] = tuya.get_device_lock_state(device['id'])
        devices_with_locks.append(device_data)
    
    return render_template('index.html', devices=devices_with_locks)

@app.route('/login', methods=['GET'])
def login_page():
    """Render login page"""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle login form submission"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Missing credentials'}), 400
    
    result = tuya.login(username, password)
    if result == "success":
        asyncio.run(tuya.discover_devices())
        return jsonify({'success': True, 'redirect': url_for('index')})
    return jsonify({'success': False, 'message': result}), 401

@app.route('/logout')
def logout():
    """Handle logout"""
    tuya.logout()
    return redirect(url_for('login_page'))

@app.route('/devices')
def get_devices():
    """Get list of devices (JSON endpoint)"""
    if not tuya.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Return devices with lock states
    devices_with_locks = []
    for device in tuya.get_devices():
        device_data = device.copy()
        device_data['locked'] = tuya.get_device_lock_state(device['id'])
        devices_with_locks.append(device_data)
    
    return jsonify(devices_with_locks)

@app.route('/control', methods=['POST'])
def control_device():
    """Control a device"""
    if not tuya.is_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    device_id = request.json.get('device_id')
    state = request.json.get('state')
    
    if not device_id or state is None:
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400
    
    try:
        asyncio.run(tuya.control_device(device_id, int(state)))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/refresh')
def refresh_devices():
    """Refresh device list"""
    if not tuya.is_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    asyncio.run(tuya.discover_devices())
    
    # Return devices with lock states
    devices_with_locks = []
    for device in tuya.get_devices():
        device_data = device.copy()
        device_data['locked'] = tuya.get_device_lock_state(device['id'])
        devices_with_locks.append(device_data)
    
    return jsonify({'success': True, 'devices': devices_with_locks})

@app.route('/set_lock', methods=['POST'])
def set_lock_state():
    """Set lock state for a device"""
    if not tuya.is_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    device_id = request.json.get('device_id')
    locked = request.json.get('locked')
    
    if not device_id or locked is None:
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400
    
    try:
        tuya.set_device_lock_state(device_id, locked)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Enable hot reload with debug mode
    # use_reloader=True enables automatic reloading when code changes
    # extra_files can be used to watch additional file types
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True,
        use_reloader=True,
        extra_files=[
            'templates/index.html',
            'templates/login.html',
            'static/style.css',
            'tuyaApi.py'
        ]
    )