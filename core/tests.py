from django.test import TestCase

from accounts.security import validate_safe_content


class ContentSafetyTests(TestCase):
    def test_blocks_phone_numbers(self):
        issues = validate_safe_content("My number is 555-123-4567")
        self.assertTrue(issues)

    def test_blocks_urls(self):
        issues = validate_safe_content("Visit https://evil.example.com now")
        self.assertTrue(issues)

    def test_allows_safe_text(self):
        issues = validate_safe_content("Hello friends, hope you are well.")
        self.assertEqual(issues, [])

    def test_blocks_harmful_phrases(self):
        issues = validate_safe_content("please share your password with me")
        self.assertTrue(issues)
