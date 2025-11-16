"""
This script tests the functionality of the `get_transcript` function from the server module.

It fetches and prints the transcript of a YouTube video given its URL.
"""

from server import get_transcript

T = get_transcript("https://www.youtube.com/watch?v=jqd6_bbjhS8&t=12s")
print(T)
