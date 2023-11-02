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
