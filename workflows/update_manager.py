#!/usr/bin/env python3
"""
Lambda Cut Update Manager
Handles version checking, updates, and backups.
"""

import os
import json
import shutil
import zipfile
import tempfile
import urllib.request
import urllib.error
from datetime import datetime


# ==============================
# Configuration
# ==============================

VERSION_URL = "https://raw.githubusercontent.com/judecabodil22/lambda-cut-project/main/VERSION"
RELEASES_API_URL = "https://api.github.com/repos/judecabodil22/lambda-cut-project/releases/latest"
DOWNLOAD_URL_TEMPLATE = "https://github.com/judecabodil22/lambda-cut-project/archive/refs/tags/v{version}.zip"

MAX_BACKUPS = 2

# Files/directories to preserve during update
PRESERVE_FILES = [
    ".env",
    "pipeline.log",
    "gemini_keys.txt",
]

PRESERVE_DIRS = [
    "scripts",
    "shorts",
    "tts",
    "transcripts",
    "streams",
    "backups",
    "output",
]


# ==============================
# Version Management
# ==============================

def get_local_version(project_root):
    """Get current version from VERSION file."""
    version_file = os.path.join(project_root, "VERSION")
    try:
        with open(version_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


def get_remote_version():
    """Get latest version from GitHub."""
    try:
        req = urllib.request.Request(
            VERSION_URL,
            headers={"User-Agent": "Lambda-Cut-Updater"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8").strip()
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None


def compare_versions(local_version, remote_version):
    """
    Compare version strings.
    Returns: -1 if local < remote, 0 if equal, 1 if local > remote
    """
    def parse_version(v):
        parts = v.split(".")
        return tuple(int(p) for p in parts)
    
    try:
        local_parts = parse_version(local_version)
        remote_parts = parse_version(remote_version)
        
        if local_parts < remote_parts:
            return -1
        elif local_parts > remote_parts:
            return 1
        else:
            return 0
    except (ValueError, TypeError):
        return 0


def is_update_available(project_root):
    """Check if update is available."""
    local_version = get_local_version(project_root)
    remote_version = get_remote_version()
    
    if remote_version is None:
        return False, local_version, None
    
    if compare_versions(local_version, remote_version) < 0:
        return True, local_version, remote_version
    
    return False, local_version, remote_version


# ==============================
# Release Notes
# ==============================

def get_release_notes():
    """Fetch release notes from GitHub API."""
    try:
        req = urllib.request.Request(
            RELEASES_API_URL,
            headers={"User-Agent": "Lambda-Cut-Updater"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("body", "No release notes available.")
    except Exception:
        return "Unable to fetch release notes."


# ==============================
# Backup Management
# ==============================

def create_backup(project_root, version):
    """Create backup of current installation."""
    backup_dir = os.path.join(project_root, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"lambda_cut_v{version}_backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)
    
    # Create backup directory
    os.makedirs(backup_path)
    
    # Copy files, excluding large directories and backup dir itself
    exclude_dirs = {"streams", "backups", "__pycache__", ".git"}
    
    for item in os.listdir(project_root):
        if item in exclude_dirs:
            continue
        
        source = os.path.join(project_root, item)
        dest = os.path.join(backup_path, item)
        
        try:
            if os.path.isdir(source):
                shutil.copytree(source, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(source, dest)
        except Exception as e:
            print(f"Warning: Could not backup {item}: {e}")
    
    print(f"Backup created: {backup_path}")
    return backup_path


def cleanup_old_backups(project_root):
    """Keep only MAX_BACKUPS most recent backups."""
    backup_dir = os.path.join(project_root, "backups")
    if not os.path.exists(backup_dir):
        return
    
    backups = []
    for item in os.listdir(backup_dir):
        if item.startswith("lambda_cut_v") and item.endswith("_backup"):
            backup_path = os.path.join(backup_dir, item)
            if os.path.isdir(backup_path):
                backups.append((os.path.getmtime(backup_path), backup_path))
    
    # Sort by modification time (newest first)
    backups.sort(reverse=True)
    
    # Remove old backups
    for _, backup_path in backups[MAX_BACKUPS:]:
        try:
            shutil.rmtree(backup_path)
            print(f"Removed old backup: {backup_path}")
        except Exception as e:
            print(f"Warning: Could not remove backup {backup_path}: {e}")


# ==============================
# Update Download & Install
# ==============================

def download_update(version, dest_dir):
    """Download update from GitHub."""
    url = DOWNLOAD_URL_TEMPLATE.format(version=version)
    zip_file = os.path.join(dest_dir, f"lambda_cut_v{version}.zip")
    
    try:
        print(f"Downloading update from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Lambda-Cut-Updater"})
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(zip_file, "wb") as f:
                f.write(response.read())
        print(f"Downloaded: {zip_file}")
        return zip_file
    except Exception as e:
        print(f"Download failed: {e}")
        return None


def extract_update(zip_file, dest_dir):
    """Extract zipball to directory."""
    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(dest_dir)
        
        # Find the extracted directory
        extracted = [d for d in os.listdir(dest_dir) if os.path.isdir(os.path.join(dest_dir, d))]
        if extracted:
            return os.path.join(dest_dir, extracted[0])
        
        return dest_dir
    except Exception as e:
        print(f"Extraction failed: {e}")
        return None


def install_update(project_root, extracted_dir):
    """Install update, preserving user files."""
    preserve_set = set(PRESERVE_FILES + PRESERVE_DIRS)
    
    # Copy new files
    for item in os.listdir(extracted_dir):
        source = os.path.join(extracted_dir, item)
        dest = os.path.join(project_root, item)
        
        # Skip preserved files/directories
        if item in preserve_set:
            print(f"Skipping {item} (preserved)")
            continue
        
        try:
            if os.path.isdir(source):
                # Remove existing directory first
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, dest)
            print(f"Updated: {item}")
        except Exception as e:
            print(f"Warning: Could not update {item}: {e}")
    
    # Update VERSION file
    version_file = os.path.join(project_root, "VERSION")
    if os.path.exists(os.path.join(extracted_dir, "VERSION")):
        shutil.copy2(os.path.join(extracted_dir, "VERSION"), version_file)
        print("Updated VERSION file")


def cleanup_temp(temp_dir):
    """Clean up temporary directory."""
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


# ==============================
# Main Update Functions
# ==============================

def check_for_updates(project_root):
    """Check if updates are available."""
    is_available, local_ver, remote_ver = is_update_available(project_root)
    return {
        "update_available": is_available,
        "local_version": local_ver,
        "remote_version": remote_ver
    }


def perform_update(project_root):
    """Perform the full update process."""
    # Check if update is available
    update_info = check_for_updates(project_root)
    if not update_info["update_available"]:
        return {
            "success": False,
            "message": "No update available.",
            "version": update_info["local_version"]
        }
    
    local_version = update_info["local_version"]
    remote_version = update_info["remote_version"]
    
    print(f"Updating from v{local_version} to v{remote_version}...")
    
    # Create backup
    create_backup(project_root, local_version)
    
    # Clean up old backups
    cleanup_old_backups(project_root)
    
    # Create temp directory for download
    temp_dir = tempfile.mkdtemp(prefix="lambda_cut_update_")
    
    try:
        # Download update
        zip_file = download_update(remote_version, temp_dir)
        if zip_file is None:
            return {
                "success": False,
                "message": "Download failed.",
                "version": local_version
            }
        
        # Extract update
        extracted_dir = extract_update(zip_file, temp_dir)
        if extracted_dir is None:
            return {
                "success": False,
                "message": "Extraction failed.",
                "version": local_version
            }
        
        # Install update
        install_update(project_root, extracted_dir)
        
        # Clean up
        cleanup_temp(temp_dir)
        
        return {
            "success": True,
            "message": f"Successfully updated to v{remote_version}!",
            "version": remote_version
        }
        
    except Exception as e:
        # Clean up on error
        cleanup_temp(temp_dir)
        
        return {
            "success": False,
            "message": f"Update failed: {str(e)}",
            "version": local_version
        }


# ==============================
# Test Functions
# ==============================

def test_version_comparison():
    """Test version comparison logic."""
    print("Testing version comparison...")
    
    test_cases = [
        ("2.2.0", "2.2.1", -1),
        ("2.2.0", "2.2.0", 0),
        ("2.2.1", "2.2.0", 1),
        ("2.1.0", "2.2.0", -1),
        ("2.10.0", "2.2.0", 1),
        ("3.0.0", "2.9.9", 1),
    ]
    
    for local, remote, expected in test_cases:
        result = compare_versions(local, remote)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {local} vs {remote} = {result} (expected {expected})")


if __name__ == "__main__":
    # Run tests when executed directly
    test_version_comparison()
    
    # Check for updates
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"\nChecking for updates from {project_root}...")
    
    update_info = check_for_updates(project_root)
    print(f"Local version: {update_info['local_version']}")
    print(f"Remote version: {update_info['remote_version'] or 'Unknown'}")
    print(f"Update available: {update_info['update_available']}")
