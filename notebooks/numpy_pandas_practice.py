"""
NumPy & Pandas Practical Learning Lab
======================================
This file serves as a hand-on laboratory for exploring NumPy and Pandas.
It maps directly to your Notion Task: "W1: To Do - Learn Pandas & NumPy".

Task Checklist:
[x] Explore Definitions, approach
[x] Take one sample dataset that is workable for both numpy and pandas
[x] Try all in-built functions of Numpy with the chosen dataset
[x] Explore different ways to practice these in-built functions
"""

import numpy as np
import pandas as pd
import os

# ==========================================
# 1. DEFINITIONS & APPROACH
# ==========================================
# NumPy:
#   - Core library for scientific computing in Python.
#   - Provides the ndarray (n-dimensional array) object, which is homogeneous (all elements must be the same type).
#   - Implemented in C, making mathematical operations on large datasets highly efficient through vectorization.
#   - Best for: Pure numerical computations, matrix operations, image processing, and algorithms.
#
# Pandas:
#   - Built on top of NumPy, designed for high-level tabular data manipulation.
#   - Provides Series (1D) and DataFrame (2D) objects, which can handle heterogeneous data (different types across columns).
#   - Offers SQL-like alignment, handling of missing data, indexing, and time-series tools.
#   - Best for: Tabular data analysis, data cleaning, ETL processes, and database-like operations.
#
# Our Approach:
#   1. Generate a synthetic "Student Performance" dataset.
#   2. Load and inspect it using Pandas for tabular analysis.
#   3. Convert the numerical parts into NumPy arrays to run efficient numeric analysis.
#   4. Try out in-built NumPy and Pandas functions grouped by categories.

print("--- Step 1: Loaded Definitions & Approach ---")

# ==========================================
# 2. CREATE A WORKABLE DATASET
# ==========================================
# We will create a dataset of 10 students containing:
# - Student ID (Int)
# - Math Score (Int)
# - Science Score (Int)
# - English Score (Int)
# - Attendance % (Float)
# - Project Completed (Bool)

print("\n--- Step 2: Creating and Loading Sample Dataset ---")

data = {
    "StudentID": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
    "MathScore": [85, 92, 58, 76, 89, 45, 98, 82, 67, 91],
    "ScienceScore": [90, 88, 64, 72, 95, 52, 96, 78, 70, 89],
    "EnglishScore": [88, 94, 60, 80, 85, 50, 92, 85, 68, 93],
    "AttendanceRate": [0.95, 0.98, 0.85, 0.90, 0.96, 0.75, 0.99, 0.92, 0.88, 0.97],
    "ProjectCompleted": [True, True, False, True, True, False, True, True, False, True]
}

# Create Pandas DataFrame
df = pd.DataFrame(data)
print("Pandas DataFrame Loaded:")
print(df)

# Create NumPy array of scores (Math, Science, English) for numeric computing
scores_matrix = df[["MathScore", "ScienceScore", "EnglishScore"]].to_numpy()
print("\nNumPy Scores Matrix (Shape: {}, Dtype: {}):".format(scores_matrix.shape, scores_matrix.dtype))
print(scores_matrix)


# ==========================================
# 3. NUMPY IN-BUILT FUNCTIONS LAB
# ==========================================
print("\n--- Step 3: Running NumPy In-Built Functions ---")

# --- CATEGORY A: CREATION ---
print("\n[Creation Functions]")
# np.array() - already demonstrated
# np.zeros()
zeros_arr = np.zeros((2, 3))
print("zeros((2,3)):\n", zeros_arr)
# np.ones()
ones_arr = np.ones((2, 3))
print("ones((2,3)):\n", ones_arr)
# np.arange()
range_arr = np.arange(1, 11, 2)
print("arange(1, 11, 2):", range_arr)
# np.linspace()
linspace_arr = np.linspace(0, 1, 5)
print("linspace(0, 1, 5):", linspace_arr)
# np.random.randint()
random_scores = np.random.randint(50, 100, size=(5, 3))
print("random.randint(50, 100, (5,3)):\n", random_scores)
# np.eye()
identity_matrix = np.eye(3)
print("eye(3) (Identity matrix):\n", identity_matrix)

# --- CATEGORY B: INSPECTION & PROPERTIES ---
print("\n[Inspection Functions]")
print("Scores Matrix shape:", scores_matrix.shape)
print("Scores Matrix ndim:", scores_matrix.ndim)
print("Scores Matrix dtype:", scores_matrix.dtype)
print("Scores Matrix size (total elements):", scores_matrix.size)

# --- CATEGORY C: MATHEMATICAL OPERATIONS ---
print("\n[Mathematical Operations]")
# Vectorized operations (adding 5 grace points to all scores)
grace_scores = np.add(scores_matrix, 5)
print("Add 5 grace points (np.add):\n", grace_scores)
# Squareroot
sqrt_scores = np.sqrt(scores_matrix)
print("Square root of scores (np.sqrt, first 3 rows):\n", sqrt_scores[:3])
# np.clip - Clip scores to be within 60 and 100 (cap minimum and maximum values)
clipped_scores = np.clip(scores_matrix, 60, 100)
print("Clipped scores (np.clip [60, 100]):\n", clipped_scores)

