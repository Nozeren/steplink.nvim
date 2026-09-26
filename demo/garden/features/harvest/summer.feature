Feature: Summer harvest

  Scenario: The tomatoes are ready
    Given it is sunny
    When I water the tomato with 2 cups
    And I pick every ripe tomato
    Then the basket holds 12 tomatoes
