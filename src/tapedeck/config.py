from prompt_toolkit import PromptSession, HTML

RSS_ETREE = "http://bt.etree.org/rss/bt_etree_org.rdf"
ARIA2 = "ws://localhost:6800/jsonrpc"
MPD = ("localhost", 6600)
PULSE = "/var/run/usr/1000/pulse/cli"

PS1 = HTML(
    "<blue>⦗</blue>"
    "<yellow>✇</yellow>"
    "<orange>_</orange>"
    "<yellow>✇</yellow>"
    "<blue>⦘</blue>"
    "<orange>{prefix}></orange> "
)
