import ipaddress
from functools import partial
from multiprocessing import Pool, cpu_count

import pandas as pd


def concat_df(dst_df: pd.DataFrame, src_df: pd.DataFrame):
    dst_df = pd.concat(
        [dst_df, src_df],
        ignore_index=True,
    )
    return dst_df


def expand_cidr_range(df: pd.DataFrame):
    """
    Takes a DataFrame containing IPv4 CIDRs,
    finds duplicate networks but with different subnets,
    throws away the less expansive ones (higher subnet numbers) and
    converts all single-IP entries to /24 subnet

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
        if "." in item["IP"] and 25 <= item["Subnet"] <= 32:
            octets_arr = item["IP"].split(".")
            octets_arr[3] = "0"
            item["IP"] = ".".join(octets_arr)
            item["Subnet"] = 24
        extensive_list.append(
            {"IP": item["IP"], "Subnet": item["Subnet"], "Tag": item["Tag"]}
        )

    # Remove any duplicates resulting from above operations
    print("-> Dropping duplicate networks but with higher subnets")
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


def convert_iprange_to_cidr(df: pd.DataFrame, ipv6=False):
    """
    Converts IP ranges to CIDR format y.y.y.y/X

    Args:
        df (pd.DataFrame): DataFrame containing IP range data
        ipv6 (bool, optional): Whether IPv6 address format is wanted
        or IPv4. Defaults to False.

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


def extract_to_ipv4_ipv6(df):
    """Filters a DataFrame of IP addresses by IP type.

    Args:
      df: A DataFrame containing IP addresses.
      ip_type: A string representing the IP type to filter for, either "ipv4" or "ipv6".

    Returns:
      A DataFrame containing the filtered IP addresses.
    """

    ipv4 = []
    ipv6 = []
    for index, row in df.iterrows():
        ip_address = row['Network']

        if ":" in ip_address:
            ipv6.append(row)
        elif "." in ip_address:
            ipv4.append(row)

    ipv4 = pd.DataFrame(ipv4, columns=["Network", "Tag"])
    ipv6 = pd.DataFrame(ipv6, columns=["Network", "Tag"])

    return ipv4, ipv6

def _cleanup_duplicates_and_subnets(df):
    """Removes duplicate CIDR addresses from a DataFrame and removes CIDR addresses that are subnets of an existing CIDR address.

    Args:
      df: A DataFrame containing network CIDR addresses.

    Returns:
      A DataFrame containing the unique CIDR addresses, where no CIDR address is a subnet of another CIDR address.
    """

    # Sort the DataFrame by CIDR address.
    df = df.sort_values(by=['Network'])

    # Iterate over the DataFrame and compare each CIDR address to the previous one.
    previous_cidr_address = None
    to_drop = []
    for index, row in df.iterrows():
        cidr_address = row['Network']

        # If the current CIDR address is the same as the previous CIDR address,
        # or if the current CIDR address is a subnet of the previous CIDR address,
        # remove the current entry.
        if previous_cidr_address and (
                cidr_address.compare_networks(previous_cidr_address) == 0 or cidr_address.subnet_of(
            previous_cidr_address)):
            to_drop.append(index)

        previous_cidr_address = cidr_address

    # Drop the duplicate and subnet CIDR addresses.
    df = df.drop(to_drop)

    return df


def _preprocess_for_cleaning(df: pd.DataFrame):
    # Convert CIDR strings to IPNetwork objects
    df["Network"] = df["Network"].apply(partial(ipaddress.ip_network, strict=False))

    # Filter for IPv4 and IPv6
    df_v4 = df[df["Network"].apply(lambda x: x.version == 4)]
    df_v6 = df[df["Network"].apply(lambda x: x.version == 6)]

    df_v4 = _cleanup_duplicates_and_subnets(df_v4)
    df_v6 = _cleanup_duplicates_and_subnets(df_v6)

    # Concatenate results
    df = pd.concat([df_v4, df_v6])
    df["Network"] = df["Network"].astype(str)
    return df


def cleanup_cidrs(cidr_df: pd.DataFrame):
    print(
        "\n*** Starting to remove redundant CIDRs ***"
    )
    print(
        "-> Splitting the dataset into smaller chunks based on their tags for parallel processing"
    )
    chunks = [
        chunk.sort_values("Network", ascending=False)
        for _, chunk in cidr_df.groupby("Tag")
    ]

    # Create a Pool of workers and process the chunks in parallel
    print(f"-> Processing {len(chunks)} chunks in parallel, this will take a while...")
    num_workers = cpu_count() - 1  # Get the number of CPU cores

    with Pool(processes=num_workers) as pool:
        cleaned_chunks = pool.map(_preprocess_for_cleaning, chunks)

    print("-> Concatenating the DataFrames...")
    return pd.concat(cleaned_chunks, axis=0, ignore_index=True).sort_values(
        by=["Tag", "Network"]
    )


def calculate_ip_stats(df: pd.DataFrame) -> list[dict]:
    """
    Calculates how many IPs are covered for each country (tag)

    Args:
        df (pd.DataFrame): CIDR DataFrame

    Returns:
        list[dict]: List of dictionaries containing stats
    """
    unique_tags = df["Tag"].unique().tolist()
    stats = []

    for tag in unique_tags:
        tagged_df = df[df["Tag"] == tag]
        total_ipv4s = 0
        total_ipv6s = 0
        for _, row in tagged_df.iterrows():
            cidr = row["Network"]
            try:
                network = ipaddress.IPv4Network(cidr, strict=False)
                total_ipv4s += network.num_addresses
            except ipaddress.AddressValueError:
                try:
                    network = ipaddress.IPv6Network(cidr, strict=False)
                    total_ipv6s += network.num_addresses
                except ipaddress.AddressValueError:
                    # Invalid CIDR, pass
                    pass
        stats.append(
            {"tag": tag, "total_ipv4s": total_ipv4s, "total_ipv6s": total_ipv6s}
        )

    return stats


def pretty_print_stats(stats):
    if stats:
        for item in stats:
            print(
                f"""Total IP numbers included for {item['tag']}
IPv4: {'{:,}'.format(item['total_ipv4s'])} IPs
IPv6: {item['total_ipv6s']:.2e} IPs
"""
            )
