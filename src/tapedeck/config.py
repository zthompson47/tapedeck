from prompt_toolkit import HTML

REDIS = dict(host="localhost", port=6379, db=0)

ETREE_RSS_URI = "http://bt.etree.org/rss/bt_etree_org.rdf"
ETREE_RSS_REDIS_KEY = "td.etree.rss"

ARIA2 = "ws://localhost:6800/jsonrpc"
ARIA2_CURIO = ("localhost", 6800)

MPD = ("localhost", 6600)

PULSE = "/var/run/user/1000/pulse/cli"

PS1 = HTML(
    "<blue>⦗</blue>"
    "<yellow>✇</yellow>"
    "<orange>_</orange>"
    "<yellow>✇</yellow>"
    "<blue>⦘</blue>"
    "<orange>{namespace}></orange> "
)
