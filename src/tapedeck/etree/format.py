def pprint_etree(rss):
    result = ""
    if rss:
        for entry in rss["entries"]:
            result += entry["title"] + "\n"
            result += entry["links"][0]["href"] + "\n"
            result += "--\n"
    print(result)

FMT = {
    "_default": pprint_etree,
}
