from youtube_search import YoutubeSearch

results = YoutubeSearch("Du hast", max_results=10).to_dict()[0]
print(results)
