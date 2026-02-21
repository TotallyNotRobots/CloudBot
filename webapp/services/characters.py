"""
Curated list of fictional characters for the daily challenge pool.
Categories: movie, book, tv, game, animation, mythology
"""
from __future__ import annotations

import datetime
import random

CHARACTERS: list[dict[str, str]] = [
    # ── Movies ──────────────────────────────────────────────────────────────
    {"name": "Darth Vader", "category": "movie", "origin": "Star Wars"},
    {"name": "Gandalf", "category": "movie/book", "origin": "The Lord of the Rings"},
    {"name": "Hannibal Lecter", "category": "movie", "origin": "The Silence of the Lambs"},
    {"name": "Ellen Ripley", "category": "movie", "origin": "Alien"},
    {"name": "Indiana Jones", "category": "movie", "origin": "Raiders of the Lost Ark"},
    {"name": "The Joker", "category": "movie/comic", "origin": "Batman"},
    {"name": "Tony Stark / Iron Man", "category": "movie/comic", "origin": "Marvel"},
    {"name": "Hermione Granger", "category": "book/movie", "origin": "Harry Potter"},
    {"name": "Atticus Finch", "category": "book/movie", "origin": "To Kill a Mockingbird"},
    {"name": "Tyler Durden", "category": "movie", "origin": "Fight Club"},
    {"name": "Forrest Gump", "category": "movie", "origin": "Forrest Gump"},
    {"name": "Jack Sparrow", "category": "movie", "origin": "Pirates of the Caribbean"},
    {"name": "Morpheus", "category": "movie", "origin": "The Matrix"},
    {"name": "Walter White", "category": "tv", "origin": "Breaking Bad"},
    {"name": "Don Corleone", "category": "movie", "origin": "The Godfather"},
    {"name": "Katniss Everdeen", "category": "book/movie", "origin": "The Hunger Games"},
    {"name": "Sherlock Holmes", "category": "book", "origin": "Arthur Conan Doyle"},
    {"name": "Elizabeth Bennet", "category": "book", "origin": "Pride and Prejudice"},
    {"name": "Jay Gatsby", "category": "book", "origin": "The Great Gatsby"},
    {"name": "Holden Caulfield", "category": "book", "origin": "The Catcher in the Rye"},
    # ── TV ──────────────────────────────────────────────────────────────────
    {"name": "Jon Snow", "category": "tv/book", "origin": "Game of Thrones"},
    {"name": "Tyrion Lannister", "category": "tv/book", "origin": "Game of Thrones"},
    {"name": "Tony Soprano", "category": "tv", "origin": "The Sopranos"},
    {"name": "Daenerys Targaryen", "category": "tv/book", "origin": "Game of Thrones"},
    {"name": "Dexter Morgan", "category": "tv", "origin": "Dexter"},
    {"name": "Eleven", "category": "tv", "origin": "Stranger Things"},
    {"name": "Michael Scott", "category": "tv", "origin": "The Office"},
    {"name": "Don Draper", "category": "tv", "origin": "Mad Men"},
    {"name": "Sheldon Cooper", "category": "tv", "origin": "The Big Bang Theory"},
    {"name": "Ross Geller", "category": "tv", "origin": "Friends"},
    # ── Animation / Anime ───────────────────────────────────────────────────
    {"name": "Simba", "category": "animation", "origin": "The Lion King"},
    {"name": "Spongebob Squarepants", "category": "animation", "origin": "SpongeBob SquarePants"},
    {"name": "Gollum", "category": "movie/book", "origin": "The Lord of the Rings"},
    {"name": "Naruto Uzumaki", "category": "anime", "origin": "Naruto"},
    {"name": "Goku", "category": "anime", "origin": "Dragon Ball Z"},
    {"name": "Light Yagami", "category": "anime", "origin": "Death Note"},
    {"name": "Luffy", "category": "anime", "origin": "One Piece"},
    {"name": "Shinji Ikari", "category": "anime", "origin": "Neon Genesis Evangelion"},
    {"name": "Astro Boy", "category": "anime", "origin": "Astro Boy"},
    {"name": "Totoro", "category": "animation", "origin": "My Neighbor Totoro"},
    # ── Video Games ─────────────────────────────────────────────────────────
    {"name": "Master Chief", "category": "game", "origin": "Halo"},
    {"name": "Geralt of Rivia", "category": "game/book", "origin": "The Witcher"},
    {"name": "Solid Snake", "category": "game", "origin": "Metal Gear Solid"},
    {"name": "Link", "category": "game", "origin": "The Legend of Zelda"},
    {"name": "Commander Shepard", "category": "game", "origin": "Mass Effect"},
    {"name": "Lara Croft", "category": "game", "origin": "Tomb Raider"},
    {"name": "Aloy", "category": "game", "origin": "Horizon Zero Dawn"},
    {"name": "Joel Miller", "category": "game", "origin": "The Last of Us"},
    {"name": "Arthur Morgan", "category": "game", "origin": "Red Dead Redemption 2"},
    {"name": "Kratos", "category": "game", "origin": "God of War"},
    # ── Classic Literature ───────────────────────────────────────────────────
    {"name": "Hamlet", "category": "book", "origin": "Shakespeare"},
    {"name": "Lady Macbeth", "category": "book", "origin": "Shakespeare"},
    {"name": "Victor Frankenstein", "category": "book", "origin": "Frankenstein"},
    {"name": "Dracula", "category": "book", "origin": "Bram Stoker"},
    {"name": "Heathcliff", "category": "book", "origin": "Wuthering Heights"},
    {"name": "Captain Ahab", "category": "book", "origin": "Moby Dick"},
    {"name": "Don Quixote", "category": "book", "origin": "Miguel de Cervantes"},
    {"name": "Raskolnikov", "category": "book", "origin": "Crime and Punishment"},
    {"name": "Anna Karenina", "category": "book", "origin": "Leo Tolstoy"},
    {"name": "Emma Woodhouse", "category": "book", "origin": "Emma by Jane Austen"},
    # ── Sci-Fi / Fantasy ─────────────────────────────────────────────────────
    {"name": "HAL 9000", "category": "movie", "origin": "2001: A Space Odyssey"},
    {"name": "Spock", "category": "tv/movie", "origin": "Star Trek"},
    {"name": "Paul Atreides", "category": "book/movie", "origin": "Dune"},
    {"name": "Ender Wiggin", "category": "book", "origin": "Ender's Game"},
    {"name": "Tyrion Lannister", "category": "tv/book", "origin": "A Song of Ice and Fire"},
    {"name": "Yoda", "category": "movie", "origin": "Star Wars"},
    {"name": "Severus Snape", "category": "book/movie", "origin": "Harry Potter"},
    {"name": "Bilbo Baggins", "category": "book/movie", "origin": "The Hobbit"},
    {"name": "Arya Stark", "category": "tv/book", "origin": "Game of Thrones"},
    {"name": "Samwise Gamgee", "category": "book/movie", "origin": "Lord of the Rings"},
    # ── Comics / Superheroes ─────────────────────────────────────────────────
    {"name": "Batman / Bruce Wayne", "category": "comic/movie", "origin": "DC Comics"},
    {"name": "Spider-Man / Peter Parker", "category": "comic/movie", "origin": "Marvel"},
    {"name": "Wolverine", "category": "comic/movie", "origin": "X-Men"},
    {"name": "Wonder Woman", "category": "comic/movie", "origin": "DC Comics"},
    {"name": "Captain America", "category": "comic/movie", "origin": "Marvel"},
    {"name": "Deadpool", "category": "comic/movie", "origin": "Marvel"},
    {"name": "Black Widow", "category": "comic/movie", "origin": "Marvel"},
    {"name": "Thanos", "category": "comic/movie", "origin": "Marvel"},
    # ── Mythology / Folklore ─────────────────────────────────────────────────
    {"name": "Odysseus", "category": "mythology", "origin": "Greek Mythology / Homer"},
    {"name": "Achilles", "category": "mythology", "origin": "Greek Mythology / Homer"},
    {"name": "Loki", "category": "mythology/movie", "origin": "Norse Mythology"},
    {"name": "Medusa", "category": "mythology", "origin": "Greek Mythology"},
    {"name": "Merlin", "category": "mythology/book", "origin": "Arthurian Legend"},
    # ── Modern Classics ──────────────────────────────────────────────────────
    {"name": "Patrick Bateman", "category": "book/movie", "origin": "American Psycho"},
    {"name": "Amy Dunne", "category": "book/movie", "origin": "Gone Girl"},
    {"name": "Alex DeLarge", "category": "book/movie", "origin": "A Clockwork Orange"},
    {"name": "Nurse Ratched", "category": "book/movie", "origin": "One Flew Over the Cuckoo's Nest"},
    {"name": "The Tramp", "category": "movie", "origin": "Charlie Chaplin"},
    {"name": "Hannibal Lecter", "category": "book/movie", "origin": "Thomas Harris"},
    {"name": "John Wick", "category": "movie", "origin": "John Wick"},
    {"name": "V", "category": "comic/movie", "origin": "V for Vendetta"},
    {"name": "Beatrice Portinari", "category": "book", "origin": "Dante's Divine Comedy"},
    {"name": "Humbert Humbert", "category": "book", "origin": "Lolita by Nabokov"},
]


def get_daily_character(date: datetime.date | None = None) -> dict[str, str]:
    """Return a deterministic character for the given date using it as a seed."""
    if date is None:
        date = datetime.date.today()
    seed = int(date.strftime("%Y%m%d"))
    rng = random.Random(seed)
    return rng.choice(CHARACTERS)


def get_random_character(exclude_name: str | None = None) -> dict[str, str]:
    """Return a uniformly random character, optionally excluding one by name."""
    pool = [c for c in CHARACTERS if c["name"] != exclude_name] if exclude_name else CHARACTERS
    return random.choice(pool)
