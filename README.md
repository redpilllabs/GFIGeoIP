# Introduction

This is a collaborative effort to gather an aggregated database of IPs registered in Iran, Russia, and China where the internet censorship system GFW has been deployed, in addition major social networks and adult websites (not comprehensive) are also aggregated. This helps users to implement ACLs on their cloud servers to help protect them from active probing or save bandwidth by content blocking mechanisms.

# How does it work?

Aggregated data are pulled from multiple sources such as DBIP, MaxMind Geolite2, ITO, and manually inspected networks.

# How do I use it?

The aggregated data is available inside `/Aggregated_Data/agg_cidrs.csv'` containing networks in CIDR format tagged with the relevant geolocation or content type.
