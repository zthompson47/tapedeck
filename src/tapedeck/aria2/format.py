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

FMT = {
    "tellActive": pprint_tellActive,
    "_default": pprint,
}
