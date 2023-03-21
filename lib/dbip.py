
import pandas as pd


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
