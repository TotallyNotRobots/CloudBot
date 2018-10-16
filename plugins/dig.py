import requests

from cloudbot import hook


@hook.command
def dig(text, nick, notice):
    """<domain> <recordtype> - returns a list of records for the specified domain valid record types are A, NS, TXT, and MX. If a record type is not chosen A will be the default."""
    args = text.split()
    domain = args.pop(0)

    if args:
        rtype = args.pop(0).upper()
    else:
        rtype = "A"

    if rtype not in ("A", "NS", "MX", "TXT"):
        rtype = "A"

    url = "http://dig.jsondns.org/IN/{}/{}".format(domain, rtype)
    r = requests.get(url)
    r.raise_for_status()
    results = r.json()
    if results['header']['rcode'] == "NXDOMAIN":
        return "no dns record for {} was found".format(domain)
    notice("The following records were found for \x02{}\x02: ".format(domain), nick)
    for r in range(len(results['answer'])):
        domain = results['answer'][r]['name']
        rtype = results['answer'][r]['type']
        ttl = results['answer'][r]['ttl']
        if rtype == "MX":
            rdata = results['answer'][r]['rdata'][1]
        elif rtype == "TXT":
            rdata = results['answer'][r]['rdata'][0]
        else:
            rdata = results['answer'][r]['rdata']
        notice("name: \x02{}\x02 type: \x02{}\x02 ttl: \x02{}\x02 rdata: \x02{}\x02".format(
            domain, rtype, ttl, rdata), nick)
