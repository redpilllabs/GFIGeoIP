
import ipaddress

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
    return pd.DataFrame(cidr_list)
