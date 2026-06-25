# 30 Live Coding Execution Drills for AI/ML Freshers

This list is designed to build your muscle memory for the most common Python data manipulation patterns tested in live coding interviews. These are not obscure LeetCode hard problems; they are practical, foundational exercises meant to ensure you don't freeze on basic syntax during a screen share.

**How to practice:** Use the **Anti-Blank-Out Protocol** for every question.
1. Write the prompt as a comment.
2. State the brute-force solution out loud.
3. Code it while talking.
4. Optimize it (using Pythonic features like `set`, list comprehensions, or `collections`).

---

## Category 1: Lists & Arrays (The Basics)
*Focus: Loops, list comprehensions, and basic logic.*

1. **Find Duplicates:** Given a list, return a list of all elements that appear more than once. *(The Linearloop question)*
2. **Remove Duplicates:** Return a new list with all duplicates removed, preserving the original order.
3. **List Intersection:** Given two lists, return a list of elements that exist in both.
4. **Second Largest:** Find the second largest number in a list without using `sort()`.
5. **Move Zeroes:** Given a list of integers, move all `0`s to the end of it while maintaining the relative order of the non-zero elements.
6. **Flatten a Nested List:** Convert a list of lists (e.g., `[[1, 2], [3, 4]]`) into a single flat list.
7. **Chunking a List:** Write a function that takes a list and an integer `n` and splits the list into chunks of size `n`.
8. **Cumulative Sum:** Given a list of numbers, return a list where each element is the sum of all elements before it.
9. **Find Missing Number:** Given an array containing `n` distinct numbers taken from `0, 1, 2, ..., n`, find the one that is missing from the array.
10. **Rotate Array:** Rotate an array to the right by `k` steps, where `k` is non-negative.

---

## Category 2: Dictionaries & Frequency
*Focus: `dict.get()`, `collections.Counter`, and handling missing keys.*

11. **Word Frequency:** Count the occurrence of each word in a given sentence, ignoring punctuation and case.
12. **Two Sum:** Given an array of integers and a target sum, return the indices of the two numbers that add up to the target. *(Hint: Use a dictionary for O(1) lookups).*
13. **Valid Anagram:** Given two strings, write a function to determine if they are anagrams of each other.
14. **First Unique Character:** Find the first non-repeating character in a string and return its index. If it doesn't exist, return -1.
15. **Majority Element:** Find the element that appears more than `n/2` times in a list.
16. **Group Anagrams:** Given a list of strings, group the anagrams together in a list of lists.
17. **Merge Dictionaries:** Given two dictionaries, merge them. If a key exists in both, add their values together.

---

## Category 3: Strings Manipulation
*Focus: Slicing, joining, and character checking.*

18. **Reverse Words in a String:** Given a sentence, reverse the order of the words (not the characters).
19. **Valid Palindrome:** Check if a string is a palindrome, ignoring spaces, punctuation, and capitalization.
20. **Count Vowels and Consonants:** Given a string, return a dictionary with the count of vowels and consonants.
21. **Longest Common Prefix:** Write a function to find the longest common prefix string amongst an array of strings.
22. **String Compression:** Compress a string using the counts of repeated characters (e.g., `aabcccccaaa` becomes `a2b1c5a3`).
23. **Replace Substring:** Write a function that replaces all occurrences of a specific substring with another string, without using the built-in `.replace()` method.

---

## Category 4: Pandas & Data Processing (ML Specific)
*Focus: Data cleaning, missing values, and DataFrame operations.*

24. **Fill Missing Values:** Given a DataFrame with missing values in a numeric column, fill the NaNs with the median of that column.
25. **Filter and Sort:** Given a DataFrame of employees with columns `Name`, `Department`, and `Salary`, return the names of people in 'Engineering' earning more than 50,000, sorted by Salary descending.
26. **Group By Aggregation:** Given a DataFrame with columns `Category` and `Price`, return the average price for each category.
27. **Apply Function:** Given a DataFrame with a `Text` column, create a new column `Word_Count` by applying a custom function that counts the words in `Text`.
28. **One-Hot Encoding:** Write a short script to convert a categorical column in a DataFrame into one-hot encoded columns using Pandas.
29. **Drop Duplicates:** Identify and drop completely duplicated rows in a DataFrame, keeping the first occurrence.
30. **Normalization:** Given a list (or Pandas series) of numbers, apply Min-Max scaling to normalize the values between 0 and 1. 

---

### Pro-Tip for Practice:
Don't just solve these in your head. The execution barrier is a physical/verbal one. Open a blank `.py` file, hit record on your phone, and **talk to the screen** while typing out the solution. If you get stuck on syntax, note exactly what line you froze on—that's your muscle memory gap.
