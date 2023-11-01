#!/usr/bin/env python
import os
import sys
import zipfile
import socket
from time import sleep

import pandas as pd
import requests

# Check for Tomli
try:
    import tomllib  # Python ^3.11
except ModuleNotFoundError:
    try:
        import tomli
    except ModuleNotFoundError:
        print(
            "Module 'tomli' was not found! [pip install tomli] (only Python versions older than 3.11)\n"
        )
        exit(0)


def fetch_remote_ip_list(url: str, network_tag: str, proxies=None):
    ip_list = []
    df = pd.DataFrame()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    response = requests.get(url, headers=headers, proxies=proxies)
    data = response.content.decode()
    for entry in data.split():
        ip_list.append(entry)
    if ip_list:
        df = pd.DataFrame(ip_list, columns=["Network"])
        df["Tag"] = network_tag
    return df


def download_and_unzip_geoip_database(license_key, output_file):
    """Downloads and unzips a GeoIP database from MaxMind.

    Args:
      license_key: The MaxMind license key.
      output_file: The path to the output file.
    """

    # Download the GeoIP database.
    url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country-CSV&license_key={license_key}&suffix=zip"
    response = requests.get(url)
    response.raise_for_status()

    # Save the GeoIP database to a file.
    with open(output_file, "wb") as f:
        f.write(response.content)

    # Unzip the GeoIP database.
    with zipfile.ZipFile(output_file, "r") as zip_file:
        zip_file.extractall()

    # Remove the GeoIP database ZIP file.
    os.remove(output_file)
