#!/usr/bin/env python3
#
#   DuckDuckGo Search Results API
#
from sys import argv
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = "Mozilla/5.0"

# Extrapolate matching information should the format of the site change.
match = {
    # Main search results body identifier.
    "searchResults": {"id": "links"},
    # Individual search results identifier.
    "result": {"class": "links_main links_deep result__body"},
    # Link and description identifier.
    "link": {"class": "result__snippet"},
}

# Plain HTML Search URL.
searchURL = "https://html.duckduckgo.com/html/?q="


def request(url, headers=None):
    # Form request for url.
    request = Request(url)

    # Add headers if supplied, or defaults.
    if headers:
        # Supplied headers.
        for header in headers:
            request.add_header(header, headers[header])
    else:
        # Default headers.
        request.add_header("User-Agent", DEFAULT_USER_AGENT)

    try:
        response = urlopen(request)
    except HTTPError as e:
        # e.code, HTTP Error code.
        #   404
        # e.msg, HTTP Error message.
        #   Not Found
        # e.hdr, HTTP Response headers.
        #   Content-Type: text/html; charset=UTF-8
        #   Referrer-Policy: no-referrer
        #   Content-Length: 1567
        #   Date: Thu, 01 Apr 2021 04:31:31 GMT
        #   Connection: close
        # e.fp, pointer to the http.client.HTTPResponse object.
        code = e.code  # HTTPError code
        error = e.msg  # HTTPError message
        headers = e.hdr  # HTTPError headers
        response = e.fp  # HTTPResponse object
        return e

    # Set HTTPResponse status code.
    code = response.status

    # Set error to None, to know we succeeded in making request
    error = None

    # Set HTTPResponse headers.
    headers = dict(response.getheaders())

    if url != response.url:
        redirect = True

    return response


def makeSoup(html):
    try:
        soup = BeautifulSoup(html, "lxml")
        return soup
    except Exception as e:
        print(e)
        return ""


def parseLink(link):
    url = urlparse(link)
    link = unquote(url.query[5:])
    return link


def search(query):
    # Quote the query string.
    query = quote("".join(query))

    # Make search request.
    response = request(f"{searchURL}{query}")

    # Parse response html.
    soup = makeSoup(response)

    # Select the <div id='links'>.
    searchResults = soup.find("div", match["searchResults"])

    # Parse out each search result from the <div id='links'>
    searchResults = searchResults.find_all("div", match["result"])

    results = []
    # Parse descritpion, link from the searchResults list.
    for result in searchResults:
        anch = result.find("a", match["link"])
        desc = anch.text
        link = parseLink(anch["href"])
        url = urlparse(link)
        if "duckduckgo.com" in url.netloc:
            continue
        results.append({"text": desc, "url": link})

    return results


if __name__ == "__main__":
    results = search(argv[1:])
    for result in results:
        print(result["text"])
        print(result["url"])
        print("---")
