import pandas as pd
from bs4 import BeautifulSoup


def convert_xls_to_df(xls_path: str):
    """
    Loads Excel sheet from ITO, extracts the CIDRs of
    the Iranian intranet into a DataFrame

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
