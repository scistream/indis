#!/usr/bin/env python3
"""
Network Experiment Analysis - Linear vs Log-Linear Regression
Saves plots to files instead of displaying them.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import warnings
import os
warnings.filterwarnings('ignore')

# Use non-interactive backend
plt.switch_backend('Agg')

def analyze_linear_vs_loglinear(df, x_col, y_col, log_transform='y', output_dir='plots'):
    """
    Perform linear and log-linear regression analysis and save plots to files
    
    Parameters:
    - df: DataFrame with experiment data
    - x_col: Column name for x-axis (independent variable)
    - y_col: Column name for y-axis (dependent variable) 
    - log_transform: 'x', 'y', or 'both' - which variable to log-transform
    - output_dir: Directory to save plots
    """
    print(f"\n🔍 Analyzing relationship: {y_col} vs {x_col}")
    print(f"📊 Log transformation applied to: {log_transform}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean data - remove rows where either column is empty/NaN
    clean_df = df.dropna(subset=[x_col, y_col])
    clean_df = clean_df[(clean_df[x_col] != '') & (clean_df[y_col] != '')]
    
    if len(clean_df) < 3:
        print(f"❌ Not enough data points for regression analysis. Need at least 3, have {len(clean_df)}")
        return
    
    # Convert to numeric
    x = pd.to_numeric(clean_df[x_col], errors='coerce')
    y = pd.to_numeric(clean_df[y_col], errors='coerce')
    
    # Remove any remaining NaN values
    valid_mask = ~(x.isna() | y.isna())
    x = x[valid_mask].values
    y = y[valid_mask].values
    
    # Remove zero or negative values if log transform is needed
    if log_transform in ['x', 'both']:
        positive_x_mask = x > 0
        x = x[positive_x_mask]
        y = y[positive_x_mask]
        
    if log_transform in ['y', 'both']:
        positive_y_mask = y > 0
        x = x[positive_y_mask]
        y = y[positive_y_mask]
    
    if len(x) < 3:
        print(f"❌ Not enough valid positive data points after log filtering. Have {len(x)}")
        return
    
    print(f"📊 Analyzing {len(x)} data points")
    print(f"📏 X ({x_col}) range: {x.min():.3f} to {x.max():.3f}")
    print(f"📏 Y ({y_col}) range: {y.min():.3f} to {y.max():.3f}")
    
    # Create figure
    plt.figure(figsize=(20, 8))
    
    # === LEFT PLOT: Original Linear Regression ===
    plt.subplot(1, 2, 1)
    plt.scatter(x, y, alpha=0.7, s=80, color='blue', label='Observations', zorder=3, edgecolors='navy', linewidth=0.5)
    
    # Generate smooth line for plotting
    x_smooth = np.linspace(x.min(), x.max(), 100)
    
    # Linear Regression on original data
    lin_reg = LinearRegression()
    lin_reg.fit(x.reshape(-1, 1), y)
    y_lin_pred = lin_reg.predict(x.reshape(-1, 1))
    y_lin_smooth = lin_reg.predict(x_smooth.reshape(-1, 1))
    
    linear_rmse = np.sqrt(mean_squared_error(y, y_lin_pred))
    r2_linear = lin_reg.score(x.reshape(-1, 1), y)
    
    plt.plot(x_smooth, y_lin_smooth, 'r-', linewidth=3, 
             label=f'Linear (RMSE: {linear_rmse:.4f}, R²: {r2_linear:.4f})', zorder=2)
    
    plt.xlabel(x_col, fontsize=12, fontweight='bold')
    plt.ylabel(y_col, fontsize=12, fontweight='bold')
    plt.title('Linear Regression (Original Scale)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    # === RIGHT PLOT: Log-Linear Regression ===
    plt.subplot(1, 2, 2)
    
    # Apply log transformation
    if log_transform == 'x':
        x_log = np.log(x)
        y_log = y
        x_label = f'log({x_col})'
        y_label = y_col
        transform_desc = f'Exponential: {y_col} = a * {x_col}^b'
    elif log_transform == 'y':
        x_log = x
        y_log = np.log(y)
        x_label = x_col
        y_label = f'log({y_col})'
        transform_desc = f'Exponential: {y_col} = a * exp(b * {x_col})'
    elif log_transform == 'both':
        x_log = np.log(x)
        y_log = np.log(y)
        x_label = f'log({x_col})'
        y_label = f'log({y_col})'
        transform_desc = f'Power law: {y_col} = a * {x_col}^b'
    
    # Linear regression on log-transformed data
    log_reg = LinearRegression()
    log_reg.fit(x_log.reshape(-1, 1), y_log)
    y_log_pred = log_reg.predict(x_log.reshape(-1, 1))
    
    # Calculate RMSE in original space
    if log_transform == 'y':
        y_orig_pred = np.exp(y_log_pred)  # Transform back to original scale
    elif log_transform == 'x':
        y_orig_pred = y_log_pred  # y is already in original scale
    elif log_transform == 'both':
        y_orig_pred = np.exp(y_log_pred)  # Transform y back to original scale
    
    log_linear_rmse = np.sqrt(mean_squared_error(y, y_orig_pred))
    r2_log = log_reg.score(x_log.reshape(-1, 1), y_log)
    
    # Plot transformed data
    plt.scatter(x_log, y_log, alpha=0.7, s=80, color='green', label='Transformed data', zorder=3, edgecolors='darkgreen', linewidth=0.5)
    
    # Generate smooth line for log regression
    x_log_smooth = np.linspace(x_log.min(), x_log.max(), 100)
    y_log_smooth = log_reg.predict(x_log_smooth.reshape(-1, 1))
    
    plt.plot(x_log_smooth, y_log_smooth, 'orange', linewidth=3,
             label=f'Log-Linear (RMSE: {log_linear_rmse:.4f}, R²: {r2_log:.4f})', zorder=2)
    
    plt.xlabel(x_label, fontsize=12, fontweight='bold')
    plt.ylabel(y_label, fontsize=12, fontweight='bold')
    plt.title('Log-Linear Regression (Log Scale)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    # Overall title
    plt.suptitle(f'{y_col} vs {x_col} - Linear vs Log-Linear Comparison', 
                 fontsize=16, fontweight='bold')
    
    # Save plot
    plot_filename = f"{output_dir}/{y_col.replace(' ', '_')}_vs_{x_col.replace(' ', '_')}_log_{log_transform}.png"
    plt.tight_layout()
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Plot saved to: {plot_filename}")
    
    # Print results
    print(f"\n📊 === Regression Comparison ===")
    print(f"🔴 Linear Regression (original scale):")
    print(f"   📐 Equation: {y_col} = {lin_reg.coef_[0]:.6f} * {x_col} + {lin_reg.intercept_:.6f}")
    print(f"   📈 R² Score: {r2_linear:.6f}")
    print(f"   📏 RMSE: {linear_rmse:.6f}")
    
    print(f"\n🟠 Log-Linear Regression:")
    print(f"   📐 Linear in log space: {y_label} = {log_reg.coef_[0]:.6f} * {x_label} + {log_reg.intercept_:.6f}")
    print(f"   🔄 {transform_desc}")
    print(f"   📈 R² Score (log space): {r2_log:.6f}")
    print(f"   📏 RMSE (original space): {log_linear_rmse:.6f}")
    
    # Determine better fit
    if log_linear_rmse < linear_rmse:
        improvement = ((linear_rmse - log_linear_rmse) / linear_rmse) * 100
        print(f"\n✅ 🟠 Log-Linear model fits better!")
        print(f"   📈 RMSE improvement: {improvement:.1f}% ({linear_rmse:.6f} → {log_linear_rmse:.6f})")
        print(f"   💡 The relationship appears to be exponential/power-law")
    else:
        improvement = ((log_linear_rmse - linear_rmse) / log_linear_rmse) * 100
        print(f"\n✅ 🔴 Linear model fits better!")
        print(f"   📈 Linear is {improvement:.1f}% better ({log_linear_rmse:.6f} → {linear_rmse:.6f})")
        print(f"   💡 The relationship appears to be linear")
    
    # Correlation info
    correlation = np.corrcoef(x, y)[0, 1]
    log_correlation = np.corrcoef(x_log, y_log)[0, 1] 
    print(f"\n📊 Correlations:")
    print(f"   Original data: {correlation:.3f}")
    print(f"   Log-transformed: {log_correlation:.3f}")
    print("=" * 60)
    
    return {
        'linear_rmse': linear_rmse,
        'log_linear_rmse': log_linear_rmse,
        'r2_linear': r2_linear,
        'r2_log': r2_log,
        'plot_file': plot_filename
    }

def main():
    """Main analysis function"""
    # Load data
    csv_file = "experiment_results_local.csv"
    
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} experiments from {csv_file}")
        print(f"📊 Columns available: {list(df.columns)}")
    except FileNotFoundError:
        print(f"❌ File {csv_file} not found. Please check the file path.")
        return
    
    if len(df) == 0:
        print("❌ No data in CSV file")
        return
    
    # Configuration - MODIFY THESE FOR YOUR ANALYSIS
    analyses = [
        # (x_column, y_column, log_transform, description)
        ("Concur.", "Observed utilization", "y", "Concurrency vs Utilization (exponential test)"),
        ("Concur.", "transfer_avg", "x", "Transfer time vs Concurrency (logarithmic test)"), 
        ("Parallel.", "transfer_max", "both", "Parallel flows vs Max transfer (power law test)"),
        ("duration", "transfer_avg", "y", "Duration vs Transfer time (exponential test)"),
    ]
    
    print(f"\n🚀 Running {len(analyses)} regression analyses...")
    
    results = []
    for x_col, y_col, log_type, desc in analyses:
        print(f"\n{'='*60}")
        print(f"🎯 {desc}")
        
        if x_col in df.columns and y_col in df.columns:
            result = analyze_linear_vs_loglinear(df, x_col, y_col, log_type)
            if result:
                result['description'] = desc
                results.append(result)
        else:
            print(f"❌ Columns '{x_col}' or '{y_col}' not found in data")
    
    # Summary
    print(f"\n🏆 === ANALYSIS SUMMARY ===")
    print(f"📊 Generated {len(results)} plots in 'plots/' directory")
    
    for result in results:
        print(f"\n📈 {result['description']}:")
        if result['log_linear_rmse'] < result['linear_rmse']:
            print(f"   ✅ Log-linear wins (RMSE: {result['log_linear_rmse']:.4f} vs {result['linear_rmse']:.4f})")
        else:
            print(f"   ✅ Linear wins (RMSE: {result['linear_rmse']:.4f} vs {result['log_linear_rmse']:.4f})")
        print(f"   📁 Plot: {result['plot_file']}")

if __name__ == "__main__":
    main()