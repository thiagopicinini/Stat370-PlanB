# Data Analysis

This directory contains exploratory data analysis, visualizations, and statistical outputs.

## Files

### EDA Oscar Sanchez Huezca.ipynb

**Purpose**: Exploratory Data Analysis notebook for the Stat370-PlanB project.

**Contents:**
- Student enrollment patterns
- Course completion statistics
- Major distribution analysis
- Grade distribution analysis
- Semester-by-semester trends
- Data quality checks

**To Open:**
```bash
jupyter notebook "EDA Oscar Sanchez Huezca.ipynb"
```

---

### semester_statistics.csv

**Purpose**: Aggregated statistics by semester.

**Possible Metrics:**
- Total student count per semester
- Average courses per student
- Grade distributions
- Enrollment trends
- Major popularity
- Course completion rates

**Usage:**
```python
import pandas as pd

stats = pd.read_csv('data_analysis/semester_statistics.csv')
```

---

## Analysis Topics

### Student Enrollment Patterns

**Questions Explored:**
- How many students are enrolled each semester?
- What is the retention rate across semesters?
- Which semesters have highest enrollment?
- How do Fall/Spring enrollment differ?

### Course Completion

**Metrics:**
- Pass rates by course
- Grade distributions
- Most commonly taken courses
- Course sequences
- Prerequisites completion

### Major Analysis

**Insights:**
- Most popular majors
- Major switching patterns
- Credits required per major
- Completion rates
- Time to degree

### Recommendation System Validation

**Analyses:**
- How many students match each major?
- Distribution of credits earned
- Common alternative major paths
- Validation of recommendation logic

---

## Adding New Analyses

### Creating New Notebooks

```bash
jupyter notebook
# Create new notebook in this directory
```

**Recommended Structure:**
1. Import libraries and load data
2. Data cleaning and preparation
3. Exploratory visualizations
4. Statistical tests
5. Summary and conclusions

### Common Imports

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path.cwd().parent))
from utils.paths import *
```

---

## Data Sources

**Available Datasets:**
- `filtered_data/merged_student_enrollment.tsv` - Combined enrollment
- `filtered_data/bachelors_majors_web.json` - Major requirements
- `filtered_data/courses.json` - Course details
- `original_data/deident_student_enrollment_*.tsv` - Raw data

**Loading Data:**
```python
from utils.paths import MERGED_ENROLLMENT, MAJORS_JSON, COURSES_JSON

# Load enrollment
df = pd.read_csv(MERGED_ENROLLMENT, sep='\t')

# Load majors
import json
with open(MAJORS_JSON) as f:
    majors = json.load(f)
```

---

## Visualization Guidelines

**Recommended Libraries:**
- matplotlib - Basic plotting
- seaborn - Statistical visualizations
- plotly - Interactive charts
- pandas plotting - Quick EDA

**Save Figures:**
```python
plt.savefig('data_analysis/figures/my_plot.png', dpi=300, bbox_inches='tight')
```

---

## Statistical Tests

**Common Analyses:**
- t-tests for group comparisons
- Chi-square for categorical associations
- ANOVA for multiple groups
- Correlation analysis
- Regression models

**Example:**
```python
from scipy import stats

# Compare grade distributions
result = stats.ttest_ind(group1, group2)
print(f"t-statistic: {result.statistic}, p-value: {result.pvalue}")
```

---

## Privacy Considerations

**Remember:**
- All data is de-identified
- No student names or IDs in outputs
- Aggregate statistics only
- No individual-level reporting
- Follow IRB guidelines

---

## Best Practices

**Documentation:**
- Add markdown cells explaining each analysis
- Document assumptions
- Note data limitations
- Include references

**Code Quality:**
- Use descriptive variable names
- Comment complex logic
- Keep cells focused
- Rerun notebooks before saving

**Reproducibility:**
- Set random seeds
- Document package versions
- Use relative paths
- Clear all outputs before committing

---

## Output Guidelines

**What to Save:**
- Summary statistics CSV files
- Key visualizations (PNG/PDF)
- Analysis results
- Model outputs

**What NOT to Save:**
- Large intermediate files
- Raw notebook outputs
- Temporary variables
- Debug prints

---

## Next Steps

**Potential Analyses:**
1. Recommendation system effectiveness
2. Student success predictors
3. Course difficulty analysis
4. Major pathway analysis
5. Time-to-degree modeling
6. Prerequisite network analysis

**Data Enhancements:**
1. Add temporal analysis
2. Cohort tracking
3. Course sequence mining
4. Major switching patterns
5. Credit accumulation trends
