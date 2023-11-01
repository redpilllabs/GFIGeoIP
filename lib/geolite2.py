import pandas as pd


def get_geolite2_id(geolite2_countries_df: pd.DataFrame, country: str):
    """
    Extracts GeoID of a given country from the 'geolite2-Country-Locations-en.csv'

    Args:
        geolite2_countries_df: DataFrame loaded from 'geolite2-Country-Locations-en.csv' file
        country (str): Country to extract GeoID

    Returns:
        int: GeoID
    """
    geoid = geolite2_countries_df.loc[geolite2_countries_df["country_name"] == country][
        "geoname_id"
    ]
    return int(str(geoid.values[0]))


def extract_geolite2_cidrs(geolite2_ipblocks: pd.DataFrame, geoid: int, tag: str):
    """
    Extracts CIDR data from the 'geolite2-Country-Blocks-IPv*.csv' files

    Args:
        geolite2_ipblocks: DataFrame loaded from 'geolite2-Country-Blocks-IPv*.csv'
        geoid (int): GeoID of the CIDRs to extract
        tag (str): Country ISO code to append at the end

    Returns:
        DataFrame: DataFrame containing CIDR data
    """
    extracted_df = geolite2_ipblocks.loc[
        (geolite2_ipblocks["geoname_id"] == geoid)
        & (geolite2_ipblocks["registered_country_geoname_id"] == geoid)
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


def extract_geo_networks(geo_id: int):
    asn_df = pd.read_csv("./resources/geolite2/GeoLite2-ASN-Blocks-IPv4.csv")
    cidr_df = pd.read_csv("./resources/geolite2/GeoLite2-Country-Blocks-IPv4.csv")

    print("Filtering CIDRs based on Geo ID...")
    cidr_df = cidr_df.loc[
        (cidr_df["geoname_id"].isin([geo_id]))
        & (cidr_df["registered_country_geoname_id"].isin([geo_id]))
    ]
    cidr_df = cidr_df.drop(
        columns=[
            "geoname_id",
            "registered_country_geoname_id",
            "represented_country_geoname_id",
            "is_anonymous_proxy",
            "is_satellite_provider",
        ]
    )

    print("Cross matching autonomous systems with filtered CIDRs...")
    asn_df = asn_df[asn_df["network"].apply(lambda x: x in cidr_df["network"].values)]

    print("Sorting the result based ASNs...")
    asn_df = asn_df.sort_values(by=["autonomous_system_number"])
    print(asn_df.head())

    print("Saving to CSV...")
    asn_df.to_csv("asns.csv")

    print("Finished!")
