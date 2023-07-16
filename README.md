# Introduction

This is a collaborative effort to gather an aggregated database of IPs registered in Iran, Russia, and China where the internet censorship system GFW has been deployed. This helps users to implement ACLs on their cloud servers to help protect them from active probing or save bandwidth by content blocking mechanisms.

Currently the aggregated database contains the following:

```
- IR -> Iran
- CN -> China
- RU -> Russia
- CF -> Cloudflare
- XX -> Adult Hosting Websites
```

# How does it work?

Aggregated data are pulled from multiple sources such as DBIP, MaxMind Geolite2, ITO, and manually inspected networks.

# How do I use it?

The aggregated data is available inside `/Aggregated_Data/agg_cidrs.csv` containing networks in CIDR format tagged with the relevant geolocation or content type.

# Collaboration

I welcome any efforts to make the `asn_list.toml` even more comprehensive and complete but in order to protect the data reliability, PRs containing the `agg_cidrs.csv` file will not be accepted, only the `.py` and `asn_list.toml` files are accepted.
