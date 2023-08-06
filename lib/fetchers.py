#!/usr/bin/env python
import sys
from os import makedirs
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

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


def fetch_ipinfo_cidrs(asn_dict: dict, proxies=None):
    ipv4_df = pd.DataFrame(columns=["Network", "Tag"])
    ipv6_df = pd.DataFrame(columns=["Network", "Tag"])

    url = "https://ipinfo.io/AS41689"

    # Send a GET request to fetch the HTML content of the page
    headers = {
        "Host": "ipinfo.io",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86\_64; rv:109.0) Gecko/20100101 Firefox/116.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,\*/\*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cookie": "flash=",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }

    print(f"Fetching CIDRs for {asn_dict['name']} ...")
    response = requests.get(
        url,
        headers=headers,
        proxies=proxies,
    )

    if response.status_code != 200:
        print(
            f"Failed to fetch IP ranges for {asn_dict['name']}. Status code: {response.status_code} {response.reason}"
        )
    else:
        soup = BeautifulSoup(response.content, "html.parser")
        ipv4_ranges_table = soup.select_one(
            "#ipv4-data > table:nth-child(1) > tbody:nth-child(2)"
        )
        ipv6_ranges_table = soup.select_one(
            "#ipv6-data > table:nth-child(1) > tbody:nth-child(2)"
        )

        if ipv4_ranges_table:
            ipv4_ranges = ipv4_ranges_table.find_all("tr")
            ipv4_ranges = sorted(list(set(ipv4_ranges)))
            ipv4_df = pd.DataFrame(ipv4_ranges, columns=["Network"])
            ipv4_df["Tag"] = asn_dict["tag"]

        if ipv6_ranges_table:
            ipv6_ranges = ipv6_ranges_table.find_all("tr")
            ipv6_ranges = sorted(list(set(ipv6_ranges)))
            ipv6_df = pd.DataFrame(ipv6_ranges, columns=["Network"])
            ipv6_df["Tag"] = asn_dict["tag"]

        return ipv4_df, ipv6_df


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


def fetch_autonomous_system_cidrs(asn_list_path: str, output_dir: str, proxies=None):
    with open(asn_list_path, mode="rb") as asn_file:
        if sys.version_info[1] < 11:
            asn_list = tomli.load(asn_file)["autonomous_systems"]
            tags = [x["tag"] for x in asn_list]
            tags = set(tags)
        else:
            asn_list = tomllib.load(asn_file)["autonomous_systems"]
            tags = [x["tag"] for x in asn_list]
            tags = set(tags)

    for tag in tags:
        cidrs_ivp4_df = pd.DataFrame()
        cidrs_ivp6_df = pd.DataFrame()
        print(f"\n\n--- Fetching Autonomous System CIDRs tagged as '{tag}' ---\n\n")
        autonomous_systems = [item for item in asn_list if item["tag"] == tag]

        for item in autonomous_systems:
            ipv4_df, ipv6_df = fetch_ipinfo_cidrs(item, proxies=proxies)
            cidrs_ivp4_df = pd.concat([cidrs_ivp4_df, ipv4_df], ignore_index=True)
            cidrs_ivp6_df = pd.concat([cidrs_ivp6_df, ipv6_df], ignore_index=True)
            # Take some rest
            sleep(2)

        # Remove duplicates
        cidrs_ivp4_df = cidrs_ivp4_df.drop_duplicates()
        cidrs_ivp6_df = cidrs_ivp6_df.drop_duplicates()

        # Save to CSV
        makedirs(output_dir, exist_ok=True)
        cidrs_ivp4_df.to_csv(f"{output_dir}/ipv4_{tag}.csv", index=False)
        cidrs_ivp6_df.to_csv(f"{output_dir}/ipv6_{tag}.csv", index=False)