# --- CATEGORY D: AGGREGATION & STATISTICS ---
print("\n[Aggregation & Statistics]")
# Overall mean score
print("Overall Mean Score:", np.mean(scores_matrix))
# Mean score by Subject (column-wise, axis=0)
# Subject index: 0=Math, 1=Science, 2=English
subject_means = np.mean(scores_matrix, axis=0)
print("Subject Means (Math, Science, English):", subject_means)
# Mean score by Student (row-wise, axis=1, first 3 students)
student_means = np.mean(scores_matrix, axis=1)
print("Student Means (First 3 students):", student_means[:3])
# Max and Min
print("Max score across all exams:", np.max(scores_matrix))
print("Min score across all exams:", np.min(scores_matrix))
# Argmax - find student and subject indices of the absolute maximum score
max_idx_flat = np.argmax(scores_matrix)
max_student, max_subject = np.unravel_index(max_idx_flat, scores_matrix.shape)
print("Maximum score of {} achieved by Student index {} in Subject index {}".format(
    scores_matrix[max_student, max_subject], max_student, max_subject
))
# Standard Deviation & Variance
print("Standard Deviation of English Scores (Column 2):", np.std(scores_matrix[:, 2]))
print("Variance of Science Scores (Column 1):", np.var(scores_matrix[:, 1]))

# --- CATEGORY E: MODIFICATION & RESHAPING ---
print("\n[Modification & Reshaping]")
# np.reshape() - Flatten the 10x3 scores matrix into a 30-element 1D array
flattened = scores_matrix.reshape(-1)
print("Reshaped to 1D (30 elements):", flattened[:10], "...and more")
# np.ravel() - Efficient view flattening
view_flat = np.ravel(scores_matrix)
# np.transpose()
transposed = np.transpose(scores_matrix)
print("Transposed Matrix (Subject rows, Student columns) shape:", transposed.shape)
# np.hstack() and np.vstack()
# Add a new column of dummy chemistry scores (10 elements)
chem_scores = np.random.randint(60, 100, size=(10, 1))
extended_scores = np.hstack((scores_matrix, chem_scores))
print("Extended Scores shape with Chemistry (np.hstack):", extended_scores.shape)

# --- CATEGORY F: SELECTION, FILTERING & CONDITIONS ---
print("\n[Selection, Filtering & Conditions]")
# Slicing: Math & Science scores of students 3 to 7
print("Slices (Rows 3-6, Columns 0-1):\n", scores_matrix[3:7, 0:2])
# Boolean Indexing: Scores where student got > 90
excellent_scores = scores_matrix[scores_matrix > 90]
print("Exam scores > 90:", excellent_scores)
# np.where(condition, if_true, if_false)
# If student scored >= 60, they Pass (1), otherwise Fail (0)
pass_fail_matrix = np.where(scores_matrix >= 60, 1, 0)
print("Pass (1) or Fail (0) Matrix:\n", pass_fail_matrix)
# np.nonzero() - find indices of failed exams (where score < 60)
fail_rows, fail_cols = np.nonzero(scores_matrix < 60)
print("Failures found at Students:", fail_rows, "and Subjects:", fail_cols)


# ==========================================
# 4. PANDAS IN-BUILT FUNCTIONS LAB
# ==========================================
print("\n--- Step 4: Running Pandas In-Built Functions ---")

# --- CATEGORY A: SELECTION & FILTERING ---
print("\n[Pandas Selection & Filtering]")
# Selecting columns
print("Math Score Column:\n", df["MathScore"].head(3))
# Selecting rows with .loc (by label) and .iloc (by position)
print("First Student Data (df.iloc[0]):\n", df.iloc[0])
print("\nStudents who scored > 80 in Math AND completed the project:")
filtered_df = df[(df["MathScore"] > 80) & (df["ProjectCompleted"] == True)]
print(filtered_df)

# --- CATEGORY B: DESCRIPTIVE STATISTICS & INSPECTION ---
print("\n[Pandas Inspection & Statistics]")
# df.describe() - quick summary stats of numeric columns
print("DataFrame Descriptive Statistics Summary:\n", df.describe())
# df.info()
print("\nDataFrame structure details:")
df.info()

# --- CATEGORY C: DATA MODIFICATION ---
print("\n[Pandas Data Modification]")
# Adding new column representing final average grade
df["AverageGrade"] = df[["MathScore", "ScienceScore", "EnglishScore"]].mean(axis=1)
# Mapping ProjectCompleted boolean to strings
df["ProjectStatus"] = df["ProjectCompleted"].map({True: "Done", False: "Pending"})
# Rename columns
df_renamed = df.rename(columns={"AverageGrade": "FinalAverage"})
print("\nDataFrame after updates (average column and status mapping):")
print(df_renamed[["StudentID", "FinalAverage", "ProjectStatus"]])

# --- CATEGORY D: GROUPING & AGGREGATION ---
print("\n[Pandas Grouping & Aggregation]")
# Grouping students by ProjectCompleted and getting their average math scores
grouped = df.groupby("ProjectCompleted")["MathScore"].mean()
print("Average Math Score grouped by Project Completion status:")
print(grouped)

# ==========================================
# 5. EXPLORE WAYS TO PRACTICE
# ==========================================
print("\n--- Step 5: Suggested Practice Workflows ---")
print("""
To solidify your learning of these NumPy & Pandas tools, you can:
1. RUN THIS LAB: Execute `python notebooks/numpy_pandas_practice.py` to see outputs live.
2. JUPYTER LAB: Open VS Code and install the Jupyter extension, then open a cell block (e.g. `ml_introduction.ipynb`)
   and type `df.head()` or `np.mean(scores_matrix)` to inspect values interactively.
3. DATA IMPORT CHALLENGE: Try downloading a public dataset (like Titanic or Iris) as a CSV, load it using `pd.read_csv`,
   clean missing values using `.fillna()` or `.dropna()`, and run descriptive metrics.
4. VECTORIZATION CHALLENGE: Write a normal python loop to calculate the square of elements in a list, then do the same using np.power(arr, 2).
   Time both using `time` module or `%timeit` in notebook to feel the performance boost!
""")

if __name__ == "__main__":
    print("\n[Execution Completed successfully!]")
