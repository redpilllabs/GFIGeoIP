#!/usr/bin/env python

# This product includes GeoLite2 Data created by MaxMind, available from https://www.maxmind.com/
# Usage is subject to EULA available from https://www.maxmind.com/en/geolite2/eula


import glob
import ipaddress
import os

import pandas as pd
from bs4 import BeautifulSoup


def convert_iprange_to_cidr(df: pd.DataFrame, ipv6=False):
    """
    Converts IP ranges to CIDR format y.y.y.y/X

    Args:
        df (pd.DataFrame): DataFrame containing IP range data
        ipv6 (bool, optional): Whether IPv6 address format is wanted or IPv4. Defaults to False.

    Returns:
        DataFrame: DataFrame containing IP CIDR data
    """
    cidr_list = []
    for _, row in df.iterrows():
        startip = (
            ipaddress.IPv6Address(row["Range_Start"])
            if ipv6
            else ipaddress.IPv4Address(row["Range_Start"])
        )
        endip = (
            ipaddress.IPv6Address(row["Range_End"])
            if ipv6
            else ipaddress.IPv4Address(row["Range_End"])
        )
        summary = ipaddress.summarize_address_range(startip, endip)
        current_cidr = list(summary)
        for item in current_cidr:
            cidr_list.append({"Network": item.__str__(), "Country": row["Country"]})

    return pd.DataFrame(cidr_list)


def load_dbip_csv(file_path: str, country_iso_code: str):
    """
    Reads CSV file from DBIP

    Args:
        file_path (str): Path to CSV file.
        country_iso_code (str): Country code in ISO to extract rows of.

    Returns:
        DataFrame: Two DataFrames containing IPv4 and IPv6 data
    """
    df = pd.read_csv(file_path, names=["Range_Start", "Range_End", "Country"])
    df = df.loc[df["Country"].isin([country_iso_code])]
    df_ip4 = df.loc[~df["Range_Start"].str.contains(":")]
    df_ip6 = df.loc[df["Range_Start"].str.contains(":")]

    return df_ip4, df_ip6


def extract_geo_id(geolite2_countries_file: str, country: str):
    """
    Extracts GeoID of a given country from the 'GeoLite2-Country-Locations-en.csv'

    Args:
        geolite2_countries_file (str): Path to 'GeoLite2-Country-Locations-en.csv' file
        country (str): Country to extract GeoID

    Returns:
        int: GeoID
    """
    geoinfo_df = pd.read_csv(geolite2_countries_file)
    geoid = geoinfo_df.loc[geoinfo_df["country_name"] == country]["geoname_id"]
    return int(str(geoid.values[0]))


def extract_geolite2_cidr(geolite2_ipblocks_csv: str, geoid: int, iso_code: str):
    """
    Extracts CIDR data from the 'GeoLite2-Country-Blocks-IPv*.csv' files

    Args:
        geolite2_ipblocks_csv (str): Path to 'GeoLite2-Country-Blocks-IPv*.csv'
        geoid (int): GeoID of the CIDRs to extract
        iso_code (str): Country ISO code to append at the end

    Returns:
        DataFrame: DataFrame containing CIDR data
    """
    ipblocks_df = pd.read_csv(geolite2_ipblocks_csv)
    extracted_df = ipblocks_df.loc[
        (ipblocks_df["geoname_id"] == geoid)
        & (ipblocks_df["registered_country_geoname_id"] == geoid)
    ]
    extracted_df = extracted_df.drop(
        columns=[
            "geoname_id",
            "registered_country_geoname_id",
            "represented_country_geoname_id",
            "is_anonymous_proxy",
            "is_satellite_provider",
        ]
    )
    extracted_df = extracted_df.rename(columns={"network": "Network"})
    extracted_df["Country"] = iso_code
    return extracted_df


def load_geolite2_csv(dir_path: str, geolocation: dict):
    geo_id = extract_geo_id(
        f"{dir_path}/GeoLite2-Country-Locations-en.csv", country=geolocation["name"]
    )
    ipv4_df = extract_geolite2_cidr(
        f"{dir_path}/GeoLite2-Country-Blocks-IPv4.csv",
        geoid=geo_id,
        iso_code=geolocation["iso_code"],
    )
    ipv6_df = extract_geolite2_cidr(
        f"{dir_path}/GeoLite2-Country-Blocks-IPv6.csv",
        geoid=geo_id,
        iso_code=geolocation["iso_code"],
    )

    return ipv4_df, ipv6_df


