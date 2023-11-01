import pandas as pd


def extract_dbip_ip_versions(dbip_df: pd.DataFrame, tag: str):
    """
    Reads CSV file from DBIP

    Args:
        dbip_df (DataFrame): DataFrame of DBIP database.
        tag (str): Country code in ISO to extract rows of.

    Returns:
        DataFrame: Two DataFrames containing IPv4 and IPv6 data
    """
    dbip_df = dbip_df.loc[dbip_df["Tag"].isin([tag])]
    df_ip4 = dbip_df.loc[~dbip_df["Range_Start"].str.contains(":")]
    df_ip6 = dbip_df.loc[dbip_df["Range_Start"].str.contains(":")]

    return df_ip4, df_ip6
