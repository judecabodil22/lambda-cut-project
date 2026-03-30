#!/usr/bin/env python3
"""
Lambda Cut Keychain Manager
Handles secure storage and retrieval of API keys using system keychain.
"""
import os
import keyring

SERVICE_NAME = "lambda-cut"


def get_service_password(username):
    """Retrieve password from system keychain."""
    try:
        password = keyring.get_password(SERVICE_NAME, username)
        return password
    except Exception:
        return None


def set_service_password(username, password):
    """Store password in system keychain."""
    try:
        keyring.set_password(SERVICE_NAME, username, password)
        return True
    except Exception:
        return False


def delete_service_password(username):
    """Delete password from system keychain."""
    try:
        keyring.delete_password(SERVICE_NAME, username)
        return True
    except Exception:
        return False


def get_all_keys():
    """Get all stored API keys."""
    keys = {
        "gemini_api_key": get_service_password("gemini-api-key"),
        "telegram_bot_token": get_service_password("telegram-bot-token"),
        "telegram_chat_id": get_service_password("telegram-chat-id"),
    }
    return keys


def set_gemini_keys(keys_list):
    """Store multiple Gemini API keys."""
    for i, key in enumerate(keys_list):
        username = f"gemini-key-{i+1}"
        set_service_password(username, key)


def get_gemini_keys():
    """Retrieve all Gemini API keys."""
    keys = []
    i = 1
    while True:
        username = f"gemini-key-{i}"
        key = get_service_password(username)
        if key is None:
            break
        keys.append(key)
        i += 1
    return keys


def has_keychain_access():
    """Check if keychain is accessible."""
    try:
        keyring.get_password(SERVICE_NAME, "test")
        return True
    except Exception:
        return False


def migrate_from_file(filepath, key_prefix):
    """Migrate keys from a file to keychain (one key per line)."""
    if not os.path.exists(filepath):
        return False
    
    try:
        with open(filepath, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
        
        if not keys:
            return False
        
        for i, key in enumerate(keys):
            username = f"{key_prefix}-{i+1}"
            set_service_password(username, key)
        
        return True
    except Exception:
        return False


def set_gcloud_tts_keys(keys_list):
    """Store multiple Google Cloud TTS API keys."""
    for i, key in enumerate(keys_list):
        username = f"gcloud-tts-key-{i+1}"
        set_service_password(username, key)


def get_gcloud_tts_keys():
    """Retrieve all Google Cloud TTS API keys."""
    keys = []
    i = 1
    while True:
        username = f"gcloud-tts-key-{i}"
        key = get_service_password(username)
        if key is None:
            break
        keys.append(key)
        i += 1
    return keys
