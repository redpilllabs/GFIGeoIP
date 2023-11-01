from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup

from lib.cidr_utils import extract_to_ipv4_ipv6


def convert_xls_to_df(xls_path: str):
    """
    Loads an Excel sheet from ito, extracts the CIDRs of
    the Iranian intranet into a DataFrame

    Args:
        xls_path (str): Path to XLS file

    Returns:
        DataFrame: DataFrame containing CIDR of the Iranian intranet.
    """
    with open(xls_path) as xml_file:
        soup = BeautifulSoup(xml_file.read(), "html.parser")
        html_string = soup.decode_contents()
        string_io_object = StringIO(html_string)
        ito_df = pd.read_html(string_io_object)[0]

        # Websites' DB and messengers' DB have different column names. Typical IR!
        if "IP" in ito_df.columns:
            ito_df = ito_df.rename(columns={"IP": "Network"})
        elif "IPv4" in ito_df.columns:
            ito_df = ito_df.rename(columns={"IPv4": "Network"})

        # Drop every column except 'Network'
        ito_df = ito_df[["Network"]]
        ito_df["Tag"] = "IR"

        ipv4, ipv6 = extract_to_ipv4_ipv6(ito_df)

        return ipv4, ipv6
