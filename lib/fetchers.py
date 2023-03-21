#!/usr/bin/env python

import socket
import sys
from os import makedirs
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


def fetch_whois_cidrs(asn_dict: dict):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("whois.radb.net", 43))
        print(f"Fetching CIDRs for {asn_dict['name']} ...")
        s.sendall(b"-i origin " + bytes(asn_dict["asn"], encoding="utf-8") + b"\n")
        ipv4_data = ""
        ipv6_data = ""
        while True:
            data = s.recv(16).decode("utf8")
            if not data:
                break
            ipv4_data += data
            ipv6_data += data

    ipv4_data = [i for i in ipv4_data.split("\n") if i.startswith("route:")]
    ipv6_data = [i for i in ipv6_data.split("\n") if i.startswith("route6:")]

    result_ipv4 = []
    result_ipv6 = []
    for item in ipv4_data:
        result_ipv4.append(item.replace("route:", "").strip())
    for item in ipv6_data:
        result_ipv6.append(item.replace("route6:", "").strip())

    result_ipv4 = sorted(list(set(result_ipv4)))
    result_ipv6 = sorted(list(set(result_ipv6)))

    ipv4_df = pd.DataFrame(result_ipv4, columns=["Network"])
    ipv6_df = pd.DataFrame(result_ipv6, columns=["Network"])
    ipv4_df["Tag"] = asn_dict["tag"]
    ipv6_df["Tag"] = asn_dict["tag"]

    return ipv4_df, ipv6_df

def fetch_remote_ip_list(url: str, network_tag: str):
    ip_list = []
    df = pd.DataFrame()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    data = response.content.decode()
    for entry in data.split():
        ip_list.append(entry)
    if ip_list:
        df = pd.DataFrame(ip_list, columns=["Network"])
        df["Tag"] = network_tag
    return df


def fetch_autonomous_system_cidrs(asn_list_path: str, output_dir: str):
    with open(asn_list_path, mode="rb") as asn_file:
        if sys.version_info[1] < 11:
            asn_list = tomli.load(asn_file)["autonomous_systems"]
            tags = [x['tag'] for x in asn_list]
            tags = set(tags)
        else:
            asn_list = tomllib.load(asn_file)["autonomous_systems"]
            tags = [x['tag'] for x in asn_list]
            tags = set(tags)

    for tag in tags:
        cidrs_ivp4_df = pd.DataFrame()
        cidrs_ivp6_df = pd.DataFrame()
        print(f"\n\n--- Fetching Autonomous System CIDRs tagged as '{tag}' ---\n\n")
        autonomous_systems = [item for item in asn_list if item["tag"] == tag]

        for item in autonomous_systems:
            ipv4_df, ipv6_df = fetch_whois_cidrs(asn_dict=item)
            cidrs_ivp4_df = pd.concat([cidrs_ivp4_df, ipv4_df], ignore_index=True)
            cidrs_ivp6_df = pd.concat([cidrs_ivp6_df, ipv6_df], ignore_index=True)
            # Take some rest
            sleep(1)

        # Remove duplicates
        cidrs_ivp4_df = cidrs_ivp4_df.drop_duplicates()
        cidrs_ivp6_df = cidrs_ivp6_df.drop_duplicates()

        # Save to CSV
        makedirs(output_dir, exist_ok=True)
        cidrs_ivp4_df.to_csv(f"{output_dir}/ipv4_{tag}.csv", index=False)
        cidrs_ivp6_df.to_csv(f"{output_dir}/ipv6_{tag}.csv", index=False)
