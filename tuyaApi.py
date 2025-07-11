import os
import json
import time
import requests
from typing import List, Dict, Optional, Union

# Configuration paths
TOKEN_PATH = os.path.expanduser('~/tuya/credentials.json')
DEVICES_PATH = os.path.expanduser('~/tuya/devices.json')
LOCKS_PATH = os.path.expanduser('~/tuya/lock_states.json')  # New lock state file
LOGIN_URI = "https://px1.tuyaus.com/homeassistant/auth.do"
REFRESH_URI = "https://px1.tuyaus.com/homeassistant/access.do"
DEVICE_URI = "https://px1.tuyaus.com/homeassistant/skill"

class TuyaApi:
    def __init__(self):
        self.session_data = self._load_token()
        self.devices = self._load_devices()
        self.lock_states = self._load_lock_states()  # Load lock states

    def _load_token(self) -> Optional[dict]:
        """Load token from credentials file if exists"""
        try:
            with open(TOKEN_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _load_devices(self) -> List[dict]:
        """Load devices list from file if exists"""
        try:
            with open(DEVICES_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _load_lock_states(self) -> Dict[str, bool]:
        """Load lock states from file if exists"""
        try:
            with open(LOCKS_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_token(self):
        """Save token to credentials file"""
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, 'w') as f:
            json.dump(self.session_data, f, indent=2)

    def _save_devices(self):
        """Save devices list to file"""
        os.makedirs(os.path.dirname(DEVICES_PATH), exist_ok=True)
        with open(DEVICES_PATH, 'w') as f:
            json.dump(self.devices, f, indent=2)

    def _save_lock_states(self):
        """Save lock states to file"""
        os.makedirs(os.path.dirname(LOCKS_PATH), exist_ok=True)
        with open(LOCKS_PATH, 'w') as f:
            json.dump(self.lock_states, f, indent=2)

    def set_device_lock_state(self, device_id: str, locked: bool):
        """Set and save lock state for a device"""
        self.lock_states[device_id] = locked
        self._save_lock_states()

    def get_device_lock_state(self, device_id: str) -> bool:
        """Get lock state for a device"""
        return self.lock_states.get(device_id, False)

    def login(self, username: str, password: str, 
              country_code: str = "95", 
              biz_type: str = "tuya", 
              from_: str = "tuya") -> str:
        """
        Authenticate with Tuya API
        Returns 'success' or error message
        """
        payload = {
            'userName': username,
            'password': password,
            'countryCode': country_code,
            'bizType': biz_type,
            'from': from_
        }
        
        try:
            response = requests.post(LOGIN_URI, data=payload)
            response.raise_for_status()
            res_data = response.json()
        except Exception as e:
            return f"Login failed: {str(e)}"
        
        if res_data.get('responseStatus') == 'error' or not res_data.get('access_token'):
            return res_data.get('errorMsg', 'Unknown authentication error')
        
        self.session_data = {
            'access_token': res_data['access_token'],
            'refresh_token': res_data['refresh_token'],
            'token_type': res_data['token_type'],
            'expires_in': res_data['expires_in'],
            'expires_at': int(time.time()) + res_data['expires_in']
        }
        
        self._save_token()
        return "success"

    def logout(self):
        """Clear session and delete credential files"""
        self.session_data = None
        self.devices = []
        try:
            os.remove(TOKEN_PATH)
            os.remove(DEVICES_PATH)
        except FileNotFoundError:
            pass

    async def refresh_token(self):
        """Refresh access token using refresh token"""
        if not self.session_data or 'refresh_token' not in self.session_data:
            return
        
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.session_data['refresh_token']
        }
        
        try:
            response = requests.post(REFRESH_URI, data=payload)
            response.raise_for_status()
            res_data = response.json()
        except Exception:
            return
        
        if 'access_token' in res_data:
            self.session_data = {
                'access_token': res_data['access_token'],
                'refresh_token': res_data['refresh_token'],
                'token_type': res_data['token_type'],
                'expires_in': res_data['expires_in'],
                'expires_at': int(time.time()) + res_data['expires_in']
            }
            self._save_token()

    async def discover_devices(self):
        """Discover and save all devices"""
        if not self.is_authenticated():
            return
        
        # Refresh token if expired
        if time.time() > self.session_data['expires_at']:
            await self.refresh_token()
        
        payload = {
            "header": {
                "name": "Discovery",
                "namespace": "discovery",
                "payloadVersion": 1
            },
            "payload": {
                "accessToken": self.session_data['access_token']
            }
        }
        
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(DEVICE_URI, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
        except Exception:
            return
        
        if res_data.get('header', {}).get('code') == 'SUCCESS':
            self.devices = res_data.get('payload', {}).get('devices', [])
            self._save_devices()

    async def control_device(self, device_id: str, state: int):
        """
        Control device state
        :param device_id: Device ID to control
        :param state: 0 for off, 1 for on
        """
        if not self.is_authenticated():
            return
        
        # Refresh token if expired
        if time.time() > self.session_data['expires_at']:
            await self.refresh_token()
        
        payload = {
            "header": {
                "name": "turnOnOff",
                "namespace": "control",
                "payloadVersion": 1
            },
            "payload": {
                "accessToken": self.session_data['access_token'],
                "devId": device_id,
                "value": state
            }
        }
        
        try:
            headers = {'Content-Type': 'application/json'}
            requests.post(DEVICE_URI, json=payload, headers=headers)
        except Exception:
            pass

    def is_authenticated(self) -> bool:
        """Check if valid session exists"""
        return (
            self.session_data is not None and
            'access_token' in self.session_data and
            time.time() < self.session_data.get('expires_at', 0)
        )

    def get_devices(self) -> List[dict]:
        """Get list of discovered devices"""
        return self.devices