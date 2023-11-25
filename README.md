# Introduction

This is a collaborative effort to gather an aggregated database of GeoIPs registered in Iran, China and also common IPs belonging to widely-used services. This helps users to implement ACLs on their VPN clients or cloud servers to aid in routing decisions, content blocking, and probing protection.

The repository offers two types of datasets targeting different use-cases, the `agg_cidrs.csv` dataset is intended for utilization on cloud servers (`xtables` module on Linux) and is currently used in `Rainb0w` proxy installers available on [RedPillLabs](https://github.com/redpilllabs) repositories page, while `.dat` datasets are intended for use on v2ray/xray and `.db` datasets are intended for sing-box compatible clients.

The `agg_cidrs.csv` dataset currently offers the following networks: `[IR, CN, CF (Cloudflare)]`.

The `geoip.dat` dataset currently offers the following networks: `[ir, cn, cloudflare, google, amazon, microsoft, github, facebook, twitter, telegram]` while the `geoip.db` only offers country tags available in GeoLite2 database.

The `geosite.dat` and `geosite.db` datasets currently offer the following networks:

```
- category-ads-all -> Aggregated list of domains used for advertising
- category-porn -> Aggregated list of domains hosting NSFW content
- cn -> Aggregated list of Chinese domains plus regex rule for the [.cn] ccTLD
- ir -> Aggregated list of Iranian domains plus regex rule for the [.ir] ccTLD
- embargo -> Websites that have banned Iranian IPs (403 error)
- github -> Domains belonging to GitHub
- cloudflare -> Domains belonging to Cloudflare
- youtube -> Domains belonging to YouTube
```

# Download

## Xray/v2ray core

`GeoIP` [https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geoip.dat](https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geoip.dat)

`GeoSite` [https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geosite.dat](https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geosite.dat)

## Sing-Box core

`GeoIP` [https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geoip.db](https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geoip.db)

`GeoSite` [https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geosite.db](https://github.com/redpilllabs/GFIGeoIP/releases/latest/download/geosite.db)

# How do I use it?

The following is a lean example of v2ray/xray client configuration:

```
"outbounds": [
  {
    "tag": "direct",
    "protocol": "freedom",
    "settings": {}
  },
  {
    "tag": "block",
    "protocol": "blackhole",
    "settings": {}
  }
],
"routing": {
  "domainStrategy": "IPIfNonMatch",
  "rules": [
    {
      "outboundTag": "block",
      "domain": [
        "geosite:category-ads-all"
      ],
      "type": "field"
    },
    {
      "outboundTag": "direct",
      "ip": [
        "geoip:private",
        "geoip:ir",
        "geosite:ir"
      ],
      "type": "field"
    }
  ]
}
```

# What sources are used for aggregation?

Data are pulled from multiple sources such as DBIP, MaxMind Geolite2, ITO, and manually inspected networks.

# Credits

- All maintainers and contributors to the project.
- [MaxMind GeoLite2 ®](https://maxmind.com)
- [DB-IP](https://db-ip.com)
- [Project V](https://github.com/v2fly)
