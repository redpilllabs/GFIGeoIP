#!/usr/bin/env python
import glob
from os import getcwd, makedirs
from os.path import exists
from pathlib import Path

import pandas as pd
from lib.adapters import convert_xls_to_df
from lib.cidr_utils import (
    calculate_ip_stats,
    cleanup_cidrs,
    concat_df,
    convert_iprange_to_cidr,
    expand_cidr_range,
    pretty_print_stats,
)
from lib.dbip import extract_dbip_ip_versions
from lib.fetchers import fetch_remote_ip_list
from lib.geolite2 import extract_geolite2_cidrs, get_geolite2_id

# This product includes geolite2 Data created by MaxMind, available from https://www.maxmind.com/
# Usage is subject to EULA available from https://www.maxmind.com/en/geolite2/eula


def main():
    data_dir_path = f"{getcwd()}/data"
    build_dir_path = f"{getcwd()}/build"
    community_db_dir = f"{data_dir_path}/community"
    geolite2_db_dir = f"{data_dir_path}/geolite2"
    ito_db_dir = f"{data_dir_path}/ito"
    dbip_db_dir = f"{data_dir_path}/dbip"

    makedirs(build_dir_path, exist_ok=True)

    aggregated_ipv4_df = pd.DataFrame(columns=["Network", "Tag"])
    aggregated_ipv6_df = pd.DataFrame(columns=["Network", "Tag"])
    geo_networks = [
        {"name": "China", "tag": "CN"},
        {"name": "Russia", "tag": "RU"},
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

    if exists(data_dir_path):
        for tag in geo_networks:
            print(f"\n\n*** Aggregating data for {tag['name']} ***")

            # Load DBIP database
            dbip_csvs = glob.glob(f"{dbip_db_dir}/*.csv")
            for csv_file in dbip_csvs:
                print("\nLoading DBIP database")
                dbip_df = pd.read_csv(
                    csv_file, names=["Range_Start", "Range_End", "Tag"]
                )
                dbip_ipv4, dbip_ipv6 = extract_dbip_ip_versions(
                    dbip_df,
                    tag=tag["tag"],
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
            print("\nLoading MaxMind GeoLite2 database")
            geolite2_countries_df = pd.read_csv(
                f"{geolite2_db_dir}/GeoLite2-Country-Locations-en.csv"
            )
            geolite2_ipv4_df = pd.read_csv(
                f"{geolite2_db_dir}/GeoLite2-Country-Blocks-IPv4.csv"
            )
            geolite2_ipv6_df = pd.read_csv(
                f"{geolite2_db_dir}/GeoLite2-Country-Blocks-IPv6.csv"
            )
            geo_id = get_geolite2_id(
                geolite2_countries_df,
                country=tag["name"],
            )
            geolite2_ipv4_df_filtered = extract_geolite2_cidrs(
                geolite2_ipv4_df, geo_id, tag["tag"]
            )
            geolite2_ipv6_df_filtered = extract_geolite2_cidrs(
                geolite2_ipv6_df, geo_id, tag["tag"]
            )

            print(f"IPv4 entries found: {len(geolite2_ipv4_df_filtered)}")
            print(f"IPv6 entries found: {len(geolite2_ipv6_df_filtered)}")

            # Add to aggregated DataFrame
            aggregated_ipv4_df = concat_df(
                aggregated_ipv4_df, geolite2_ipv4_df_filtered
            )
            aggregated_ipv6_df = concat_df(
                aggregated_ipv6_df, geolite2_ipv6_df_filtered
            )

            # Load community-contributed CIDRs if available
            print("\nLoading community-contributed CIDR database")
            if Path(f"{community_db_dir}/ipv4_{tag['tag']}.csv").is_file():
                manual_ipv4_df = pd.read_csv(
                    f"{community_db_dir}/ipv4_{tag['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(manual_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, manual_ipv4_df)

            if Path(f"{community_db_dir}/ipv6_{tag['tag']}.csv").is_file():
                manual_ipv6_df = pd.read_csv(
                    f"{community_db_dir}/ipv6_{tag['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(manual_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, manual_ipv6_df)

            # Load ito database
            if tag["tag"] == "IR":
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
        for tag in aggregated_df["Tag"].unique().tolist():
            aggregated_df[aggregated_df["Tag"] == tag]["Network"].to_csv(
                f"{build_dir_path}/geoip_{tag.lower()}.txt",
                index=False,
                header=False,
            )

        print("\n====================================")
        print("||           Results              ||")
        print("====================================")
        stats = calculate_ip_stats(aggregated_df)
        pretty_print_stats(stats)

        # Save merged CSV
        print(f"\nSaving CSV to {build_dir_path}/agg_cidrs.csv")
        aggregated_df.to_csv(f"{build_dir_path}/agg_cidrs.csv", index=False)
    else:
        print(f"Database directory '{data_dir_path}' was not found!")
        exit(0)


if __name__ == "__main__":
    main()
