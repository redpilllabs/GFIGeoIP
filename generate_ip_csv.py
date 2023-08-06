#!/usr/bin/env python

# This product includes GeoLite2 Data created by MaxMind, available from https://www.maxmind.com/
# Usage is subject to EULA available from https://www.maxmind.com/en/geolite2/eula

import os
from pathlib import Path

import pandas as pd

from lib.adapters import convert_xls_to_df
from lib.cidr_utils import (concat_df, convert_iprange_to_cidr,
                            expand_cidr_range)
from lib.dbip import load_dbip_csv
from lib.fetchers import fetch_autonomous_system_cidrs, fetch_remote_ip_list
from lib.geolite2 import load_geolite2_csv


def main():
    export_dir_path = "./Aggregated_Data"
    data_dir_path = "./Data_Source"
    geolite2_db_dir = f"{data_dir_path}/GeoLite2"
    autonomous_systems_db_dir = f"{data_dir_path}/AS_CIDRs"
    manual_db_dir = f"{data_dir_path}/Manual"
    dbip_filename = "dbip-country-lite-2023-02.csv"
    ito_website_excel_filename = "Export-14011212203139.xls"
    ito_im_excel_filename = "Export-14011212203100.xls"

    aggregated_ipv4_df = pd.DataFrame(columns=["Network", "Tag"])
    aggregated_ipv6_df = pd.DataFrame(columns=["Network", "Tag"])
    aggregated_df = pd.DataFrame(columns=["Network", "Tag"])
    geo_networks = [
        {"name": "China", "tag": "CN"},
        {"name": "Iran", "tag": "IR"},
    ]
    content_networks = [
        {"name": "Pornography", "tag": "XX"}
    ]

    fetch_autonomous_system_cidrs(
        asn_list_path="./Data_Source/asn_list.toml",
        output_dir="./Data_Source/AS_CIDRs",
        proxies=proxies,
    )
    fetch_autonomous_system_cidrs(asn_list_path="./Data_Source/asn_list.toml",output_dir="./Data_Source/AS_CIDRs")

    # First off append the Cloudflare network IPs
    cf_ipv4_df = fetch_remote_ip_list("https://www.cloudflare.com/ips-v4", "CF")
    if not cf_ipv4_df.empty:
        aggregated_ipv4_df = concat_df(aggregated_ipv4_df, cf_ipv4_df)

    cf_ipv6_df = fetch_remote_ip_list("https://www.cloudflare.com/ips-v6", "CF")
    if not cf_ipv6_df.empty:
        aggregated_ipv6_df = concat_df(aggregated_ipv6_df, cf_ipv6_df)

    # Append ArvanCloud network as IR
    ac_ipv4_df = fetch_remote_ip_list("https://www.arvancloud.ir/fa/ips.txt", "IR")
    if ac_ipv4_df:
        aggregated_ipv4_df = concat_df(aggregated_ipv4_df, ac_ipv4_df)

    if os.path.exists(data_dir_path):
        for network in geo_networks:
            print(f"\n\n*** Aggregating data for {network['name']} ***")

            # Load DBIP database
            print("\nLoading DBIP database")
            dbip_ipv4, dbip_ipv6 = load_dbip_csv(
                file_path=f"{data_dir_path}/{dbip_filename}",
                tag=network["tag"],
            )
            # Convert IP range to CIDR
            dbip_ipv4 = convert_iprange_to_cidr(dbip_ipv4, ipv6=False)
            dbip_ipv6 = convert_iprange_to_cidr(dbip_ipv6, ipv6=True)

            print(f"IPv4 entries found: {len(dbip_ipv4)}")
            print(f"IPv6 entries found: {len(dbip_ipv6)}")

            # Add to aggregated DataFrame
            aggregated_ipv4_df = concat_df(aggregated_ipv4_df, dbip_ipv4)
            aggregated_ipv6_df = concat_df(aggregated_ipv6_df, dbip_ipv6)

            # Load MaxMind GeoLite2 database
            print("\nLoading MaxMind GeoLite2 database")
            geolite2_ipv4_df, geolite2_ipv6_df = load_geolite2_csv(
                dir_path=geolite2_db_dir, geolocation=network
            )

            print(f"IPv4 entries found: {len(geolite2_ipv4_df)}")
            print(f"IPv6 entries found: {len(geolite2_ipv6_df)}")

            # Add to aggregated DataFrame
            aggregated_ipv4_df = concat_df(aggregated_ipv4_df, geolite2_ipv4_df)
            aggregated_ipv6_df = concat_df(aggregated_ipv6_df, geolite2_ipv6_df)

            # Load and concat autonomous systems CIDRs CSVs
            print("\nLoading autonomous systems CIDR database")
            if Path(
                f"{autonomous_systems_db_dir}/ipv4_{network['tag']}.csv"
            ).is_file():
                as_ipv4_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv4_{network['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(as_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, as_ipv4_df)

            if Path(
                f"{autonomous_systems_db_dir}/ipv6_{network['tag']}.csv"
            ).is_file():
                as_ipv6_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv6_{network['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(as_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, as_ipv6_df)

            # Load manually found CIDRs if available
            print("\nLoading manually found CIDR database")
            if Path(f"{manual_db_dir}/ipv4_{network['tag']}.csv").is_file():
                manual_ipv4_df = pd.read_csv(
                    f"{manual_db_dir}/ipv4_{network['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(manual_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, manual_ipv4_df)

            if Path(f"{manual_db_dir}/ipv6_{network['tag']}.csv").is_file():
                manual_ipv6_df = pd.read_csv(
                    f"{manual_db_dir}/ipv6_{network['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(manual_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, manual_ipv6_df)

            # Load ITO database
            if network["tag"] == "IR":
                print("\nLoading ITO website database")
                ito_df = convert_xls_to_df(f"{data_dir_path}/{ito_website_excel_filename}")
                print(f"IPv4 entries found: {len(ito_df)}")
                aggregated_ipv4_df = pd.concat(
                    [aggregated_ipv4_df, ito_df], ignore_index=True
                )

                print("\nLoading ITO instant messengers database")
                ito_df = convert_xls_to_df(f"{data_dir_path}/{ito_im_excel_filename}")
                print(f"IPv4 entries found: {len(ito_df)}")
                aggregated_ipv4_df = pd.concat(
                    [aggregated_ipv4_df, ito_df], ignore_index=True
                )

        # Content-based aggregation
        for network in content_networks:
            print(f"\n\n*** Aggregating data for {network['name']} ***")

            # Load and concat autonomous systems CIDRs CSVs
            print("\nLoading autonomous systems CIDR database")
            if Path(f"{autonomous_systems_db_dir}/ipv4_{network['tag']}.csv").is_file():
                as_ipv4_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv4_{network['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(as_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, as_ipv4_df)

            if Path(f"{autonomous_systems_db_dir}/ipv6_{network['tag']}.csv").is_file():
                as_ipv6_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv6_{network['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(as_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, as_ipv6_df)

            # Load manually found CIDRs if available
            print("\nLoading manually found CIDR database")
            if Path(f"{manual_db_dir}/ipv4_{network['tag']}.csv").is_file():
                manual_ipv4_df = pd.read_csv(
                    f"{manual_db_dir}/ipv4_{network['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(manual_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, manual_ipv4_df)

            if Path(f"{manual_db_dir}/ipv6_{network['tag']}.csv").is_file():
                manual_ipv6_df = pd.read_csv(
                    f"{manual_db_dir}/ipv6_{network['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(manual_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, manual_ipv6_df)

        # Remove duplicates
        print("\n====================================")
        print("||     Cleaning up duplicates     ||")
        print("====================================")
        print("\n-> Dropping duplicates")
        aggregated_ipv4_df = aggregated_ipv4_df.drop_duplicates()
        aggregated_ipv6_df = aggregated_ipv6_df.drop_duplicates()

        aggregated_ipv4_df = expand_cidr_range(aggregated_ipv4_df)

        print("\n====================================")
        print("||           Results              ||")
        print("====================================")
        print(f"--- Total unique IPv4 entries: {len(aggregated_ipv4_df)}")
        print(f"--- Total unique IPv6 entries: {len(aggregated_ipv6_df)}")

        # Merge IPv4 and IPv6 into one DataFrame for easier processing
        aggregated_df = pd.concat(
            [aggregated_ipv4_df, aggregated_ipv6_df], ignore_index=True
        )

        # Save merged CSV
        print(f"\nSaving CSV to {export_dir_path}/agg_cidrs.csv")
        os.makedirs(export_dir_path, exist_ok=True)
        aggregated_df.to_csv(f"{export_dir_path}/agg_cidrs.csv", index=False)
    else:
        print(f"Database directory '{data_dir_path}' was not found!")
        exit(0)


if __name__ == "__main__":
    main()
