Feature: Content safety
  As a community member
  I want unsafe content blocked
  So that young people stay safe online

  Scenario: Phone numbers are rejected in posts
    Given a verified user is logged in
    When I try to post "Call me at 555-123-4567"
    Then the post should be rejected

  Scenario: Safe posts are accepted
    Given a verified user is logged in
    When I try to post "Had a great day at school"
    Then the post should be accepted
