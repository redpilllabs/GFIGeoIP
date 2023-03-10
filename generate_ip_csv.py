#!/usr/bin/env python

# This product includes GeoLite2 Data created by MaxMind, available from https://www.maxmind.com/
# Usage is subject to EULA available from https://www.maxmind.com/en/geolite2/eula


import ipaddress
import os
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


def get_ip_list_txt(url: str):
    ip_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    data = response.content.decode()
    for entry in data.split():
        ip_list.append(entry)
    return ip_list


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
            cidr_list.append({"Network": item.__str__(), "Tag": row["Tag"]})

    return pd.DataFrame(cidr_list)


def load_dbip_csv(file_path: str, tag: str):
    """
    Reads CSV file from DBIP

    Args:
        file_path (str): Path to CSV file.
        tag (str): Country code in ISO to extract rows of.

    Returns:
        DataFrame: Two DataFrames containing IPv4 and IPv6 data
    """
    df = pd.read_csv(file_path, names=["Range_Start", "Range_End", "Tag"])
    df = df.loc[df["Tag"].isin([tag])]
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


def extract_geolite2_cidr(geolite2_ipblocks_csv: str, geoid: int, tag: str):
    """
    Extracts CIDR data from the 'GeoLite2-Country-Blocks-IPv*.csv' files

    Args:
        geolite2_ipblocks_csv (str): Path to 'GeoLite2-Country-Blocks-IPv*.csv'
        geoid (int): GeoID of the CIDRs to extract
        tag (str): Country ISO code to append at the end

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
    extracted_df["Tag"] = tag
    return extracted_df


def load_geolite2_csv(dir_path: str, geolocation: dict):
    geo_id = extract_geo_id(
        f"{dir_path}/GeoLite2-Country-Locations-en.csv", country=geolocation["name"]
    )
    ipv4_df = extract_geolite2_cidr(
        f"{dir_path}/GeoLite2-Country-Blocks-IPv4.csv",
        geoid=geo_id,
        tag=geolocation["tag"],
    )
    ipv6_df = extract_geolite2_cidr(
        f"{dir_path}/GeoLite2-Country-Blocks-IPv6.csv",
        geoid=geo_id,
        tag=geolocation["tag"],
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

    # Websites' DB and messengers' DB have different column names! Typical IR!
    if "IP" in ito_df.columns:
        ito_df = ito_df.rename(columns={"IP": "Network"})
    elif "IPv4" in ito_df.columns:
        ito_df = ito_df.rename(columns={"IPv4": "Network"})

    ito_df = ito_df[["Network"]]
    ito_df["Tag"] = "IR"

    return ito_df


def concat_df(dst_df: pd.DataFrame, src_df: pd.DataFrame):
    dst_df = pd.concat(
        [dst_df, src_df],
        ignore_index=True,
    )
    return dst_df


def expand_df(df: pd.DataFrame):
    """
    Takes a DataFrame containing IPv4 CIDRs, finds duplicate networks but with different subnets,
    throws away the less expansive ones (higher subnet numbers) and converts all single-IP entries to /24 subnet

    Args:
        df (pd.DataFrame): IPv4 DataFrame

    Returns:
        pd.DataFrame: Expanded DataFrame
    """
    # Separate the subnet notation from the IP
    split_list = []
    for row in zip(df["Network"], df["Tag"]):
        ip_arr = str(row[0]).split("/")
        ip_addr = ip_arr[0]
        ip_subnet = ip_arr[1]
        split_list.append({"IP": ip_addr, "Subnet": int(ip_subnet), "Tag": row[1]})

    # Convert all single IPv4s to their last octet's max range
    print("-> Converting smaller subnets to /24 to cover the whole C class network")
    extensive_list = []
    for item in split_list:
        if "." in item["IP"] and item["Subnet"] >= 25 and item["Subnet"] <= 32:
            octets_arr = item["IP"].split(".")
            octets_arr[3] = "0"
            item["IP"] = ".".join(octets_arr)
            item["Subnet"] = 24
        extensive_list.append(
            {"IP": item["IP"], "Subnet": item["Subnet"], "Tag": item["Tag"]}
        )

    # Remove any duplicates resulting from above operations
    print("-> Dropping duplicate IPs but with higher subnets")
    tmp_df = pd.DataFrame(extensive_list)
    tmp_df = tmp_df.sort_values("Subnet", ascending=True)
    tmp_df = tmp_df.drop_duplicates(subset=["IP"])

    result_list = []
    for row in zip(tmp_df["IP"], tmp_df["Subnet"], tmp_df["Tag"]):
        cidr = f"{row[0]}/{row[1]}"
        result_list.append({"Network": cidr, "Tag": row[2]})
    result_df = pd.DataFrame(result_list)
    result_df = result_df.sort_values("Tag").reset_index(drop=True)

    return result_df


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
    geolocations = [
        {"name": "Iran", "tag": "IR"},
        {"name": "China", "tag": "CN"},
        {"name": "Russia", "tag": "RU"},
    ]
    contents = [
        {"name": "Pornography", "tag": "XX"},
        {"name": "Social Media", "tag": "YY"},
    ]

    # First off append the Cloudflare network IPs
    cf_ipv4_list = get_ip_list_txt("https://www.cloudflare.com/ips-v4")
    if cf_ipv4_list:
        cf_ipv4_df = pd.DataFrame(cf_ipv4_list, columns=["Network"])
        cf_ipv4_df["Tag"] = "CF"
        aggregated_ipv4_df = concat_df(aggregated_ipv4_df, cf_ipv4_df)

    cf_ipv6_list = get_ip_list_txt("https://www.cloudflare.com/ips-v6")
    if cf_ipv6_list:
        cf_ipv6_df = pd.DataFrame(cf_ipv6_list, columns=["Network"])
        cf_ipv6_df["Tag"] = "CF"
        aggregated_ipv6_df = concat_df(aggregated_ipv6_df, cf_ipv6_df)

    # Append ArvanCloud network as IR
    ac_ipv4_list = get_ip_list_txt("https://www.arvancloud.ir/fa/ips.txt")
    if ac_ipv4_list:
        ac_ipv4_df = pd.DataFrame(ac_ipv4_list, columns=["Network"])
        ac_ipv4_df["Tag"] = "IR"
        aggregated_ipv4_df = concat_df(aggregated_ipv4_df, ac_ipv4_df)

    if os.path.exists(data_dir_path):
        for geolocation in geolocations:
            print(f"\n\n*** Aggregating data for {geolocation['name']} ***")

            # Load DBIP database
            print("\nLoading DBIP database")
            dbip_ipv4, dbip_ipv6 = load_dbip_csv(
                file_path=f"{data_dir_path}/{dbip_filename}",
                tag=geolocation["tag"],
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
                dir_path=geolite2_db_dir, geolocation=geolocation
            )

            print(f"IPv4 entries found: {len(geolite2_ipv4_df)}")
            print(f"IPv6 entries found: {len(geolite2_ipv6_df)}")

            # Add to aggregated DataFrame
            aggregated_ipv4_df = concat_df(aggregated_ipv4_df, geolite2_ipv4_df)
            aggregated_ipv6_df = concat_df(aggregated_ipv6_df, geolite2_ipv6_df)

            # Load and concat autonomous systems CIDRs CSVs
            print("\nLoading autonomous systems CIDR database")
            if Path(
                f"{autonomous_systems_db_dir}/ipv4_{geolocation['tag']}.csv"
            ).is_file():
                as_ipv4_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv4_{geolocation['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(as_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, as_ipv4_df)

            if Path(
                f"{autonomous_systems_db_dir}/ipv6_{geolocation['tag']}.csv"
            ).is_file():
                as_ipv6_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv6_{geolocation['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(as_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, as_ipv6_df)

            # Load manually found CIDRs if available
            print("\nLoading manually found CIDR database")
            if Path(f"{manual_db_dir}/ipv4_{geolocation['tag']}.csv").is_file():
                manual_ipv4_df = pd.read_csv(
                    f"{manual_db_dir}/ipv4_{geolocation['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(manual_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, manual_ipv4_df)

            if Path(f"{manual_db_dir}/ipv6_{geolocation['tag']}.csv").is_file():
                manual_ipv6_df = pd.read_csv(
                    f"{manual_db_dir}/ipv6_{geolocation['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(manual_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, manual_ipv6_df)

            # Load ITO database
            if geolocation["tag"] == "IR":
                print("\nLoading ITO website database")
                ito_df = read_ito_db(f"{data_dir_path}/{ito_website_excel_filename}")
                print(f"IPv4 entries found: {len(ito_df)}")
                aggregated_ipv4_df = pd.concat(
                    [aggregated_ipv4_df, ito_df], ignore_index=True
                )

                print("\nLoading ITO instant messengers database")
                ito_df = read_ito_db(f"{data_dir_path}/{ito_im_excel_filename}")
                print(f"IPv4 entries found: {len(ito_df)}")
                aggregated_ipv4_df = pd.concat(
                    [aggregated_ipv4_df, ito_df], ignore_index=True
                )

        # Content-based aggregation
        for content in contents:
            print(f"\n\n*** Aggregating data for {content['name']} ***")

            # Load and concat autonomous systems CIDRs CSVs
            print("\nLoading autonomous systems CIDR database")
            if Path(f"{autonomous_systems_db_dir}/ipv4_{content['tag']}.csv").is_file():
                as_ipv4_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv4_{content['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(as_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, as_ipv4_df)

            if Path(f"{autonomous_systems_db_dir}/ipv6_{content['tag']}.csv").is_file():
                as_ipv6_df = pd.read_csv(
                    f"{autonomous_systems_db_dir}/ipv6_{content['tag']}.csv"
                )
                print(f"IPv6 entries found: {len(as_ipv6_df)}")
                aggregated_ipv6_df = concat_df(aggregated_ipv6_df, as_ipv6_df)

            # Load manually found CIDRs if available
            print("\nLoading manually found CIDR database")
            if Path(f"{manual_db_dir}/ipv4_{content['tag']}.csv").is_file():
                manual_ipv4_df = pd.read_csv(
                    f"{manual_db_dir}/ipv4_{content['tag']}.csv"
                )
                print(f"IPv4 entries found: {len(manual_ipv4_df)}")
                aggregated_ipv4_df = concat_df(aggregated_ipv4_df, manual_ipv4_df)

            if Path(f"{manual_db_dir}/ipv6_{content['tag']}.csv").is_file():
                manual_ipv6_df = pd.read_csv(
                    f"{manual_db_dir}/ipv6_{content['tag']}.csv"
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

        aggregated_ipv4_df = expand_df(aggregated_ipv4_df)

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
