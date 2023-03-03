#!/usr/bin/env python

import pandas as pd


def main():
    geo_id = 130758
    asn_df = pd.read_csv("./Data_Source/GeoLite2-ASN-Blocks-IPv4.csv")
    cidr_df = pd.read_csv("./Data_Source/GeoLite2-Country-Blocks-IPv4.csv")

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


if __name__ == "__main__":
    main()
