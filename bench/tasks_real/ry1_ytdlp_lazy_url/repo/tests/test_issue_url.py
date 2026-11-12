import unittest

from yt_dlp.extractor import gen_extractor_classes


class TestCharlieRoseUrl(unittest.TestCase):
    def test_charlierose_episode_url(self):
        url = "https://charlierose.com/episodes/30887?autoplay=true"
        matches = [ie.ie_key() for ie in gen_extractor_classes() if ie.suitable(url)]
        self.assertEqual(matches[0], "CharlieRose")
