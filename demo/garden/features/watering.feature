Feature: Watering the garden

  Scenario: A dry morning
    Given it is sunny
    And I have enabled the sprinkler "Tomato bed"
    When I water the basil with 1 cup
    Then the soil is damp

  Scenario Outline: Rain saves water
    Given it is <weather>
    When I water the mint with <amount>
    Then the soil is <soil>

    Examples:
      | weather | amount  | soil |
      | raining | nothing | wet  |
      | sunny   | 2 cups  | damp |
