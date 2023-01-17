#!/usr/bin/env python

import socket
import sys
from os import makedirs
from time import sleep

import pandas as pd

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


def fetch_cidrs(asn_dict: dict):
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
    ipv4_df["Country"] = asn_dict["country"]
    ipv6_df["Country"] = asn_dict["country"]

    return ipv4_df, ipv6_df


def main():
    output_dir = "./Data/AS_CIDRs"
    country_iso_codes = ["CN", "IR", "RU"]
    asn_filename = "./Data/asn_list.toml"
    cidrs_ivp4_df = pd.DataFrame()
    cidrs_ivp6_df = pd.DataFrame()

    with open(asn_filename, mode="rb") as asn_file:
        if sys.version_info[1] < 11:
            asn_list = tomli.load(asn_file)["autonomous_systems"]
        else:
            asn_list = tomllib.load(asn_file)["autonomous_systems"]

    for country in country_iso_codes:
        print(f"\n\n--- Fetching Autonomous System CIDRs for {country} ---\n\n")
        country_asn_list = [item for item in asn_list if item["country"] == country]

        for item in country_asn_list:
            ipv4_df, ipv6_df = fetch_cidrs(asn_dict=item)
            cidrs_ivp4_df = pd.concat([cidrs_ivp4_df, ipv4_df], ignore_index=True)
            cidrs_ivp6_df = pd.concat([cidrs_ivp6_df, ipv6_df], ignore_index=True)
            # Take some rest
            sleep(1)

        # Remove duplicates
        cidrs_ivp4_df = cidrs_ivp4_df.drop_duplicates()
        cidrs_ivp6_df = cidrs_ivp6_df.drop_duplicates()

        # Save to CSV
        makedirs(output_dir, exist_ok=True)
        cidrs_ivp4_df.to_csv(f"{output_dir}/ipv4_{country}.csv", index=False)
        cidrs_ivp6_df.to_csv(f"{output_dir}/ipv6_{country}.csv", index=False)


if __name__ == "__main__":
    main()
