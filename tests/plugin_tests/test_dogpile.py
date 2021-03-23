from pathlib import Path

import pytest

from plugins import dogpile


@pytest.fixture(scope="module")
def test_data():
    data = {}
    for file in Path("tests/data/").resolve().rglob("dogpile-*.html"):
        name = file.stem.split("-", 1)[1]
        with file.open("rb") as f:
            data[name] = f.read()

    yield data


def add_page(mock_requests, endpoint, test_data):
    data = test_data[endpoint]
    mock_requests.add(
        "GET",
        "https://www.dogpile.com/search/" + endpoint,
        body=data,
    )


def test_web_search(test_data, mock_requests):
    add_page(mock_requests, "web", test_data)
    assert (
        dogpile.dogpile("test search")
        == "https://search.google.com/test/mobile-friendly -- "
        "\x02Test how easily a visitor can use your page on a mobile device. "
        "Just enter a page URL to see how your page scores. "
        "... Google apps. Main menu Mobile-Friendly Test ... "
        "Search Console alerts you about critical site errors such as "
        "detection of hacked content, and helps you manage how your content "
        "appears in search results.\x02"
    )

    mock_requests.replace(
        "GET",
        "https://www.dogpile.com/search/web",
        body="",
    )

    assert dogpile.dogpile("test search") == "No results found."


def test_image_search(test_data, mock_requests):
    add_page(mock_requests, "images", test_data)

    assert dogpile.dogpileimage("test search") in [
        "http://www.opentestsearch.com/files/2012/04/Searchdaimon_admin_4.png",
        "https://avaldes.com/wp-content/uploads/2014/03/test_search_xml.png?2d262d&2d262d",
        "http://solospark.com/wp-content/uploads/2013/11/google.seo_.search.testing.infographic.png",
        "http://searchengineland.com/figz/wp-content/seloads/2014/04/bing-test-design.png",
        "https://searchengineland.com/figz/wp-content/seloads/2015/01/yahoo-search-google-interface-1421673260-800x460.png",
        "https://avaldes.com/wp-content/uploads/2014/03/test_search_json.png?x43424",
        "http://intranetdiary.co.uk/wp-content/uploads/2013/03/Search-results-for-get-an-eye-test-culture-hub.png",
        "http://searchengineland.com/figz/wp-content/seloads/2016/05/google-mobile-friendly-test-tool-new.png",
        "http://www.opentestsearch.com/files/2012/09/Google-site-search-admin-31.png",
        "http://www.saadkamal.com/wp-content/uploads/2009/03/microsoft-kumo-search-engine.png",
        "https://content.lessonplanet.com/resources/previews/original/bacteria-test-word-search-puzzle-worksheet.jpg?1414269464",
        "http://www.maven-infosoft.com/wp-content/uploads/2016/05/Search-Console-Mobile-Friendly-Test.png",
        "http://searchengineland.com/figz/wp-content/seloads/2017/04/google-jobs-answer.jpg",
        "https://cdn.vox-cdn.com/thumbor/ZjEhxzbS9SyQYPP56vUiUXAwoLo=/207x0:891x456/1200x800/filters:focal(207x0:891x456)/cdn.vox-cdn.com/uploads/chorus_image/image/49980909/google-search-internet-speed-test.0.0.jpg",
        "http://www.androidpolice.com/wp-content/uploads/2017/07/nexus2cee_google-search-test-rounded-cards-layout-new-6.png",
        "https://searchengineland.com/figz/wp-content/seloads/2017/12/rich-results-google-testing-tool.png",
        "http://www.cctvcamerapros.com/v/images/test-monitor/cable-search/IP-Camera-Monitor-Cable-Tester.jpg",
        "http://www.androidpolice.com/wp-content/uploads/2017/07/nexus2cee_google-search-test-rounded-cards-layout-old-2.png",
        "http://images.fonearena.com/blog/wp-content/uploads/2016/07/google-search-speed-test-4.png",
        "https://marketplace-cdn.atlassian.com/files/images/b3d56053-21c0-4d1b-bd4b-54ccb2093acc.png",
        "http://dustn.tv/wp-content/uploads/2016/06/08-successful-search-test.jpg",
        "http://2.bp.blogspot.com/-0J2qyCHOxPM/U21ZWYc5tHI/AAAAAAAAJaQ/eEa1q4Yjp9c/s1600/Minecraft+Crossword+Free+Printable+.jpg",
        "https://fossbytes.com/wp-content/uploads/2017/08/Google-Search-Speed-test-Main3.png",
        "https://9to5google.files.wordpress.com/2016/05/google-search-ab-test-11.png",
        "https://cyberbloc.de/wp-content/uploads/2013/01/Facebook_Graph_Search_test_081.jpg",
        "https://searchengineland.com/figz/wp-content/seloads/2015/08/google-online-appointment-booking-intuit-landing-page.png",
        "http://www.androidpolice.com/wp-content/uploads/2017/07/nexus2cee_google-search-test-rounded-cards-layout-old-4.png",
        "http://www.cctvcamerapros.com/v/images/test-monitor/cable-search/IP-Camera-Test-Monitor-Cable.jpg",
        "https://jungsuwonkidsclub.files.wordpress.com/2008/11/testing-word-search.jpg",
        "https://justaucguy.files.wordpress.com/2014/12/test-exchangesearch-fl.jpg",
        "https://s3.amazonaws.com/images.seroundtable.com/google-image-search-new-interface-1358516501.jpg",
        "https://i.pinimg.com/736x/24/2d/02/242d029a84185ba7709bc019b36b0fd6--genealogy-dna-test-genealogy-search.jpg",
        "http://slideplayer.com/9460680/29/images/6/Use+the+filters+to+find+questions+for+your+test.jpg",
        "https://marketplace-cdn.atlassian.com/files/images/8de36cd1-c798-4592-8a94-4cb2922188a9.jpeg",
        "https://cdn0.tnwcdn.com/wp-content/blogs.dir/1/files/2016/05/Google_search_test.jpg",
    ]

    mock_requests.replace(
        "GET",
        "https://www.dogpile.com/search/images",
        body="",
    )

    assert dogpile.dogpileimage("test search") == "No results found."

    mock_requests.replace(
        "GET",
        "https://www.dogpile.com/search/images",
        body=test_data["images-empty"],
    )

    assert dogpile.dogpileimage("test search") == "No results found."
