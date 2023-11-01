#!/usr/bin/env python
import glob
import os
from pathlib import Path

import pandas as pd

from lib.adapters import convert_xls_to_df
from lib.cidr_utils import (calculate_ip_stats, cleanup_cidrs, concat_df, convert_iprange_to_cidr, expand_cidr_range,
                            pretty_print_stats)
from lib.dbip import load_dbip_csv
from lib.fetchers import fetch_remote_ip_list
from lib.geolite2 import load_geolite2_csv


# This product includes geolite2 Data created by MaxMind, available from https://www.maxmind.com/
# Usage is subject to EULA available from https://www.maxmind.com/en/geolite2/eula


def main():
    data_export_dir_path = "./data"
    resources_dir_path = "./resources"
    community_db_dir = f"{resources_dir_path}/community"
    geolite2_db_dir = f"{resources_dir_path}/geolite2"
    ito_db_dir = f"{resources_dir_path}/ito"
    dbip_db_dir = f"{resources_dir_path}/dbip"

    aggregated_ipv4_df = pd.DataFrame(columns=["Network", "Tag"])
    aggregated_ipv6_df = pd.DataFrame(columns=["Network", "Tag"])
    geo_networks = [
        {"name": "China", "tag": "CN"},
        {"name": "Iran", "tag": "IR"},
    ]

    # First off append the Cloudflare network IPs
    cf_ipv4_df = fetch_remote_ip_list("https://www.cloudflare.com/ips-v4", "CF")
    if not cf_ipv4_df.empty:
        aggregated_ipv4_df = concat_df(aggregated_ipv4_df, cf_ipv4_df)

    cf_ipv6_df = fetch_remote_ip_list("https://www.cloudflare.com/ips-v6", "CF")
    if not cf_ipv6_df.empty:
        aggregated_ipv6_df = concat_df(aggregated_ipv6_df, cf_ipv6_df)

    # Append ArvanCloud network as IR
    ac_ipv4_df = fetch_remote_ip_list(
        "https://www.arvancloud.ir/fa/ips.txt", "IR", proxies=None
    )
    if not ac_ipv4_df.empty:
        aggregated_ipv4_df = concat_df(aggregated_ipv4_df, ac_ipv4_df)

    if os.path.exists(resources_dir_path):
        for network in geo_networks:
            print(f"\n\n*** Aggregating data for {network['name']} ***")

            # Load DBIP database
            dbip_csvs = glob.glob(f"{dbip_db_dir}/*.csv")
            for csv_file in dbip_csvs:
                print("\nLoading DBIP database")
                dbip_ipv4, dbip_ipv6 = load_dbip_csv(
                    file_path=csv_file,
                    tag=network["tag"],
                )
                # Convert IP ranges to CIDR
                dbip_ipv4 = convert_iprange_to_cidr(dbip_ipv4, ipv6=False)
                dbip_ipv6 = convert_iprange_to_cidr(dbip_ipv6, ipv6=True)

                print(f"IPv4 entries found: {len(dbip_ipv4)}")
                print(f"IPv6 entries found: {len(dbip_ipv6)}")

                # Add to aggregated DataFrame
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, dbip_ipv4)
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, dbip_ipv6)

            # Load MaxMind geolite2 database
            print("\nLoading MaxMind geolite2 database")
            geolite2_ipv4_df, geolite2_ipv6_df = load_geolite2_csv(
                dir_path=geolite2_db_dir, geolocation=network
            )

            print(f"IPv4 entries found: {len(geolite2_ipv4_df)}")
            print(f"IPv6 entries found: {len(geolite2_ipv6_df)}")

            # Add to aggregated DataFrame
            aggregated_ipv4_df = concat_df(aggregated_ipv4_df, geolite2_ipv4_df)
            aggregated_ipv6_df = concat_df(aggregated_ipv6_df, geolite2_ipv6_df)

            # Load community-contributed CIDRs if available
            print("\nLoading community-contributed CIDR database")
            if Path(f"{community_db_dir}/ipv4_{network['tag']}.csv").is_file():
                manual_ipv4_df = pd.read_csv(
                    f"{community_db_dir}/ipv4_{network['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(manual_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, manual_ipv4_df)

            if Path(f"{community_db_dir}/ipv6_{network['tag']}.csv").is_file():
                manual_ipv6_df = pd.read_csv(
                    f"{community_db_dir}/ipv6_{network['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(manual_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, manual_ipv6_df)

            # Load ito database
            if network["tag"] == "IR":
                dbip_csvs = glob.glob(f"{ito_db_dir}/*.xls")
                for csv_file in dbip_csvs:
                    print(f"\nLoading ITO database {csv_file}")
                    ito_ipv4_df, ito_ipv6_df = convert_xls_to_df(csv_file)

                    print(f"IPv4 entries found: {len(ito_ipv4_df)}")
                    aggregated_ipv4_df = pd.concat(
                        [aggregated_ipv4_df, ito_ipv4_df], ignore_index=True
                    )
                    print(f"IPv6 entries found: {len(ito_ipv6_df)}")
                    aggregated_ipv6_df = pd.concat(
                        [aggregated_ipv6_df, ito_ipv6_df], ignore_index=True
                    )

        # Remove duplicates
        print("\n====================================")
        print("||     Cleaning up duplicates     ||")
        print("====================================")
        print("\n-> Dropping duplicates")
        aggregated_ipv4_df = aggregated_ipv4_df.drop_duplicates()
        aggregated_ipv6_df = aggregated_ipv6_df.drop_duplicates()
        aggregated_ipv4_df = expand_cidr_range(aggregated_ipv4_df)
        aggregated_ipv4_df = cleanup_cidrs(aggregated_ipv4_df)
        aggregated_ipv6_df = cleanup_cidrs(aggregated_ipv6_df)

        # Merge IPv4 and IPv6 into one DataFrame for easier processing
        aggregated_df = pd.concat(
            [aggregated_ipv4_df, aggregated_ipv6_df], ignore_index=True
        )

        # Export to specific files to build binary .dat files for clients
        for network in geo_networks:
            tag = network["tag"]
            aggregated_df[aggregated_df['Tag'] == tag]["Network"].to_csv(f"{community_db_dir}/v2ray/geoip_{tag.lower()}.txt",
                                                                         index=False,
                                                                         header=False,
                                                                         )

        print("\n====================================")
        print("||           Results              ||")
        print("====================================")
        stats = calculate_ip_stats(aggregated_df)
        pretty_print_stats(stats)

        # Save merged CSV
        print(f"\nSaving CSV to {data_export_dir_path}/agg_cidrs.csv")
        os.makedirs(data_export_dir_path, exist_ok=True)
        aggregated_df.to_csv(f"{data_export_dir_path}/agg_cidrs.csv", index=False)
    else:
        print(f"Database directory '{resources_dir_path}' was not found!")
        exit(0)


if __name__ == "__main__":
    main()
