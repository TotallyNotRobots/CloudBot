from unittest.mock import MagicMock

import pytest

from plugins import mylife


@pytest.mark.asyncio()
async def test_mylife(mock_requests, event_loop):
    mock_requests.add(
        "GET",
        "http://www.fmylife.com/random",
        body="""\
<!DOCTYPE html>
<html lang="us">
<body>
<main id="main">
<div class="container site-content">
<div id="content">
<div class="row flex-block">
<div class="col-sm-8">
<div class="row">
<article class="col-xs-12 article-panel">
<div class="panel panel-classic">
<div class="article-contents">
<a class="article-link" href="/article/today-foo_155676.html">
<span class="icon-piment"></span>&nbsp;
Today, foo fml
</a>
</div>
</div>
</article>
<article class="col-xs-12 article-panel">
<div class="panel panel-classic">
<div class="article-contents">
<a class="article-link" href="/article/today-bar_132473.html">
<span class="icon-piment"></span>&nbsp;
Today, bar fml
</a>
</div>
</div>
</article>
<article class="col-xs-12 article-panel">
<div class="panel panel-classic">
<div class="article-contents">
<a class="article-link" href="/article/today-bar_132473.html">
<span class="icon-piment"></span>&nbsp;
Today, bar aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
aaaaaaaaaa fml
</a>
</div>
</div>
</article>
<article class="col-xs-12 article-panel">
<div class="panel panel-classic">
<div class="article-contents">
<a class="article-link" href="/article/today-bar_132473.html">
<span class="icon-piment"></span>&nbsp;
Today, bar
</a>
</div>
</div>
</article>
<article class="col-xs-12 article-panel">
<div class="panel panel-classic">
<div class="article-contents">
<a class="article-link" href="/article/news_142303.html">
some news
</a>
</div>
</div>
</article>
</div>
</div>
</div>
</div>
</main>
</body>
</html>""",
    )
    reply = MagicMock()
    res = await mylife.fml(reply, event_loop)
    assert res is None
    reply.assert_called_with("(#132473) Today, bar fml")
