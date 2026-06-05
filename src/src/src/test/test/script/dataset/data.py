#!/usr/bin/env python3
"""
Synthetic Water Quality Dataset Generator
For reproducible experiments in DSM paper

Usage:
    python generate_data.py
    python generate_data.py --records 50000 --output custom.csv
"""

import numpy as np
import pandas as pd
import argparse
from pathlib import Path

# Set fixed seed for reproducibility (as per paper)
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

def generate_water_quality_dataset(num_records: int = 20000) -> pd.DataFrame:
    """
    Generate synthetic water quality dataset.
    
    Distributions derived from USGS and EPA public datasets as described in paper.
    
    Args:
        num_records: Number of records to generate (default: 20000)
    
    Returns:
        DataFrame with water quality parameters
    """
    data = {
        # pH: Normal distribution N(7.5, 1.0), clipped to [0, 14]
        'pH': np.clip(np.random.normal(7.5, 1.0, num_records), 0, 14),
        
        # Turbidity: Exponential distribution rate=0.02, clipped to [0, 5000] NTU
        'turbidity_ntu': np.clip(np.random.exponential(50, num_records), 0, 5000),
        
        # Dissolved Oxygen: Normal N(8.0, 2.0), clipped to [0, 20] mg/L
        'dissolved_oxygen_mgl': np.clip(np.random.normal(8.0, 2.0, num_records), 0, 20),
        
        # Temperature: Normal N(20, 10), clipped to [0, 50] °C
        'temperature_celsius': np.clip(np.random.normal(20, 10, num_records), 0, 50),
        
        # Contaminant flag: 5% contamination rate (as per EPA reports)
        'contaminant_detected': np.random.choice([0, 1], num_records, p=[0.95, 0.05]),
        
        # E. coli levels: Categorical distribution
        # 0: 70%, 1: 15%, 2: 8%, 3: 4%, 4: 2%, 5: 1%
        'ecoli_level': np.random.choice(
            [0, 1, 2, 3, 4, 5],
            num_records,
            p=[0.70, 0.15, 0.08, 0.04, 0.02, 0.01]
        ),
        
        # Sensor ID: 1000 sensors as per paper
        'sensor_id': np.random.randint(1, 1001, num_records),
    }
    
    # Add timestamps (sequential, starting from 2024-01-01)
    start_timestamp = pd.Timestamp('2024-01-01 00:00:00')
    timestamps = [start_timestamp + pd.Timedelta(hours=i) for i in range(num_records)]
    data['timestamp'] = timestamps
    
    df = pd.DataFrame(data)
    
    # Round floating point columns to 2 decimal places for realism
    df['pH'] = df['pH'].round(2)
    df['turbidity_ntu'] = df['turbidity_ntu'].round(1)
    df['dissolved_oxygen_mgl'] = df['dissolved_oxygen_mgl'].round(2)
    df['temperature_celsius'] = df['temperature_celsius'].round(1)
    
    return df

def generate_query_workload(num_queries: int = 10000) -> pd.DataFrame:
    """
    Generate synthetic query workload for benchmarking.
    
    As described in paper: queries favor recent and anomalous records.
    
    Args:
        num_queries: Number of simulated queries
    
    Returns:
        DataFrame with query parameters
    """
    # Query recency bias: 70% recent (last 7 days), 20% medium (8-30 days), 10% old
    recency_bias = np.random.choice(
        ['recent', 'medium', 'old'],
        num_queries,
        p=[0.70, 0.20, 0.10]
    )
    
    # Query anomaly bias: 30% target contaminant records
    anomaly_bias = np.random.choice(
        [True, False],
        num_queries,
        p=[0.30, 0.70]
    )
    
    df = pd.DataFrame({
        'query_id': range(1, num_queries + 1),
        'recency_bias': recency_bias,
        'anomaly_bias': anomaly_bias,
    })
    
    return df

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic water quality dataset for DSM paper')
    parser.add_argument('--records', '-n', type=int, default=20000,
                        help='Number of records to generate (default: 20000)')
    parser.add_argument('--output', '-o', type=str, default='water_quality_dataset.csv',
                        help='Output filename (default: water_quality_dataset.csv)')
    parser.add_argument('--queries', '-q', type=int, default=10000,
                        help='Number of query workload records (default: 10000)')
    parser.add_argument('--query-output', '-qo', type=str, default='query_workload.csv',
                        help='Query workload output filename')
    
    args = parser.parse_args()
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {args.records} water quality records with seed {RANDOM_SEED}...")
    df = generate_water_quality_dataset(args.records)
    df.to_csv(output_path, index=False)
    print(f"✅ Saved to {output_path}")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   pH range: [{df['pH'].min()}, {df['pH'].max()}]")
    print(f"   Contamination rate: {df['contaminant_detected'].mean()*100:.1f}%")
    
    # Generate query workload
    print(f"\nGenerating {args.queries} query workload records...")
    qdf = generate_query_workload(args.queries)
    qdf.to_csv(args.query_output, index=False)
    print(f"✅ Saved to {args.query_output}")
    
    # Print summary statistics (as in paper Section 4.1.1)
    print("\n=== Dataset Summary Statistics (Paper Section 4.1.1) ===")
    print(f"pH: μ={df['pH'].mean():.2f}, σ={df['pH'].std():.2f}")
    print(f"Turbidity: μ={df['turbidity_ntu'].mean():.1f} NTU")
    print(f"Dissolved Oxygen: μ={df['dissolved_oxygen_mgl'].mean():.2f} mg/L")
    print(f"Temperature: μ={df['temperature_celsius'].mean():.1f}°C")
    print(f"Unique sensors: {df['sensor_id'].nunique()}")
    
    print("\n✅ Dataset generation complete. Fixed seed ensures reproducibility.")

if __name__ == "__main__":
    main()