def read_ito_db(xls_path: str):
    """
    Loads Excel sheet from ITO, extracts the CIDRs of the Iranian intranet into a DataFrame

    Args:
        xls_path (str): Path to XLS file

    Returns:
        DataFrame: DataFrame containing CIDR of the Iranian intranet.
    """
    ito_df = pd.DataFrame()
    with open(xls_path) as xml_file:
        soup = BeautifulSoup(xml_file.read(), "html.parser")
        ito_df = pd.read_html(soup.decode_contents())[0]

    ito_df = ito_df[["IPv4"]]
    ito_df = ito_df.rename(columns={"IPv4": "Network"})
    ito_df["Country"] = "IR"

    return ito_df


def main():
    export_dir_path = "./Aggregated_Data"
    data_dir_path = "./Data"
    geolite2_db_dir = f"{data_dir_path}/GeoLite2"
    autonomous_systems_db_dir = f"{data_dir_path}/AS_CIDRs"
    dbip_filename = "dbip-country-lite-2023-01.csv"
    ito_excel_filename = "Export-14011020215714.xls"
    geolocations = [
        {"name": "Iran", "iso_code": "IR"},
        {"name": "China", "iso_code": "CN"},
        {"name": "Russia", "iso_code": "RU"},
    ]
    aggregated_ipv4_df = pd.DataFrame(columns=["Network", "Country"])
    aggregated_ipv6_df = pd.DataFrame(columns=["Network", "Country"])
    aggregated_df = pd.DataFrame(columns=["Network", "Country"])

    if os.path.exists(data_dir_path):
        for geolocation in geolocations:
            print(f"\nAggregating data for {geolocation['name']}")

            # Load DBIP database
            print("Loading DBIP database")
            dbip_ipv4, dbip_ipv6 = load_dbip_csv(
                file_path=f"{data_dir_path}/{dbip_filename}",
                country_iso_code=geolocation["iso_code"],
            )
            # Convert IP range to CIDR
            dbip_ipv4 = convert_iprange_to_cidr(dbip_ipv4, ipv6=False)
            dbip_ipv6 = convert_iprange_to_cidr(dbip_ipv6, ipv6=True)

            print(f"IPv4 entries found: {len(dbip_ipv4)}")
            print(f"IPv6 entries found: {len(dbip_ipv6)}")

            # Load MaxMind GeoLite2 database
            print("Loading MaxMind GeoLite2 database")
            geolite2_ipv4_df, geolite2_ipv6_df = load_geolite2_csv(
                dir_path=geolite2_db_dir, geolocation=geolocation
            )

            print(f"IPv4 entries found: {len(geolite2_ipv4_df)}")
            print(f"IPv6 entries found: {len(geolite2_ipv6_df)}")

            # Load and concat autonomous systems CIDRs CSVs
            print("Loading autonomous systems CIDR database")
            for ipv4_file in glob.iglob(f"{autonomous_systems_db_dir}/ipv4_*.csv"):
                geolocation_autonomous_systems_df = pd.read_csv(ipv4_file)
                aggregated_ipv4_df = pd.concat(
                    [aggregated_ipv4_df, geolocation_autonomous_systems_df],
                    ignore_index=True,
                )

            for ipv6_file in glob.iglob(f"{autonomous_systems_db_dir}/ipv6_*.csv"):
                geolocation_autonomous_systems_df = pd.read_csv(ipv6_file)
                aggregated_ipv6_df = pd.concat(
                    [aggregated_ipv6_df, geolocation_autonomous_systems_df],
                    ignore_index=True,
                )

            print(f"IPv4 entries found: {len(aggregated_ipv4_df)}")
            print(f"IPv6 entries found: {len(aggregated_ipv6_df)}")

            # Load ITO database
            if geolocation["iso_code"] == "IR":
                print("Loading ITO database")
                ito_df = read_ito_db(f"{data_dir_path}/{ito_excel_filename}")
                aggregated_ipv4_df = pd.concat(
                    [aggregated_ipv4_df, ito_df], ignore_index=True
                )
                print(f"IPv4 entries found: {len(ito_df)}")

            # Concat all of the loaded CSVs
            print("Concatenating databases into one")
            aggregated_ipv4_df = pd.concat(
                [aggregated_ipv4_df, geolite2_ipv4_df], ignore_index=True
            )
            aggregated_ipv6_df = pd.concat(
                [aggregated_ipv6_df, geolite2_ipv6_df], ignore_index=True
            )

            print(f"Total raw IPv4 entries: {len(aggregated_ipv4_df)}")
            print(f"Total raw IPv6 entries: {len(aggregated_ipv6_df)}")

            # Remove duplicates
            print("Cleaning up")
            aggregated_ipv4_df = aggregated_ipv4_df.drop_duplicates()
            aggregated_ipv6_df = aggregated_ipv6_df.drop_duplicates()

            print(f"Total unique IPv4 entries: {len(aggregated_ipv4_df)}")
            print(f"Total unique IPv6 entries: {len(aggregated_ipv6_df)}")

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
