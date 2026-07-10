Feature: Desktop-only access
  As a visitor
  I want Desktap to block mobile devices
  So that people use a desktop computer

  Scenario: Desktop users can view the landing page
    Given I am using a desktop browser
    When I visit the landing page
    Then I should see the landing page

  Scenario: Mobile users are blocked
    Given I am using a mobile browser
    When I visit the landing page
    Then I should be redirected to the blocked page
