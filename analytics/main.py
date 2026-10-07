import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
import json
from datetime import datetime
import re

class AdaptiveDataAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.insights = {
            'overview': {},
            'numerical_analysis': {},
            'categorical_analysis': {},
            'temporal_analysis': {},
            'correlations': {},
            'anomalies': [],
            'summary': ''
        }
        
    def identify_column_types(self) -> Dict[str, List[str]]:
        """Intelligently identify column types based on data and names"""
        column_types = {
            'numerical': [],
            'categorical': [],
            'temporal': [],
            'monetary': [],
            'percentage': [],
            'id_fields': [],
            'binary': []
        }
        
        monetary_keywords = ['premium', 'claim', 'amount', 'price', 'cost', 'revenue', 'salary', 'payment', 'fee']
        percentage_keywords = ['rate', 'ratio', 'percentage', 'pct', '%']
        temporal_keywords = ['date', 'time', 'year', 'month', 'day', 'timestamp', 'created', 'updated']
        id_keywords = ['id', 'code', 'key', 'identifier', 'uuid', 'hash']
        
        for col in self.df.columns:
            col_lower = col.lower()
            dtype = self.df[col].dtype
            
            # Check for date/time columns
            if pd.api.types.is_datetime64_any_dtype(self.df[col]) or any(word in col_lower for word in temporal_keywords):
                try:
                    pd.to_datetime(self.df[col], errors='raise')
                    column_types['temporal'].append(col)
                    continue
                except:
                    pass
            
            # Check for numerical columns
            if pd.api.types.is_numeric_dtype(self.df[col]):
                # Check for monetary values
                if any(word in col_lower for word in monetary_keywords):
                    column_types['monetary'].append(col)
                # Check for percentages
                elif any(word in col_lower for word in percentage_keywords) or (self.df[col].between(0, 1).all() and self.df[col].max() <= 1):
                    column_types['percentage'].append(col)
                # Check for binary (0/1) columns
                elif self.df[col].dropna().isin([0, 1]).all():
                    column_types['binary'].append(col)
                # Regular numerical
                else:
                    column_types['numerical'].append(col)
            
            # Check for categorical/text columns
            elif pd.api.types.is_object_dtype(self.df[col]) or pd.api.types.is_categorical_dtype(self.df[col]):
                # Check if it might be an ID field
                if any(word in col_lower for word in id_keywords) or self.df[col].nunique() > len(self.df) * 0.8:
                    column_types['id_fields'].append(col)
                else:
                    column_types['categorical'].append(col)
        
        return column_types
    
    def analyze_numerical(self, columns: List[str]) -> Dict[str, Any]:
        """Comprehensive numerical analysis"""
        analysis = {}
        
        for col in columns:
            data = self.df[col].dropna()
            if len(data) == 0:
                continue
                
            stats = {
                'count': int(len(data)),
                'missing': int(self.df[col].isna().sum()),
                'mean': float(data.mean()),
                'median': float(data.median()),
                'mode': float(data.mode()[0]) if not data.mode().empty else None,
                'std': float(data.std()),
                'var': float(data.var()),
                'min': float(data.min()),
                'max': float(data.max()),
                'range': float(data.max() - data.min()),
                'q1': float(data.quantile(0.25)),
                'q3': float(data.quantile(0.75)),
                'iqr': float(data.quantile(0.75) - data.quantile(0.25)),
                'skewness': float(data.skew()),
                'kurtosis': float(data.kurtosis()),
                'cv': float(data.std() / data.mean()) if data.mean() != 0 else 0,
            }
            
            # Detect outliers using IQR method
            q1, q3 = data.quantile(0.25), data.quantile(0.75)
            iqr = q3 - q1
            outliers = data[(data < q1 - 1.5 * iqr) | (data > q3 + 1.5 * iqr)]
            stats['outliers_count'] = len(outliers)
            stats['outliers_percentage'] = len(outliers) / len(data) * 100
            stats['outliers_range'] = (float(outliers.min()), float(outliers.max())) if len(outliers) > 0 else None
            
            # Distribution shape
            if abs(stats['skewness']) < 0.5:
                stats['distribution'] = "approximately symmetric"
            elif stats['skewness'] > 0.5:
                stats['distribution'] = "right-skewed (positive skew)"
            else:
                stats['distribution'] = "left-skewed (negative skew)"
            
            analysis[col] = stats
            
        return analysis
    
    def analyze_categorical(self, columns: List[str]) -> Dict[str, Any]:
        """Comprehensive categorical analysis"""
        analysis = {}
        
        for col in columns:
            data = self.df[col].dropna()
            if len(data) == 0:
                continue
            
            value_counts = data.value_counts()
            top_categories = value_counts.head(10).to_dict()
            
            stats = {
                'count': int(len(data)),
                'missing': int(self.df[col].isna().sum()),
                'unique_values': int(data.nunique()),
                'top_categories': {str(k): int(v) for k, v in top_categories.items()},
                'top_category': str(data.mode()[0]) if not data.mode().empty else None,
                'top_category_frequency': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                'top_category_percentage': float(value_counts.iloc[0] / len(data) * 100) if len(value_counts) > 0 else 0,
                'entropy': self._calculate_entropy(value_counts.values),
                'cardinality_ratio': data.nunique() / len(data)
            }
            
            # Check for rare categories
            rare_threshold = 0.01  # 1%
            rare_categories = value_counts[value_counts / len(data) < rare_threshold]
            stats['rare_categories_count'] = len(rare_categories)
            stats['rare_categories_percentage'] = len(rare_categories) / data.nunique() * 100 if data.nunique() > 0 else 0
            
            analysis[col] = stats
            
        return analysis
    
    def _calculate_entropy(self, frequencies):
        """Calculate Shannon entropy"""
        probs = frequencies / frequencies.sum()
        return float(-np.sum(probs * np.log2(probs + 1e-10)))
    
    def analyze_temporal(self, columns: List[str]) -> Dict[str, Any]:
        """Comprehensive temporal analysis"""
        analysis = {}
        
        for col in columns:
            try:
                # Convert to datetime
                dates = pd.to_datetime(self.df[col], errors='coerce').dropna()
                if len(dates) == 0:
                    continue
                
                # Extract temporal features
                years = dates.dt.year
                months = dates.dt.month
                quarters = dates.dt.quarter
                days_of_week = dates.dt.dayofweek
                
                stats = {
                    'count': int(len(dates)),
                    'missing': int(self.df[col].isna().sum()),
                    'min_date': dates.min().strftime('%Y-%m-%d'),
                    'max_date': dates.max().strftime('%Y-%m-%d'),
                    'date_range_days': (dates.max() - dates.min()).days,
                    'year_distribution': years.value_counts().to_dict(),
                    'month_distribution': months.value_counts().to_dict(),
                    'quarter_distribution': quarters.value_counts().to_dict(),
                    'day_of_week_distribution': days_of_week.value_counts().to_dict(),
                    'is_weekend_ratio': float((days_of_week >= 5).sum() / len(dates)),
                    'most_common_year': int(years.mode()[0]) if not years.mode().empty else None,
                    'most_common_month': int(months.mode()[0]) if not months.mode().empty else None,
                }
                
                # Check for seasonality
                monthly_avg = dates.groupby(months).size().mean()
                monthly_std = dates.groupby(months).size().std()
                stats['seasonality_strength'] = float(monthly_std / monthly_avg) if monthly_avg > 0 else 0
                
                analysis[col] = stats
                
            except Exception as e:
                print(f"Error analyzing temporal column {col}: {e}")
                continue
        
        return analysis
    
    def analyze_correlations(self, numerical_cols: List[str]) -> Dict[str, Any]:
        """Find significant correlations between numerical columns"""
        if len(numerical_cols) < 2:
            return {}
        
        correlation_matrix = self.df[numerical_cols].corr()
        significant_correlations = []
        
        for i in range(len(numerical_cols)):
            for j in range(i+1, len(numerical_cols)):
                corr = correlation_matrix.iloc[i, j]
                if abs(corr) > 0.5:  # Significant correlation threshold
                    significant_correlations.append({
                        'col1': numerical_cols[i],
                        'col2': numerical_cols[j],
                        'correlation': float(corr),
                        'strength': 'strong' if abs(corr) > 0.7 else 'moderate',
                        'direction': 'positive' if corr > 0 else 'negative'
                    })
        
        return {
            'correlation_matrix': correlation_matrix.to_dict(),
            'significant_correlations': significant_correlations
        }
    
    def detect_anomalies(self, column_types: Dict[str, List[str]]) -> List[str]:
        """Detect data anomalies and quality issues"""
        anomalies = []
        
        # Check for missing data
        missing_pct = self.df.isna().sum() / len(self.df) * 100
        high_missing = missing_pct[missing_pct > 20]
        for col, pct in high_missing.items():
            anomalies.append(f"Column '{col}' has {pct:.1f}% missing values")
        
        # Check for constant columns
        for col in self.df.columns:
            if self.df[col].nunique() == 1:
                anomalies.append(f"Column '{col}' is constant (single value)")
        
        # Check for duplicates
        duplicates = self.df.duplicated().sum()
        if duplicates > 0:
            anomalies.append(f"Dataset contains {duplicates} duplicate rows ({duplicates/len(self.df)*100:.1f}%)")
        
        # Check for suspicious values in numerical columns
        for col in column_types.get('monetary', []):
            if col in self.df.columns:
                negative_count = (self.df[col] < 0).sum()
                if negative_count > 0:
                    anomalies.append(f"Column '{col}' has {negative_count} negative values (monetary fields should typically be positive)")
                
                zero_count = (self.df[col] == 0).sum()
                if zero_count > len(self.df) * 0.5:
                    anomalies.append(f"Column '{col}' has {zero_count} zero values ({zero_count/len(self.df)*100:.1f}%)")
        
        return anomalies
    
    def generate_essay_summary(self) -> str:
        """Generate a comprehensive human-readable essay summary"""
        
        column_types = self.identify_column_types()
        
        # Perform all analyses
        num_analysis = self.analyze_numerical(column_types['numerical'] + column_types['monetary'] + column_types['percentage'])
        cat_analysis = self.analyze_categorical(column_types['categorical'])
        temp_analysis = self.analyze_temporal(column_types['temporal'])
        corr_analysis = self.analyze_correlations(column_types['numerical'] + column_types['monetary'])
        anomalies = self.detect_anomalies(column_types)
        
        # Build the essay
        essay = []
        
        # 1. Overview
        essay.append(f"# DATA ANALYSIS REPORT\n")
        essay.append(f"**Dataset Overview:** This analysis examines {len(self.df):,} records with {len(self.df.columns)} features. ")
        essay.append(f"The dataset contains {len(column_types['numerical'])} numerical, {len(column_types['categorical'])} categorical, ")
        essay.append(f"{len(column_types['temporal'])} temporal, and {len(column_types['monetary'])} monetary fields.\n")
        
        # 2. Data Quality
        if anomalies:
            essay.append("## Data Quality Assessment\n")
            essay.append("Several data quality issues were identified:\n")
            for anomaly in anomalies[:5]:  # Top 5 anomalies
                essay.append(f"• {anomaly}")
            essay.append("")
        
        # 3. Numerical Analysis
        if num_analysis:
            essay.append("## Numerical Analysis\n")
            
            for col, stats in num_analysis.items():
                essay.append(f"### {col}")
                
                # Central tendency and spread
                essay.append(f"Values range from {stats['min']:.2f} to {stats['max']:.2f}, ")
                essay.append(f"with a mean of {stats['mean']:.2f} and median of {stats['median']:.2f}. ")
                
                if abs(stats['mean'] - stats['median']) > stats['std'] * 0.2:
                    essay.append(f"The notable gap between mean and median indicates {stats['distribution']}. ")
                
                # Variability
                essay.append(f"The standard deviation is {stats['std']:.2f}, ")
                essay.append(f"giving a coefficient of variation of {stats['cv']:.2f}. ")
                
                # Outliers
                if stats['outliers_count'] > 0:
                    essay.append(f"There are {stats['outliers_count']} outliers ({stats['outliers_percentage']:.1f}% of data), ")
                    essay.append(f"ranging from {stats['outliers_range'][0]:.2f} to {stats['outliers_range'][1]:.2f}. ")
                
                # Quartiles
                essay.append(f"The interquartile range (IQR) is {stats['iqr']:.2f}, ")
                essay.append(f"with 25% of values below {stats['q1']:.2f} and 25% above {stats['q3']:.2f}.\n")
        
        # 4. Temporal Patterns
        if temp_analysis:
            essay.append("## Temporal Patterns\n")
            
            for col, stats in temp_analysis.items():
                essay.append(f"### {col}")
                essay.append(f"Data spans {stats['date_range_days']} days from {stats['min_date']} to {stats['max_date']}. ")
                
                # Seasonal patterns
                if stats['seasonality_strength'] > 0.3:
                    essay.append("Strong seasonal patterns are evident in the data. ")
                elif stats['seasonality_strength'] > 0.1:
                    essay.append("Weak seasonal patterns may be present. ")
                
                # Weekend vs weekday
                if 'is_weekend_ratio' in stats:
                    weekend_pct = stats['is_weekend_ratio'] * 100
                    essay.append(f"Approximately {weekend_pct:.1f}% of records fall on weekends. ")
                
                # Most active periods
                if stats['most_common_month']:
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    essay.append(f"The most active month is {month_names[stats['most_common_month']-1]}. ")
                
                essay.append("")
        
        # 5. Categorical Insights
        if cat_analysis:
            essay.append("## Categorical Insights\n")
            
            for col, stats in cat_analysis.items():
                essay.append(f"### {col}")
                essay.append(f"This field has {stats['unique_values']} unique values. ")
                
                if stats['top_category']:
                    essay.append(f"The most common category is '{stats['top_category']}', ")
                    essay.append(f"appearing {stats['top_category_frequency']} times ({stats['top_category_percentage']:.1f}% of records). ")
                
                if stats['rare_categories_count'] > 0:
                    essay.append(f"There are {stats['rare_categories_count']} rare categories (appearing in less than 1% of records). ")
                
                # Cardinality assessment
                if stats['cardinality_ratio'] > 0.5:
                    essay.append("This field has very high cardinality (almost unique per record). ")
                elif stats['cardinality_ratio'] < 0.01:
                    essay.append("This field has very low cardinality (few distinct values). ")
                
                essay.append("")
        
        # 6. Correlations and Relationships
        if corr_analysis and corr_analysis.get('significant_correlations'):
            essay.append("## Key Relationships\n")
            essay.append("Several significant correlations were discovered:\n")
            
            for corr in corr_analysis['significant_correlations']:
                essay.append(f"• {corr['col1']} and {corr['col2']} show a **{corr['strength']} {corr['direction']}** correlation ")
                essay.append(f"({corr['correlation']:.2f}). ")
                
                # Interpret the correlation
                if corr['direction'] == 'positive':
                    essay.append("As one increases, the other tends to increase. ")
                else:
                    essay.append("As one increases, the other tends to decrease. ")
                essay.append("")
        
        # 7. Key Takeaways
        essay.append("## Key Takeaways\n")
        
        # Extract most important insights
        takeaways = []
        
        # Overall data quality
        if not anomalies:
            takeaways.append("✓ The dataset appears clean with no major quality issues")
        else:
            takeaways.append(f"⚠ Address {len(anomalies)} data quality issues identified above")
        
        # Most variable metric
        if num_analysis:
            most_variable = max(num_analysis.items(), key=lambda x: x[1]['cv'])
            takeaways.append(f"📊 '{most_variable[0]}' shows the highest relative variability (CV: {most_variable[1]['cv']:.2f})")
        
        # Temporal coverage
        if temp_analysis:
            first_temp = list(temp_analysis.values())[0]
            takeaways.append(f"📅 Data covers {first_temp['date_range_days']} days of temporal information")
        
        # Strongest correlation
        if corr_analysis and corr_analysis.get('significant_correlations'):
            strongest = max(corr_analysis['significant_correlations'], key=lambda x: abs(x['correlation']))
            takeaways.append(f"🔗 Strongest relationship: {strongest['col1']} ↔ {strongest['col2']} ({strongest['correlation']:.2f})")
        
        for takeaway in takeaways:
            essay.append(f"{takeaway}")
        
        # Final note
        essay.append("\n---")
        essay.append(f"*Analysis generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        essay.append(f"*Total records analyzed: {len(self.df):,}*")
        
        return "\n".join(essay)
    
    def analyze(self) -> Dict[str, Any]:
        """Main analysis method"""
        column_types = self.identify_column_types()
        
        self.insights['column_types'] = {k: list(v) for k, v in column_types.items()}
        self.insights['overview'] = {
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'memory_usage': f"{self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
            'missing_values': self.df.isna().sum().to_dict(),
            'duplicates': int(self.df.duplicated().sum())
        }
        
        self.insights['numerical_analysis'] = self.analyze_numerical(
            column_types['numerical'] + column_types['monetary'] + column_types['percentage']
        )
        self.insights['categorical_analysis'] = self.analyze_categorical(column_types['categorical'])
        self.insights['temporal_analysis'] = self.analyze_temporal(column_types['temporal'])
        self.insights['correlations'] = self.analyze_correlations(
            column_types['numerical'] + column_types['monetary']
        )
        self.insights['anomalies'] = self.detect_anomalies(column_types)
        self.insights['summary'] = self.generate_essay_summary()
        
        return self.insights

# Usage example with your FastAPI endpoint
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import BytesIO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Beaver chat API (roles, tags, Ollama planner)
from beaver_api import router as beaver_router
app.include_router(beaver_router)

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    
    # Read the file
    if file.filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(content))
    elif file.filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(content))
    else:
        return {"error": "Unsupported file type"}
    
    # Run adaptive analysis
    analyzer = AdaptiveDataAnalyzer(df)
    insights = analyzer.analyze()
    
    return {
        "filename": file.filename,
        "analysis": insights
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)