import random
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import OTP

def generate_otp_code():
    return ''.join(random.choices('0123456789', k=6))

def send_verification_code(phone_number):
    # Create or update OTP record
    code = generate_otp_code()
    otp, created = OTP.objects.update_or_create(
        phone_number=phone_number,
        defaults={
            'code': code,
            'created_at': timezone.now(),
            'expires_at': timezone.now() + timedelta(minutes=5),
            'attempt_count': 0,
            'is_verified': False,
        }
    )

    # Mock mode for testing (prints code to console)
    if getattr(settings, 'MOCK_SMS', False):
        print(f"[MOCK] Code for {phone_number}: {otp.code}")
        return {"status": "mock"}
    print(f"CODE IS : {code}")
    # Production SMS.ir API
    api_key = settings.SMS_IR_API_KEY
    template_id = int(settings.SMS_IR_VERIFY_TEMPLATE_ID)
    # Match your template's placeholder – adjust as needed
    param_name = "code"   # use "Code" if your template uses #CODE#

    url = "https://api.sms.ir/v1/send/verify"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/plain',
        'x-api-key': api_key
    }
    payload = {
        "mobile": phone_number,
        "templateId": template_id,
        "parameters": [{"name": param_name, "value": otp.code}]
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    result = response.json()
    print(f"SMS.ir response: {result}")

    if response.status_code != 200 or result.get('status') != 1:
        raise Exception(f"SMS failed: {result.get('message')}")
    return result