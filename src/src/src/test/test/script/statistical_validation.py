#!/usr/bin/env python3
"""
Statistical Validation Script for DSM Gas Benchmarks
Runs 50 iterations of gas benchmarks and performs statistical analysis
with t-tests and confidence intervals as per paper methodology

Usage:
    python statistical_validation.py --runs 50 --output results.csv
"""

import subprocess
import json
import csv
import argparse
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StatisticalValidator:
    """
    Runs gas benchmarks multiple times and performs statistical analysis.
    Validates claims with p < 0.001 significance level.
    """
    
    def __init__(self, runs: int = 50, output_file: str = "results.csv"):
        self.runs = runs
        self.output_file = output_file
        self.results = {
            'dsm_deployment': [],
            'array_deployment': [],
            'mapping_deployment': [],
            'dsm_migration_1000': [],
            'array_migration_1000': [],
            'mapping_migration_1000': [],
            'dsm_streaming_peak': [],
            'array_streaming_peak': [],
            'dsm_store_gas': [],
            'array_store_gas': [],
        }
    
    def run_foundry_test(self, test_name: str) -> Dict:
        """
        Run a Foundry test and extract gas measurements.
        
        Args:
            test_name: Name of the test to run
        
        Returns:
            Dictionary with gas measurements
        """
        try:
            # Run forge test from root directory
            cmd = [
                "forge", "test",
                "--match-test", test_name,
                "-vvv"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd="c:/Users/user/dsm-blockchain-storage"
            )
            
            # Parse gas output from console logs
            output = result.stdout + result.stderr
            
            # Extract gas values
            gas_values = {}
            lines = output.split('\n')
            
            for line in lines:
                # Look for deployment gas outputs
                if 'DSM Deployment Gas:' in line:
                    try:
                        gas_val = int(line.split('DSM Deployment Gas:')[1].strip())
                        gas_values['DSM Deployment Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'Array Baseline Deployment Gas:' in line:
                    try:
                        gas_val = int(line.split('Array Baseline Deployment Gas:')[1].strip())
                        gas_values['Array Baseline Deployment Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'Mapping-Only Deployment Gas:' in line:
                    try:
                        gas_val = int(line.split('Mapping-Only Deployment Gas:')[1].strip())
                        gas_values['Mapping-Only Deployment Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'DSM Migration Gas:' in line:
                    try:
                        gas_val = int(line.split('DSM Migration Gas:')[1].strip())
                        gas_values['DSM Migration Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'Array Baseline Migration Gas:' in line:
                    try:
                        gas_val = int(line.split('Array Baseline Migration Gas:')[1].strip())
                        gas_values['Array Baseline Migration Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'Mapping-Only Migration Gas:' in line:
                    try:
                        gas_val = int(line.split('Mapping-Only Migration Gas:')[1].strip())
                        gas_values['Mapping-Only Migration Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'DSM Peak Migration Gas:' in line:
                    try:
                        gas_val = int(line.split('DSM Peak Migration Gas:')[1].strip())
                        gas_values['DSM Peak Migration Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'Array Baseline Peak Migration Gas:' in line:
                    try:
                        gas_val = int(line.split('Array Baseline Peak Migration Gas:')[1].strip())
                        gas_values['Array Baseline Peak Migration Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'DSM Store Gas:' in line:
                    try:
                        gas_val = int(line.split('DSM Store Gas:')[1].strip())
                        gas_values['DSM Store Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
                elif 'Array Baseline Store Gas:' in line:
                    try:
                        gas_val = int(line.split('Array Baseline Store Gas:')[1].strip())
                        gas_values['Array Baseline Store Gas'] = gas_val
                    except (ValueError, IndexError):
                        pass
            
            return gas_values
            
        except Exception as e:
            logger.error(f"Error running test {test_name}: {e}")
            return {}
    
    def run_benchmark_iteration(self, iteration: int):
        """
        Run a single benchmark iteration.
        
        Args:
            iteration: Iteration number
        """
        logger.info(f"Running iteration {iteration + 1}/{self.runs}")
        
        # Run deployment gas test
        deployment_gas = self.run_foundry_test("test_DeploymentGasComparison")
        if 'DSM Deployment Gas' in deployment_gas:
            self.results['dsm_deployment'].append(deployment_gas['DSM Deployment Gas'])
        if 'Array Baseline Deployment Gas' in deployment_gas:
            self.results['array_deployment'].append(deployment_gas['Array Baseline Deployment Gas'])
        if 'Mapping-Only Deployment Gas' in deployment_gas:
            self.results['mapping_deployment'].append(deployment_gas['Mapping-Only Deployment Gas'])
        
        # Run migration gas test at 1000 records
        migration_gas = self.run_foundry_test("test_MigrationGas_at_1000Records")
        if 'DSM Migration Gas' in migration_gas:
            self.results['dsm_migration_1000'].append(migration_gas['DSM Migration Gas'])
        if 'Array Baseline Migration Gas' in migration_gas:
            self.results['array_migration_1000'].append(migration_gas['Array Baseline Migration Gas'])
        if 'Mapping-Only Migration Gas' in migration_gas:
            self.results['mapping_migration_1000'].append(migration_gas['Mapping-Only Migration Gas'])
        
        # Run streaming simulation test
        streaming_gas = self.run_foundry_test("test_StreamingSimulation_10000Records")
        if 'DSM Peak Migration Gas' in streaming_gas:
            self.results['dsm_streaming_peak'].append(streaming_gas['DSM Peak Migration Gas'])
        if 'Array Baseline Peak Migration Gas' in streaming_gas:
            self.results['array_streaming_peak'].append(streaming_gas['Array Baseline Peak Migration Gas'])
        
        # Run execution time comparison test
        execution_gas = self.run_foundry_test("test_ExecutionTimeComparison")
        if 'DSM Store Gas' in execution_gas:
            self.results['dsm_store_gas'].append(execution_gas['DSM Store Gas'])
        if 'Array Baseline Store Gas' in execution_gas:
            self.results['array_store_gas'].append(execution_gas['Array Baseline Store Gas'])
    
    def run_all_iterations(self):
        """Run all benchmark iterations."""
        logger.info(f"Starting {self.runs} benchmark iterations")
        
        for i in range(self.runs):
            self.run_benchmark_iteration(i)
            
            # Save intermediate results every 10 iterations
            if (i + 1) % 10 == 0:
                self.save_results()
                logger.info(f"Saved intermediate results after {i + 1} iterations")
        
        logger.info("Completed all iterations")
    
    def calculate_statistics(self, data: List[float]) -> Dict:
        """
        Calculate statistical metrics for a dataset.
        
        Args:
            data: List of measurements
        
        Returns:
            Dictionary with statistics
        """
        if len(data) == 0:
            return {}
        
        data_array = np.array(data)
        
        return {
            'mean': np.mean(data_array),
            'std': np.std(data_array, ddof=1),
            'min': np.min(data_array),
            'max': np.max(data_array),
            'median': np.median(data_array),
            'count': len(data_array),
            'ci_95': stats.t.interval(
                0.95,
                len(data_array) - 1,
                loc=np.mean(data_array),
                scale=stats.sem(data_array)
            )
        }
    
    def perform_t_test(
        self,
        sample1: List[float],
        sample2: List[float],
        test_name: str
    ) -> Dict:
        """
        Perform independent two-tailed t-test.
        
        Args:
            sample1: First sample
            sample2: Second sample
            test_name: Name of the test
        
        Returns:
            Dictionary with t-test results
        """
        if len(sample1) < 2 or len(sample2) < 2:
            return {'error': 'Insufficient data'}
        
        t_stat, p_value = stats.ttest_ind(sample1, sample2)
        
        # Calculate Cohen's d (effect size)
        pooled_std = np.sqrt(
            ((len(sample1) - 1) * np.var(sample1, ddof=1) +
             (len(sample2) - 1) * np.var(sample2, ddof=1)) /
            (len(sample1) + len(sample2) - 2)
        )
        cohens_d = (np.mean(sample1) - np.mean(sample2)) / pooled_std
        
        return {
            'test_name': test_name,
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': p_value < 0.001,
            'cohens_d': cohens_d,
            'degrees_of_freedom': len(sample1) + len(sample2) - 2
        }
    
    def generate_report(self) -> Dict:
        """
        Generate comprehensive statistical report.
        
        Returns:
            Dictionary with all statistical results
        """
        report = {
            'iterations': self.runs,
            'deployment_gas': {},
            'migration_gas_1000': {},
            'streaming_peak_gas': {},
            'execution_time_gas': {},
            'statistical_tests': {}
        }
        
        # Deployment gas statistics
        report['deployment_gas']['dsm'] = self.calculate_statistics(self.results['dsm_deployment'])
        report['deployment_gas']['array'] = self.calculate_statistics(self.results['array_deployment'])
        report['deployment_gas']['mapping'] = self.calculate_statistics(self.results['mapping_deployment'])
        
        # Migration gas statistics at 1000 records
        report['migration_gas_1000']['dsm'] = self.calculate_statistics(self.results['dsm_migration_1000'])
        report['migration_gas_1000']['array'] = self.calculate_statistics(self.results['array_migration_1000'])
        report['migration_gas_1000']['mapping'] = self.calculate_statistics(self.results['mapping_migration_1000'])
        
        # Streaming peak gas statistics
        report['streaming_peak_gas']['dsm'] = self.calculate_statistics(self.results['dsm_streaming_peak'])
        report['streaming_peak_gas']['array'] = self.calculate_statistics(self.results['array_streaming_peak'])
        
        # Execution time gas statistics
        report['execution_time_gas']['dsm'] = self.calculate_statistics(self.results['dsm_store_gas'])
        report['execution_time_gas']['array'] = self.calculate_statistics(self.results['array_store_gas'])
        
        # Statistical tests
        report['statistical_tests']['deployment_dsm_vs_array'] = self.perform_t_test(
            self.results['dsm_deployment'],
            self.results['array_deployment'],
            'Deployment Gas: DSM vs Array Baseline'
        )
        
        report['statistical_tests']['migration_dsm_vs_array'] = self.perform_t_test(
            self.results['dsm_migration_1000'],
            self.results['array_migration_1000'],
            'Migration Gas (n=1000): DSM vs Array Baseline'
        )
        
        report['statistical_tests']['migration_dsm_vs_mapping'] = self.perform_t_test(
            self.results['dsm_migration_1000'],
            self.results['mapping_migration_1000'],
            'Migration Gas (n=1000): DSM vs Mapping-Only'
        )
        
        report['statistical_tests']['streaming_dsm_vs_array'] = self.perform_t_test(
            self.results['dsm_streaming_peak'],
            self.results['array_streaming_peak'],
            'Streaming Peak Gas: DSM vs Array Baseline'
        )
        
        report['statistical_tests']['execution_dsm_vs_array'] = self.perform_t_test(
            self.results['dsm_store_gas'],
            self.results['array_store_gas'],
            'Execution Time Gas: DSM vs Array Baseline'
        )
        
        return report
    
    def save_results(self):
        """Save results to CSV file."""
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'iteration',
                'dsm_deployment',
                'array_deployment',
                'mapping_deployment',
                'dsm_migration_1000',
                'array_migration_1000',
                'mapping_migration_1000',
                'dsm_streaming_peak',
                'array_streaming_peak',
                'dsm_store_gas',
                'array_store_gas'
            ])
            
            for i in range(self.runs):
                writer.writerow([
                    i + 1,
                    self.results['dsm_deployment'][i] if i < len(self.results['dsm_deployment']) else '',
                    self.results['array_deployment'][i] if i < len(self.results['array_deployment']) else '',
                    self.results['mapping_deployment'][i] if i < len(self.results['mapping_deployment']) else '',
                    self.results['dsm_migration_1000'][i] if i < len(self.results['dsm_migration_1000']) else '',
                    self.results['array_migration_1000'][i] if i < len(self.results['array_migration_1000']) else '',
                    self.results['mapping_migration_1000'][i] if i < len(self.results['mapping_migration_1000']) else '',
                    self.results['dsm_streaming_peak'][i] if i < len(self.results['dsm_streaming_peak']) else '',
                    self.results['array_streaming_peak'][i] if i < len(self.results['array_streaming_peak']) else '',
                    self.results['dsm_store_gas'][i] if i < len(self.results['dsm_store_gas']) else '',
                    self.results['array_store_gas'][i] if i < len(self.results['array_store_gas']) else '',
                ])
        
        logger.info(f"Saved results to {self.output_file}")
    
    def print_report(self, report: Dict):
        """Print statistical report to console."""
        print("\n" + "="*80)
        print("STATISTICAL VALIDATION REPORT")
        print("="*80)
        print(f"Iterations: {report['iterations']}")
        print()
        
        # Deployment gas
        print("DEPLOYMENT GAS STATISTICS")
        print("-" * 80)
        dsm_stats = report['deployment_gas']['dsm']
        array_stats = report['deployment_gas']['array']
        
        if dsm_stats and array_stats:
            print(f"DSM:        {dsm_stats['mean']:,.0f} ± {dsm_stats['std']:,.0f} gas (95% CI: [{dsm_stats['ci_95'][0]:,.0f}, {dsm_stats['ci_95'][1]:,.0f}])")
            print(f"Array:      {array_stats['mean']:,.0f} ± {array_stats['std']:,.0f} gas (95% CI: [{array_stats['ci_95'][0]:,.0f}, {array_stats['ci_95'][1]:,.0f}])")
            
            reduction = ((array_stats['mean'] - dsm_stats['mean']) / array_stats['mean']) * 100
            print(f"Reduction:  {reduction:.2f}%")
        print()
        
        # Migration gas at 1000 records
        print("MIGRATION GAS STATISTICS (n=1000)")
        print("-" * 80)
        dsm_mig = report['migration_gas_1000']['dsm']
        array_mig = report['migration_gas_1000']['array']
        mapping_mig = report['migration_gas_1000']['mapping']
        
        if dsm_mig and array_mig:
            print(f"DSM:        {dsm_mig['mean']:,.0f} ± {dsm_mig['std']:,.0f} gas")
            print(f"Array:      {array_mig['mean']:,.0f} ± {array_mig['std']:,.0f} gas")
            if mapping_mig:
                print(f"Mapping:    {mapping_mig['mean']:,.0f} ± {mapping_mig['std']:,.0f} gas")
            
            reduction_vs_array = ((array_mig['mean'] - dsm_mig['mean']) / array_mig['mean']) * 100
            print(f"DSM vs Array: {reduction_vs_array:.2f}% reduction")
        print()
        
        # Execution time gas statistics
        print("EXECUTION TIME GAS STATISTICS (gas proxy)")
        print("-" * 80)
        dsm_exec = report['execution_time_gas']['dsm']
        array_exec = report['execution_time_gas']['array']
        
        if dsm_exec and array_exec:
            print(f"DSM:        {dsm_exec['mean']:,.0f} ± {dsm_exec['std']:,.0f} gas")
            print(f"Array:      {array_exec['mean']:,.0f} ± {array_exec['std']:,.0f} gas")
            
            reduction_vs_array = ((array_exec['mean'] - dsm_exec['mean']) / array_exec['mean']) * 100
            print(f"DSM vs Array: {reduction_vs_array:.2f}% reduction")
        print()
        
        # Statistical tests
        print("STATISTICAL TESTS (independent two-tailed t-test)")
        print("-" * 80)
        for test_name, test_result in report['statistical_tests'].items():
            if 'error' not in test_result:
                sig = "✓ SIGNIFICANT" if test_result['significant'] else "✗ NOT SIGNIFICANT"
                print(f"{test_result['test_name']}:")
                print(f"  t-statistic: {test_result['t_statistic']:.4f}")
                print(f"  p-value: {test_result['p_value']:.2e}")
                print(f"  Significance (p < 0.001): {sig}")
                print(f"  Cohen's d: {test_result['cohens_d']:.4f}")
                print()
        
        print("="*80)
    
    def save_report_json(self, report: Dict, filename: str = "statistical_report.json"):
        """Save statistical report to JSON file."""
        output_path = Path(filename)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Saved statistical report to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Statistical validation for DSM gas benchmarks')
    parser.add_argument('--runs', '-r', type=int, default=50,
                        help='Number of benchmark iterations (default: 50)')
    parser.add_argument('--output', '-o', type=str, default='results.csv',
                        help='Output CSV file (default: results.csv)')
    parser.add_argument('--report', type=str, default='statistical_report.json',
                        help='Statistical report JSON file (default: statistical_report.json)')
    parser.add_argument('--load-only', action='store_true',
                        help='Only load existing results and generate report (skip running benchmarks)')
    
    args = parser.parse_args()
    
    validator = StatisticalValidator(runs=args.runs, output_file=args.output)
    
    if not args.load_only:
        validator.run_all_iterations()
        validator.save_results()
    else:
        # Load existing results
        logger.info(f"Loading existing results from {args.output}")
        df = pd.read_csv(args.output)
        for col in df.columns:
            if col != 'iteration':
                validator.results[col] = df[col].dropna().tolist()
    
    # Generate and print report
    report = validator.generate_report()
    validator.print_report(report)
    validator.save_report_json(report, args.report)
    
    logger.info("Statistical validation complete")


if __name__ == "__main__":
    main()
