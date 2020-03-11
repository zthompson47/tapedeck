from pprint import pformat

def pprint(content):
    return pformat(
        content, indent=0, compact=True, sort_dicts=False, width=60
    )

def pprint_tellActive(content):
    result = ""
    for torrent in content["result"]:
        if result:
            result += "\n"
        result += torrent["gid"] + " "
        result += str(
            int(torrent["completedLength"]) /
            int(torrent["totalLength"])
        ) + " "
        result += torrent["bittorrent"]["info"]["name"]
    return result

def pprint_etree(rss):
    result = ""
    if rss:
        for entry in rss["entries"]:
            result += entry["title"] + "\n"
            result += entry["links"][0]["href"] + "\n"
            result += "--"
    return result

def passthru(x):
    return x

def decode(x):
    return x.decode("utf-8")

FMT_ETREE = {
    "_default": pprint_etree,
}

FMT_ARIA2 = {
    "tellActive": pprint_tellActive,
    "_default": pprint,
}

FMT_MPD = {
    "_default": passthru,
}

FMT_PULSE = {
    "_default": decode,
}
